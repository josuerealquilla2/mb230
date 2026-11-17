from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Exam(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    question_count = models.PositiveIntegerField()
    dataset_sha256 = models.CharField(max_length=64, unique=True)
    source_sha256 = models.CharField(max_length=64)
    imported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.slug


class Question(models.Model):
    id = models.CharField(max_length=40, primary_key=True)
    exam = models.ForeignKey(Exam, related_name="questions", on_delete=models.CASCADE)
    pdf_order = models.PositiveIntegerField()
    source_question_number = models.PositiveIntegerField()
    question_type = models.CharField(max_length=32, db_index=True)
    language = models.CharField(max_length=8, default="en")
    prompt_text = models.TextField()
    raw_text = models.TextField()
    source_answer_raw = models.TextField(blank=True)
    source_answer = models.JSONField(default=dict)
    verified_answer = models.JSONField(null=True, blank=True)
    explanation_raw = models.TextField(blank=True)
    community_discussion_raw = models.TextField(blank=True)
    interaction = models.JSONField(default=dict)
    source_page_start = models.PositiveIntegerField()
    source_page_end = models.PositiveIntegerField()
    content_sha256 = models.CharField(max_length=64, unique=True)
    review_status = models.CharField(max_length=32, default="auto_extracted")
    translations = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["pdf_order"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "pdf_order"], name="uq_question_exam_order")
        ]
        indexes = [models.Index(fields=["exam", "question_type", "pdf_order"])]

    def __str__(self) -> str:
        return f"{self.pdf_order}. {self.id}"


class Option(models.Model):
    question = models.ForeignKey(Question, related_name="options", on_delete=models.CASCADE)
    key = models.CharField(max_length=16)
    position = models.PositiveIntegerField()
    text = models.TextField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["question", "key"], name="uq_option_question_key"),
            models.UniqueConstraint(
                fields=["question", "position"], name="uq_option_question_position"
            ),
        ]


class Reference(models.Model):
    question = models.ForeignKey(Question, related_name="references", on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    raw_text = models.TextField()
    url = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"], name="uq_reference_question_position"
            )
        ]


class CommunityComment(models.Model):
    question = models.ForeignKey(
        Question, related_name="community_comments", on_delete=models.CASCADE
    )
    position = models.PositiveIntegerField()
    raw_text = models.TextField()
    selected_answer = models.CharField(max_length=32, null=True, blank=True)
    source_pages = models.JSONField(default=list)
    source_bboxes = models.JSONField(default=list)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"], name="uq_comment_question_position"
            )
        ]


class QuestionMedia(models.Model):
    question = models.ForeignKey(Question, related_name="media", on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    role = models.CharField(max_length=32, db_index=True)
    sha256 = models.CharField(max_length=64, db_index=True)
    relative_path = models.TextField()
    mime_type = models.CharField(max_length=64)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    source_page = models.PositiveIntegerField()
    source_bbox = models.JSONField(default=list)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"], name="uq_media_question_position"
            )
        ]


class PracticeSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="practice_sessions",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    exam = models.ForeignKey(Exam, related_name="practice_sessions", on_delete=models.CASCADE)
    mode = models.CharField(max_length=32, default="sequential")
    current_position = models.PositiveIntegerField(default=1)
    total_items = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)


class UserPreference(models.Model):
    class Theme(models.TextChoices):
        SYSTEM = "system", "System"
        LIGHT = "light", "Light"
        DARK = "dark", "Dark"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="preferences", on_delete=models.CASCADE
    )
    theme = models.CharField(max_length=12, choices=Theme.choices, default=Theme.SYSTEM)
    show_translation = models.BooleanField(default=True)
    default_session_size = models.PositiveSmallIntegerField(default=463)
    onboarding_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class SessionItem(models.Model):
    session = models.ForeignKey(PracticeSession, related_name="items", on_delete=models.CASCADE)
    position = models.PositiveIntegerField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answered = models.BooleanField(default=False)
    response = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "position"], name="uq_session_item_position"
            ),
            models.UniqueConstraint(
                fields=["session", "question"], name="uq_session_item_question"
            ),
        ]


class SavedQuestion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="saved_questions", on_delete=models.CASCADE
    )
    question = models.ForeignKey(Question, related_name="saved_by", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question__pdf_order"]
        constraints = [
            models.UniqueConstraint(fields=["user", "question"], name="uq_saved_question_user")
        ]
