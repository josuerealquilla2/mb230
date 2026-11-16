from django.contrib import admin

from practice.models import Exam, PracticeSession, Question


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("slug", "title", "question_count", "imported_at")
    search_fields = ("slug", "title")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("pdf_order", "id", "question_type", "source_page_start", "source_page_end")
    list_filter = ("question_type", "review_status")
    search_fields = ("id", "prompt_text")
    ordering = ("pdf_order",)


@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "status", "current_position", "total_items", "created_at")
    list_filter = ("status", "mode")
