from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from practice.models import Exam, PracticeSession, Question, SessionItem

ANSWER_MEDIA_ROLES = {"answer_asset", "comment_asset", "source_fragment"}


def question_queryset():
    return Question.objects.select_related("exam").prefetch_related(
        "options", "references", "community_comments", "media"
    )


def session_summary(session: PracticeSession) -> dict[str, Any]:
    counts = session.items.aggregate(
        answered_items=Count("id", filter=Q(answered=True)),
        correct_items=Count("id", filter=Q(is_correct=True)),
    )
    return {
        "id": session.id,
        "exam_slug": session.exam.slug,
        "mode": session.mode,
        "current_position": session.current_position,
        "total_items": session.total_items,
        "answered_items": counts["answered_items"],
        "correct_items": counts["correct_items"],
        "status": session.status,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


@transaction.atomic
def create_practice_session(
    exam: Exam, *, mode: str, from_order: int, to_order: int, owner=None
) -> PracticeSession:
    questions = list(
        Question.objects.filter(exam=exam, pdf_order__gte=from_order, pdf_order__lte=to_order)
        .order_by("pdf_order")
        .only("id")
    )
    if not questions:
        raise ValidationError("No hay preguntas dentro del intervalo solicitado.")
    session = PracticeSession.objects.create(
        exam=exam,
        owner=owner,
        mode=mode,
        current_position=1,
        total_items=len(questions),
    )
    SessionItem.objects.bulk_create(
        [
            SessionItem(session=session, position=position, question=question)
            for position, question in enumerate(questions, start=1)
        ],
        batch_size=500,
    )
    return session


def grade(question: Question, response: dict[str, Any]) -> bool | None:
    if question.interaction.get("grading_mode") != "automatic":
        return None
    submitted = response.get("choice_keys")
    if not isinstance(submitted, list) or not all(isinstance(item, str) for item in submitted):
        raise ValidationError("response.choice_keys debe ser una lista de claves de opción.")
    expected = question.source_answer.get("option_keys", [])
    return set(submitted) == set(expected) and len(submitted) == len(expected)


def build_feedback(
    session: PracticeSession, item: SessionItem, question: Question, request=None
) -> dict[str, Any]:
    answer_media = [media for media in question.media.all() if media.role in ANSWER_MEDIA_ROLES]
    return {
        "question_id": question.id,
        "is_correct": item.is_correct,
        "grading_mode": question.interaction.get("grading_mode", "reveal_only"),
        "source_answer": question.source_answer,
        "source_answer_raw": question.source_answer_raw,
        "explanation_raw": question.explanation_raw,
        "community_discussion_raw": question.community_discussion_raw,
        "references": question.references.all(),
        "community_comments": question.community_comments.all(),
        "answer_media": answer_media,
        "session_status": session.status,
        "next_position": session.current_position if session.status == "active" else None,
    }


@transaction.atomic
def submit_answer(
    session_id,
    *,
    question_id: str,
    response: dict[str, Any],
    idempotency_key: str | None,
    request=None,
    owner=None,
) -> dict[str, Any]:
    try:
        session = (
            PracticeSession.objects.select_for_update()
            .select_related("exam")
            .get(pk=session_id, owner=owner)
        )
    except PracticeSession.DoesNotExist as exc:
        raise NotFound("Sesión de práctica no encontrada.") from exc

    if idempotency_key:
        previous = SessionItem.objects.filter(
            session=session,
            question_id=question_id,
            idempotency_key=idempotency_key,
            answered=True,
        ).first()
        if previous:
            question = question_queryset().get(pk=previous.question_id)
            return build_feedback(session, previous, question, request)

    try:
        item = SessionItem.objects.select_for_update().get(
            session=session, position=session.current_position
        )
    except SessionItem.DoesNotExist as exc:
        raise ValidationError("La sesión no tiene una pregunta activa.") from exc
    if item.question_id != question_id:
        raise ValidationError("La respuesta debe corresponder a la pregunta actual.")
    if item.answered:
        raise ValidationError("La pregunta actual ya fue respondida.")

    question = question_queryset().get(pk=item.question_id)
    item.answered = True
    item.response = response
    item.is_correct = grade(question, response)
    item.idempotency_key = idempotency_key
    item.answered_at = timezone.now()
    item.save(
        update_fields=["answered", "response", "is_correct", "idempotency_key", "answered_at"]
    )

    if session.current_position >= session.total_items:
        session.status = PracticeSession.Status.COMPLETED
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])
    else:
        session.current_position += 1
        session.save(update_fields=["current_position"])
    return build_feedback(session, item, question, request)


@transaction.atomic
def discard_answer(
    session_id,
    *,
    question_id: str,
    repeat: bool,
    owner=None,
) -> dict[str, Any]:
    try:
        session = (
            PracticeSession.objects.select_for_update()
            .select_related("exam")
            .get(pk=session_id, owner=owner)
        )
    except PracticeSession.DoesNotExist as exc:
        raise NotFound("Sesión de práctica no encontrada.") from exc

    try:
        item = SessionItem.objects.select_for_update().get(
            session=session, question_id=question_id, answered=True
        )
    except SessionItem.DoesNotExist as exc:
        raise ValidationError("La pregunta no tiene una respuesta guardada.") from exc

    is_latest = item.position == session.current_position - 1
    is_completed_latest = (
        session.status == PracticeSession.Status.COMPLETED
        and item.position == session.current_position == session.total_items
    )
    if not (is_latest or is_completed_latest):
        raise ValidationError("Solo puedes cambiar el resultado de la pregunta actual.")

    item.answered = False
    item.response = None
    item.is_correct = None
    item.idempotency_key = None
    item.answered_at = None
    item.save(
        update_fields=["answered", "response", "is_correct", "idempotency_key", "answered_at"]
    )

    if repeat:
        session.current_position = item.position
        session.status = PracticeSession.Status.ACTIVE
        session.completed_at = None
        session.save(update_fields=["current_position", "status", "completed_at"])

    return session_summary(session)
