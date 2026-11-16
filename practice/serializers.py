from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from practice.models import (
    CommunityComment,
    Exam,
    Option,
    Question,
    QuestionMedia,
    Reference,
    UserPreference,
)

User = get_user_model()


class OptionSerializer(serializers.ModelSerializer):
    text_es = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = ("key", "position", "text", "text_es")

    def get_text_es(self, obj: Option) -> str:
        translations = getattr(obj.question, "translations", {}) or {}
        return str(translations.get("options", {}).get(obj.key, ""))


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = QuestionMedia
        fields = (
            "position",
            "role",
            "url",
            "sha256",
            "mime_type",
            "width",
            "height",
            "source_page",
        )

    def get_url(self, obj: QuestionMedia) -> str:
        path = f"{settings.MEDIA_URL}{obj.relative_path.replace('\\', '/')}"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path


class QuestionPublicSerializer(serializers.ModelSerializer):
    exam_slug = serializers.CharField(source="exam.slug")
    options = OptionSerializer(many=True)
    question_media = serializers.SerializerMethodField()
    source_pages = serializers.SerializerMethodField()
    prompt_text_es = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            "id",
            "exam_slug",
            "pdf_order",
            "source_question_number",
            "question_type",
            "language",
            "prompt_text",
            "prompt_text_es",
            "options",
            "interaction",
            "question_media",
            "source_pages",
        )

    def get_question_media(self, obj: Question) -> list[dict]:
        items = [item for item in obj.media.all() if item.role == "question_asset"]
        return MediaSerializer(items, many=True, context=self.context).data

    def get_source_pages(self, obj: Question) -> dict[str, int]:
        return {"start": obj.source_page_start, "end": obj.source_page_end}

    def get_prompt_text_es(self, obj: Question) -> str:
        return str((obj.translations or {}).get("prompt_text", ""))


class QuestionPageSerializer(serializers.Serializer):
    data = QuestionPublicSerializer(many=True)
    next_after_order = serializers.IntegerField(allow_null=True)
    count = serializers.IntegerField()


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = (
            "slug",
            "title",
            "description",
            "question_count",
            "dataset_sha256",
            "source_sha256",
        )


class PracticeSessionCreateSerializer(serializers.Serializer):
    exam_slug = serializers.SlugField(default="mb-230")
    mode = serializers.ChoiceField(choices=["sequential"], default="sequential")
    from_order = serializers.IntegerField(min_value=1, default=1)
    to_order = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class PracticeSessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    exam_slug = serializers.CharField()
    mode = serializers.CharField()
    current_position = serializers.IntegerField()
    total_items = serializers.IntegerField()
    answered_items = serializers.IntegerField()
    correct_items = serializers.IntegerField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class AnswerSubmissionSerializer(serializers.Serializer):
    question_id = serializers.CharField(max_length=40)
    response = serializers.JSONField(default=dict)


class ReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reference
        fields = ("position", "raw_text", "url")


class CommunityCommentSerializer(serializers.ModelSerializer):
    raw_text_es = serializers.SerializerMethodField()

    class Meta:
        model = CommunityComment
        fields = ("position", "raw_text", "raw_text_es", "selected_answer", "source_pages")

    def get_raw_text_es(self, obj: CommunityComment) -> str:
        translations = getattr(obj.question, "translations", {}) or {}
        return str(translations.get("comments", {}).get(str(obj.position), ""))


class AnswerFeedbackSerializer(serializers.Serializer):
    question_id = serializers.CharField()
    is_correct = serializers.BooleanField(allow_null=True)
    grading_mode = serializers.CharField()
    source_answer = serializers.JSONField()
    source_answer_raw = serializers.CharField(allow_blank=True)
    explanation_raw = serializers.CharField(allow_blank=True)
    community_discussion_raw = serializers.CharField(allow_blank=True)
    references = ReferenceSerializer(many=True)
    community_comments = CommunityCommentSerializer(many=True)
    answer_media = MediaSerializer(many=True)
    session_status = serializers.CharField()
    next_position = serializers.IntegerField(allow_null=True)


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    dataset_ready = serializers.BooleanField(required=False)
    question_count = serializers.IntegerField(required=False)


class RegisterSerializer(serializers.Serializer):
    username = serializers.RegexField(r"^[\w.@+-]+$", min_length=3, max_length=40)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)

    def validate_username(self, value: str) -> str:
        normalized = value.strip().lower()
        if User.objects.filter(username__iexact=normalized).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya está ocupado.")
        return normalized

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):  # type: ignore[no-untyped-def]
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=40)
    password = serializers.CharField(write_only=True, max_length=128)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = (
            "theme",
            "show_translation",
            "default_session_size",
            "onboarding_completed",
        )

    def validate_default_session_size(self, value: int) -> int:
        if value not in {10, 20, 50, 463}:
            raise serializers.ValidationError("El tamaño debe ser 10, 20, 50 o 463.")
        return value
