from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from practice.exceptions import Conflict
from practice.models import Exam, PracticeSession, Question, SavedQuestion, SessionItem
from practice.serializers import (
    AnswerFeedbackSerializer,
    AnswerDispositionSerializer,
    AnswerSubmissionSerializer,
    AuthResponseSerializer,
    ExamSerializer,
    HealthSerializer,
    LoginSerializer,
    PracticeSessionCreateSerializer,
    PracticeSessionSerializer,
    QuestionPageSerializer,
    QuestionFeedbackSerializer,
    QuestionPublicSerializer,
    RegisterSerializer,
    UserPreferenceSerializer,
    UserSerializer,
    TopicSerializer,
)
from practice.services import (
    create_practice_session,
    build_question_feedback,
    discard_answer,
    question_queryset,
    session_summary,
    submit_answer,
)
from practice.topics import TOPICS, get_topic, topic_query

QUESTION_TYPES = {"single_choice", "multiple_choice", "yes_no", "drag_drop", "hotspot"}


class LiveHealthView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(responses=HealthSerializer)
    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class ReadyHealthView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(responses=HealthSerializer)
    def get(self, request: Request) -> Response:
        count = Question.objects.count()
        ready = count == 463
        return Response(
            {
                "status": "ok" if ready else "not_ready",
                "dataset_ready": ready,
                "question_count": count,
            },
            status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class ExamListView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(responses=ExamSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(ExamSerializer(Exam.objects.order_by("slug"), many=True).data)


class ExamDetailView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(responses=ExamSerializer)
    def get(self, request: Request, slug: str) -> Response:
        exam = get_object_or_404(Exam, slug=slug)
        return Response(ExamSerializer(exam).data)


class QuestionListView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "after_order",
                OpenApiTypes.INT,
                description="Devuelve preguntas posteriores a este orden",
            ),
            OpenApiParameter("topic", OpenApiTypes.STR, description="Identificador del tema"),
            OpenApiParameter("limit", OpenApiTypes.INT, description="Cantidad entre 1 y 100"),
            OpenApiParameter(
                "question_type",
                OpenApiTypes.STR,
                enum=sorted(QUESTION_TYPES),
                description="Tipo de pregunta",
            ),
        ],
        responses=QuestionPageSerializer,
    )
    def get(self, request: Request, slug: str) -> Response:
        exam = get_object_or_404(Exam, slug=slug)
        try:
            after_order = int(request.query_params.get("after_order", 0))
            limit = int(request.query_params.get("limit", 20))
        except ValueError as exc:
            raise ValidationError("after_order y limit deben ser números enteros.") from exc
        if after_order < 0 or not 1 <= limit <= 100:
            raise ValidationError("after_order debe ser >= 0 y limit debe estar entre 1 y 100.")
        question_type = request.query_params.get("question_type")
        if question_type and question_type not in QUESTION_TYPES:
            raise ValidationError(
                f"question_type debe ser uno de: {', '.join(sorted(QUESTION_TYPES))}."
            )

        topic_id = request.query_params.get("topic")
        topic = get_topic(topic_id) if topic_id else None
        if topic_id and topic is None:
            raise ValidationError("El tema solicitado no existe.")

        queryset = question_queryset().filter(exam=exam, pdf_order__gt=after_order)
        if topic:
            queryset = queryset.filter(topic_query(topic)).distinct()
        if question_type:
            queryset = queryset.filter(question_type=question_type)
        questions = list(queryset.order_by("pdf_order")[: limit + 1])
        has_more = len(questions) > limit
        page_items = questions[:limit]
        payload = {
            "data": QuestionPublicSerializer(
                page_items, many=True, context={"request": request}
            ).data,
            "next_after_order": page_items[-1].pdf_order if has_more and page_items else None,
            "count": len(page_items),
        }
        return Response(payload)


class TopicListView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=TopicSerializer(many=True))
    def get(self, request: Request, slug: str) -> Response:
        exam = get_object_or_404(Exam, slug=slug)
        base = Question.objects.filter(exam=exam)
        payload = [
            {
                "id": topic.id,
                "label": topic.label,
                "description": topic.description,
                "question_count": base.filter(topic_query(topic)).distinct().count(),
            }
            for topic in TOPICS
        ]
        return Response(TopicSerializer(payload, many=True).data)


class QuestionDetailView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(responses=QuestionPublicSerializer)
    def get(self, request: Request, question_id: str) -> Response:
        try:
            question = question_queryset().get(pk=question_id)
        except Question.DoesNotExist as exc:
            raise NotFound("Pregunta no encontrada.") from exc
        return Response(QuestionPublicSerializer(question, context={"request": request}).data)


class QuestionCheckView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=AnswerSubmissionSerializer, responses=QuestionFeedbackSerializer)
    def post(self, request: Request, question_id: str) -> Response:
        serializer = AnswerSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["question_id"] != question_id:
            raise ValidationError("La respuesta no corresponde a la pregunta indicada.")
        try:
            question = question_queryset().get(pk=question_id)
        except Question.DoesNotExist as exc:
            raise NotFound("Pregunta no encontrada.") from exc
        feedback = build_question_feedback(question, serializer.validated_data["response"])
        return Response(QuestionFeedbackSerializer(feedback, context={"request": request}).data)


class SavedQuestionListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=QuestionPublicSerializer(many=True))
    def get(self, request: Request) -> Response:
        ids = SavedQuestion.objects.filter(user=request.user).values_list("question_id", flat=True)
        questions = question_queryset().filter(pk__in=ids).order_by("pdf_order")
        return Response(QuestionPublicSerializer(questions, many=True, context={"request": request}).data)


class SavedQuestionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request: Request, question_id: str) -> Response:
        question = get_object_or_404(Question, pk=question_id)
        _, created = SavedQuestion.objects.get_or_create(user=request.user, question=question)
        return Response({"saved": True}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request: Request, question_id: str) -> Response:
        SavedQuestion.objects.filter(user=request.user, question_id=question_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PracticeSessionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PracticeSessionSerializer(many=True))
    def get(self, request: Request) -> Response:
        sessions = (
            PracticeSession.objects.filter(owner=request.user)
            .select_related("exam")
            .order_by("-updated_at")
        )
        return Response(
            PracticeSessionSerializer([session_summary(item) for item in sessions], many=True).data
        )

    @extend_schema(
        request=PracticeSessionCreateSerializer, responses={201: PracticeSessionSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = PracticeSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        exam = get_object_or_404(Exam, slug=data["exam_slug"])
        end = data.get("to_order") or exam.question_count
        if end < data["from_order"] or end > exam.question_count:
            raise ValidationError("El intervalo de preguntas no es válido.")
        session = create_practice_session(
            exam,
            mode=data["mode"],
            from_order=data["from_order"],
            to_order=end,
            owner=request.user,
        )
        session = PracticeSession.objects.select_related("exam").get(pk=session.pk)
        return Response(
            PracticeSessionSerializer(session_summary(session)).data,
            status=status.HTTP_201_CREATED,
        )


class PracticeSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(responses=PracticeSessionSerializer)
    def get(self, request: Request, session_id) -> Response:  # type: ignore[no-untyped-def]
        try:
            session = PracticeSession.objects.select_related("exam").get(
                pk=session_id, owner=request.user
            )
        except PracticeSession.DoesNotExist as exc:
            raise NotFound("Sesión de práctica no encontrada.") from exc
        return Response(PracticeSessionSerializer(session_summary(session)).data)


class PracticeSessionNextView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(responses=QuestionPublicSerializer)
    def get(self, request: Request, session_id) -> Response:  # type: ignore[no-untyped-def]
        try:
            session = PracticeSession.objects.get(pk=session_id, owner=request.user)
        except PracticeSession.DoesNotExist as exc:
            raise NotFound("Sesión de práctica no encontrada.") from exc
        if session.status != PracticeSession.Status.ACTIVE:
            raise Conflict("La sesión de práctica ha terminado.")
        try:
            item = SessionItem.objects.get(session=session, position=session.current_position)
            question = question_queryset().get(pk=item.question_id)
        except (SessionItem.DoesNotExist, Question.DoesNotExist) as exc:
            raise Conflict("La sesión no tiene una pregunta activa.") from exc
        return Response(QuestionPublicSerializer(question, context={"request": request}).data)


class PracticeSessionAnswerView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(request=AnswerSubmissionSerializer, responses=AnswerFeedbackSerializer)
    def post(self, request: Request, session_id) -> Response:  # type: ignore[no-untyped-def]
        serializer = AnswerSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        feedback = submit_answer(
            session_id,
            question_id=data["question_id"],
            response=data["response"],
            idempotency_key=request.headers.get("Idempotency-Key"),
            request=request,
            owner=request.user,
        )
        return Response(AnswerFeedbackSerializer(feedback, context={"request": request}).data)


class PracticeSessionAnswerDispositionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=AnswerDispositionSerializer, responses=PracticeSessionSerializer)
    def post(self, request: Request, session_id) -> Response:  # type: ignore[no-untyped-def]
        serializer = AnswerDispositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        summary = discard_answer(
            session_id,
            question_id=data["question_id"],
            repeat=data["action"] == "repeat",
            owner=request.user,
        )
        return Response(PracticeSessionSerializer(summary).data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses=AuthResponseSerializer)
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"].strip().lower()
        user = authenticate(
            request=request,
            username=username,
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise ValidationError("Usuario o contraseña incorrectos.")
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request: Request):
        from practice.models import UserPreference

        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        return preference

    @extend_schema(responses=UserPreferenceSerializer)
    def get(self, request: Request) -> Response:
        return Response(UserPreferenceSerializer(self.get_object(request)).data)

    @extend_schema(request=UserPreferenceSerializer, responses=UserPreferenceSerializer)
    def patch(self, request: Request) -> Response:
        serializer = UserPreferenceSerializer(
            self.get_object(request), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
