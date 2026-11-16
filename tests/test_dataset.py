from collections import Counter

from practice.dataset import validate_dataset, validate_translation_dataset
from practice.models import Exam


def test_canonical_dataset_is_complete_and_ordered() -> None:
    manifest, questions = validate_dataset()
    assert manifest["question_count"] == 463
    assert [item["pdf_order"] for item in questions] == list(range(1, 464))
    assert Counter(item["question_type"] for item in questions) == {
        "single_choice": 166,
        "multiple_choice": 69,
        "yes_no": 41,
        "drag_drop": 94,
        "hotspot": 93,
    }


def test_first_five_source_answers_are_preserved() -> None:
    _, questions = validate_dataset()
    assert [item["source_answer"]["option_keys"] for item in questions[:5]] == [
        ["B"],
        ["B"],
        ["A"],
        ["B"],
        ["B"],
    ]


def test_every_question_has_an_exact_source_fragment() -> None:
    _, questions = validate_dataset()
    assert all(any(media["role"] == "source_fragment" for media in q["media"]) for q in questions)


def test_non_breaking_spaces_from_the_pdf_are_preserved() -> None:
    _, questions = validate_dataset()
    assert sum(question["raw_text"].count("\u00a0") for question in questions) == 8


def test_spanish_translation_corpus_is_complete(db) -> None:  # type: ignore[no-untyped-def]
    from practice.dataset import import_canonical_dataset

    exam = import_canonical_dataset()
    translations = validate_translation_dataset(Exam.objects.get(pk=exam.pk))
    assert len(translations) == 463
    assert all(item["prompt_text"].strip() for item in translations)
