from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from practice.models import CommunityComment, Exam, Option, Question, QuestionMedia, Reference


class DatasetValidationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise DatasetValidationError(
                    f"JSONL inválido en {path}:{line_number}: {exc}"
                ) from exc
    return records


def _content_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "content_sha256"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def validate_dataset(
    canonical_dir: Path | None = None, media_dir: Path | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    canonical_dir = canonical_dir or Path(settings.DATASET_CANONICAL_DIR)
    media_dir = media_dir or Path(settings.MEDIA_ROOT)
    manifest_path = canonical_dir / "manifest.json"
    questions_path = canonical_dir / "questions.jsonl"
    if not manifest_path.is_file() or not questions_path.is_file():
        raise DatasetValidationError("Se requieren manifest.json y questions.jsonl")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    questions = load_jsonl(questions_path)
    expected_count = int(manifest["question_count"])
    if len(questions) != expected_count:
        raise DatasetValidationError(
            f"Se esperaban {expected_count} preguntas; hay {len(questions)}"
        )
    orders = [int(item["pdf_order"]) for item in questions]
    if orders != list(range(1, expected_count + 1)):
        raise DatasetValidationError("pdf_order debe ser continuo, único y ascendente desde 1")
    if len({item["id"] for item in questions}) != len(questions):
        raise DatasetValidationError("Los identificadores de pregunta no son únicos")

    for question in questions:
        option_keys = {option["key"] for option in question.get("options", [])}
        answer_keys = set(question.get("source_answer", {}).get("option_keys", []))
        if not answer_keys.issubset(option_keys):
            raise DatasetValidationError(
                f"{question['id']} tiene respuestas sin opción correspondiente"
            )
        if question.get("content_sha256") != _content_hash(question):
            raise DatasetValidationError(f"Hash de contenido incorrecto: {question['id']}")
        for media in question.get("media", []):
            path = media_dir / media["relative_path"]
            if not path.is_file() or sha256_file(path) != media["sha256"]:
                raise DatasetValidationError(f"Recurso visual ausente o modificado: {path}")
    if manifest.get("questions_sha256") != sha256_file(questions_path):
        raise DatasetValidationError("El hash de questions.jsonl no coincide con el manifiesto")
    return manifest, questions


def validate_translation_dataset(
    exam: Exam, translation_path: Path | None = None
) -> list[dict[str, Any]]:
    translation_path = translation_path or Path(settings.DATASET_TRANSLATIONS_DIR) / "es.jsonl"
    if not translation_path.is_file():
        raise DatasetValidationError(f"No existe el archivo de traducciones: {translation_path}")

    records = load_jsonl(translation_path)
    by_id = {str(record.get("question_id", "")): record for record in records}
    questions = list(
        exam.questions.prefetch_related("options", "community_comments").order_by("pdf_order")
    )
    expected_ids = {question.id for question in questions}
    if len(records) != len(by_id) or set(by_id) != expected_ids:
        raise DatasetValidationError(
            "Las traducciones deben contener exactamente una entrada para cada pregunta."
        )

    for question in questions:
        translation = by_id[question.id]
        if not str(translation.get("prompt_text", "")).strip():
            raise DatasetValidationError(f"Falta la traducción de la pregunta {question.id}")
        option_translations = translation.get("options", {})
        for option in question.options.all():
            if option.text.strip() and not str(option_translations.get(option.key, "")).strip():
                raise DatasetValidationError(
                    f"Falta la traducción de la opción {question.id}/{option.key}"
                )
        comment_translations = translation.get("comments", {})
        for comment in question.community_comments.all():
            if comment.raw_text.strip() and not str(
                comment_translations.get(str(comment.position), "")
            ).strip():
                raise DatasetValidationError(
                    f"Falta la traducción del comentario {question.id}/{comment.position}"
                )
    return records


def apply_translations(exam: Exam, translation_path: Path | None = None) -> int:
    records = validate_translation_dataset(exam, translation_path)
    translations = {str(record["question_id"]): record for record in records}
    questions = list(exam.questions.order_by("pdf_order"))
    for question in questions:
        record = translations[question.id]
        question.translations = {
            "language": "es",
            "prompt_text": record["prompt_text"],
            "options": record.get("options", {}),
            "comments": record.get("comments", {}),
            "method": record.get("translation_method", "machine"),
        }
    Question.objects.bulk_update(questions, ["translations"], batch_size=200)
    return len(questions)


@transaction.atomic
def import_canonical_dataset(*, replace: bool = False) -> Exam:
    manifest, records = validate_dataset()
    slug = manifest["exam"]["slug"]
    existing = Exam.objects.filter(slug=slug).first()
    if existing and existing.dataset_sha256 == manifest["dataset_sha256"]:
        apply_translations(existing)
        return existing
    if existing and not replace:
        raise DatasetValidationError(
            f"El examen {slug} ya contiene otra versión. Usa --replace de forma explícita."
        )
    if existing:
        existing.delete()

    exam = Exam.objects.create(
        slug=slug,
        title=manifest["exam"]["title"],
        description=manifest["exam"].get("description", ""),
        question_count=manifest["question_count"],
        dataset_sha256=manifest["dataset_sha256"],
        source_sha256=manifest["source"]["sha256"],
    )
    questions: list[Question] = []
    for record in records:
        questions.append(
            Question(
                id=record["id"],
                exam=exam,
                pdf_order=record["pdf_order"],
                source_question_number=record["source_question_number"],
                question_type=record["question_type"],
                language=record.get("language", "en"),
                prompt_text=record["prompt_text"],
                raw_text=record["raw_text"],
                source_answer_raw=record["source_answer"]["raw_text"],
                source_answer=record["source_answer"],
                verified_answer=record.get("verified_answer"),
                explanation_raw=record["explanation_raw"],
                community_discussion_raw=record["community_discussion_raw"],
                interaction=record["interaction"],
                source_page_start=record["source_pages"]["start"],
                source_page_end=record["source_pages"]["end"],
                content_sha256=record["content_sha256"],
                review_status=record.get("review_status", "auto_extracted"),
            )
        )
    Question.objects.bulk_create(questions, batch_size=200)

    options: list[Option] = []
    references: list[Reference] = []
    comments: list[CommunityComment] = []
    media_items: list[QuestionMedia] = []
    for record in records:
        question_id = record["id"]
        options.extend(
            Option(
                question_id=question_id,
                key=item["key"],
                position=item["position"],
                text=item["text"],
            )
            for item in record.get("options", [])
        )
        references.extend(
            Reference(
                question_id=question_id,
                position=item["position"],
                raw_text=item["raw_text"],
                url=item.get("url"),
            )
            for item in record.get("references", [])
        )
        comments.extend(
            CommunityComment(
                question_id=question_id,
                position=item["position"],
                raw_text=item["raw_text"],
                selected_answer=item.get("selected_answer"),
                source_pages=item.get("source_pages", []),
                source_bboxes=item.get("source_bboxes", []),
            )
            for item in record.get("community_comments", [])
        )
        media_items.extend(
            QuestionMedia(
                question_id=question_id,
                position=item["position"],
                role=item["role"],
                sha256=item["sha256"],
                relative_path=item["relative_path"],
                mime_type=item["mime_type"],
                width=item["width"],
                height=item["height"],
                source_page=item["source_page"],
                source_bbox=item["source_bbox"],
            )
            for item in record.get("media", [])
        )
    Option.objects.bulk_create(options, batch_size=1000)
    Reference.objects.bulk_create(references, batch_size=500)
    CommunityComment.objects.bulk_create(comments, batch_size=1000)
    QuestionMedia.objects.bulk_create(media_items, batch_size=1000)
    apply_translations(exam)
    return exam
