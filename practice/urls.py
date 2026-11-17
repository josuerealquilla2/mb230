from django.urls import path

from practice.views import (
    ExamDetailView,
    ExamListView,
    LiveHealthView,
    LoginView,
    LogoutView,
    MeView,
    PracticeSessionAnswerView,
    PracticeSessionAnswerDispositionView,
    PracticeSessionCreateView,
    PracticeSessionDetailView,
    PracticeSessionNextView,
    QuestionDetailView,
    QuestionListView,
    ReadyHealthView,
    RegisterView,
    UserPreferenceView,
)

urlpatterns = [
    path("health/live", LiveHealthView.as_view(), name="health-live"),
    path("health/ready", ReadyHealthView.as_view(), name="health-ready"),
    path("api/v1/auth/register", RegisterView.as_view(), name="auth-register"),
    path("api/v1/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/v1/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/v1/auth/me", MeView.as_view(), name="auth-me"),
    path("api/v1/me/preferences", UserPreferenceView.as_view(), name="user-preferences"),
    path("api/v1/exams", ExamListView.as_view(), name="exam-list"),
    path("api/v1/exams/<slug:slug>", ExamDetailView.as_view(), name="exam-detail"),
    path("api/v1/exams/<slug:slug>/questions", QuestionListView.as_view(), name="question-list"),
    path(
        "api/v1/questions/<str:question_id>", QuestionDetailView.as_view(), name="question-detail"
    ),
    path("api/v1/practice-sessions", PracticeSessionCreateView.as_view(), name="session-create"),
    path(
        "api/v1/practice-sessions/<uuid:session_id>",
        PracticeSessionDetailView.as_view(),
        name="session-detail",
    ),
    path(
        "api/v1/practice-sessions/<uuid:session_id>/next",
        PracticeSessionNextView.as_view(),
        name="session-next",
    ),
    path(
        "api/v1/practice-sessions/<uuid:session_id>/answers",
        PracticeSessionAnswerView.as_view(),
        name="session-answer",
    ),
    path(
        "api/v1/practice-sessions/<uuid:session_id>/answers/disposition",
        PracticeSessionAnswerDispositionView.as_view(),
        name="session-answer-disposition",
    ),
]
