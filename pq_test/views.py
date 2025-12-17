# backend/pq_test/views.py
from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Classroom,
    Quiz,
    Question,
    QuizSession,
    ParticipantSession,
    AnswerRecord,
)
from .serializers import (
    ClassroomSerializer,
    ClassroomJoinSerializer,
    QuizSerializer,
    QuestionSerializer,
    QuizSessionSerializer,
    ParticipantSessionSerializer,
    AnswerRecordSerializer,
    SubmitAnswerSerializer,
    AggregatedStatsSerializer,
)
from .permissions import (
    IsOwnerOrReadOnly,
    IsOwnerOrHostOrReadOnly,
    IsHostOrReadOnly,
    IsSelfParticipant,
)


class ClassroomViewSet(viewsets.ModelViewSet):
    """
    Allows any authenticated user to create classrooms.
    Owner can edit/delete their own classroom.
    """

    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        return Classroom.objects.filter(Q(owner=user) | Q(members=user)).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["post"], url_path="join")
    def join_classroom(self, request):
        serializer = ClassroomJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["join_code"].upper()

        classroom = get_object_or_404(Classroom, join_code=code)
        classroom.members.add(request.user)
        return Response(
            ClassroomSerializer(classroom, context={"request": request}).data
        )


class QuizViewSet(viewsets.ModelViewSet):
    """
    Quizzes owned by a user or linked to a classroom where they are a member.
    """

    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrHostOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        return Quiz.objects.filter(
            Q(owner=user) | Q(classroom__members=user) | Q(classroom__owner=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        quiz = self.get_object()
        quiz.status = Quiz.STATUS_PUBLISHED
        quiz.save(update_fields=["status"])
        return Response(
            QuizSerializer(quiz, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, pk=None):
        quiz = self.get_object()
        quiz.status = Quiz.STATUS_DRAFT
        quiz.save(update_fields=["status"])
        return Response(
            QuizSerializer(quiz, context={"request": request}).data
        )

    def destroy(self, request, *args, **kwargs):
        """
        Allow quiz deletion by owner, staff, or any session host of the quiz.
        Cascade remove related sessions/participants/answers to avoid FK protect.
        """
        quiz = self.get_object()
        user = request.user
        is_allowed = (
            getattr(quiz, "owner_id", None) == getattr(user, "id", None)
            or getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or quiz.sessions.filter(host=user).exists()
        )
        if not is_allowed:
            return Response(
                {"detail": "Not allowed to delete this quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            # Remove answers first (Question->AnswerRecord is PROTECT)
            AnswerRecord.objects.filter(question__quiz=quiz).delete()
            # Remove sessions and participants
            QuizSession.objects.filter(quiz=quiz).delete()
            # Remove questions then quiz
            quiz.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    Manage questions for quizzes.
    """

    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Question.objects.filter(
            Q(quiz__owner=user)
            | Q(quiz__classroom__members=user)
            | Q(quiz__classroom__owner=user)
            | Q(quiz__sessions__host=user)
        ).distinct()

    def perform_destroy(self, instance):
        # Remove answers first to avoid PROTECT constraint
        AnswerRecord.objects.filter(question=instance).delete()
        return super().perform_destroy(instance)


class QuizSessionViewSet(viewsets.ModelViewSet):
    """
    Hosts create and manage sessions for their quizzes.
    """

    serializer_class = QuizSessionSerializer
    permission_classes = [IsAuthenticated, IsHostOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs_host = QuizSession.objects.filter(host=user)
        qs_participant = QuizSession.objects.filter(participants__user=user)
        return (qs_host | qs_participant).distinct()

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    @action(detail=True, methods=["post"], url_path="start")
    def start_session(self, request, pk=None):
        session = self.get_object()
        session.start()

        # Set total timer if configured on the quiz
        time_limit = session.quiz.total_time_limit_seconds or 0
        if time_limit > 0:
            session.total_time_limit_seconds = time_limit
            session.total_time_expires_at = timezone.now() + timedelta(seconds=time_limit)
        else:
            session.total_time_limit_seconds = 0
            session.total_time_expires_at = None
        session.save(update_fields=["total_time_limit_seconds", "total_time_expires_at"])

        # For async mode, auto-pick first question and broadcast immediately
        initial_payload = None
        if (
            session.mode == QuizSession.MODE_ASYNC
            and session.current_question_id is None
        ):
            first_question = (
                session.quiz.questions.all().order_by("order", "id").first()
            )
            if first_question:
                session.current_question = first_question
                session.save(update_fields=["current_question"])
                channel_layer = get_channel_layer()
                question_payload = {
                    "question_id": first_question.id,
                    "question_text": first_question.text,
                    "option_a": first_question.option_a,
                    "option_b": first_question.option_b,
                    "option_c": first_question.option_c,
                    "option_d": first_question.option_d,
                    "order": first_question.order,
                    "time_limit": first_question.effective_time_limit(),
                }
                initial_payload = question_payload
                async_to_sync(channel_layer.group_send)(
                    f"pq_session_{session.session_code}",
                    {
                        "type": "broadcast_event",
                        "event": "current_question_changed",
                        "data": question_payload,
                    },
                )
                stats = compute_question_stats(session, first_question)
                async_to_sync(channel_layer.group_send)(
                    f"pq_session_{session.session_code}",
                    {
                        "type": "broadcast_event",
                        "event": "stats_update",
                        "data": stats,
                    },
                )

        data = QuizSessionSerializer(session, context={"request": request}).data
        if initial_payload:
            data["current_question_payload"] = initial_payload
        return Response(data)

    @action(detail=True, methods=["post"], url_path="pause")
    def pause_session(self, request, pk=None):
        session = self.get_object()
        session.pause()
        return Response(
            QuizSessionSerializer(session, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="resume")
    def resume_session(self, request, pk=None):
        session = self.get_object()
        session.resume()
        return Response(
            QuizSessionSerializer(session, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="end")
    def end_session(self, request, pk=None):
        session = self.get_object()
        session.end()
        return Response(
            QuizSessionSerializer(session, context={"request": request}).data
        )

    @action(detail=False, methods=["get"], url_path=r"by-code/(?P<session_code>[^/]+)")
    def by_code(self, request, session_code=None):
        """
        GET /api/pq/sessions/by-code/<session_code>/
        Returns session + quiz (with questions) for host or joined participant.
        """
        session = get_object_or_404(
            QuizSession.objects.select_related("quiz"), session_code=session_code
        )

        is_host = session.host_id == request.user.id
        is_participant = session.participants.filter(user=request.user).exists()
        if not is_host and not is_participant:
            return Response(
                {"detail": "Not allowed for this session."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Mark participant completion if total timer expired
        if session.total_time_expires_at and timezone.now() > session.total_time_expires_at:
            participant = session.participants.filter(user=request.user).first()
            if participant and not participant.completed:
                missing = list(
                    session.quiz.questions.exclude(
                        answers__participant=participant
                    ).values_list("id", flat=True)
                )
                participant.completed = True
                participant.completed_reason = "time_expired"
                participant.not_done_questions = missing
                participant.save(
                    update_fields=["completed", "completed_reason", "not_done_questions", "last_active_at"]
                )

        session_data = QuizSessionSerializer(
            session, context={"request": request}
        ).data
        quiz_data = QuizSerializer(
            session.quiz, context={"request": request}
        ).data
        payload = {"session": session_data, "quiz": quiz_data}

        # Always include question stats so participants can see results later
        payload["question_stats"] = [
            compute_question_stats(session, q)
            for q in session.quiz.questions.all()
        ]

        if is_host:
            participants = ParticipantSessionSerializer(
                session.participants.all(),
                many=True,
                context={"request": request},
            ).data
            payload["participants"] = participants
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="analytics")
    def analytics(self, request, pk=None):
        session = self.get_object()
        user = request.user
        if session.host_id != getattr(user, "id", None) and not getattr(
            user, "is_staff", False
        ) and not getattr(user, "is_superuser", False):
            return Response(
                {"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN
            )
        participants = ParticipantSessionSerializer(
            session.participants.all(),
            many=True,
            context={"request": request},
        ).data
        question_stats = [
            compute_question_stats(session, q) for q in session.quiz.questions.all()
        ]
        return Response(
            {"participants": participants, "question_stats": question_stats},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"by-code/(?P<session_code>[^/]+)/projector",
    )
    def projector_view(self, request, session_code=None):
        """
        Host-only endpoint for projector data.
        Returns all questions (active) and stats when the session has ended.
        """
        session = get_object_or_404(
            QuizSession.objects.select_related("quiz", "host").prefetch_related(
                "quiz__questions"
            ),
            session_code=session_code,
        )

        if session.host_id != getattr(request.user, "id", None):
            return Response(
                {"detail": "Projector view is host-only."},
                status=status.HTTP_403_FORBIDDEN,
            )

        quiz = session.quiz
        questions = quiz.questions.filter(active=True).order_by("order", "id")
        question_data = QuestionSerializer(
            questions, many=True, context={"request": request}
        ).data

        payload = {
            "session": QuizSessionSerializer(
                session, context={"request": request}
            ).data,
            "quiz": QuizSerializer(quiz, context={"request": request}).data,
            "questions": question_data,
        }

        if session.status == QuizSession.STATUS_ENDED:
            payload["question_stats"] = [
                compute_question_stats(session, q) for q in questions
            ]

        return Response(payload)

    # 🔹 NEW ACTION: public_live
    @action(detail=False, methods=["get"], url_path="public-live")
    def public_live(self, request):
        """
        GET /api/pq/sessions/public-live/

        Returns all LIVE, PUBLIC sessions.
        Serializer includes is_host / is_participant so frontend
        can show 'Host dashboard' vs 'Join & play'.
        """
        include_async = request.query_params.get("include_async") in {"1", "true", "True"}
        qs = QuizSession.objects.select_related("quiz", "host").filter(
            is_public=True,
            status=QuizSession.STATUS_LIVE,
        )
        if not include_async:
            qs = qs.filter(mode=QuizSession.MODE_LIVE)
        data = QuizSessionSerializer(
            qs, many=True, context={"request": request}
        ).data
        return Response(data)

class JoinSessionView(APIView):
    """
    POST /api/pq/sessions/<session_code>/join/

    Body:
      { "join_password": "optional-password-or-key" }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, session_code):
        session = get_object_or_404(QuizSession, session_code=session_code)

        if session.total_time_expires_at and timezone.now() > session.total_time_expires_at:
            return Response(
                {"detail": "This session has ended (time limit reached)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if session.require_classroom_membership and session.classroom:
            if not (
                session.classroom.owner_id == request.user.id
                or session.classroom.members.filter(id=request.user.id).exists()
            ):
                return Response(
                    {"detail": "You are not a member of this classroom."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        join_password = request.data.get("join_password", "")

        if not session.is_public and session.join_password:
            if join_password != session.join_password:
                return Response(
                    {"detail": "Invalid session password/key."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        participant, created = ParticipantSession.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={},
        )

        data = ParticipantSessionSerializer(
            participant, context={"request": request}
        ).data

        # Notify host/projector via websocket that a participant joined
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"pq_session_{session.session_code}",
            {
                "type": "broadcast_event",
                "event": "participant_joined",
                "data": data,
            },
        )
        return Response(data, status=status.HTTP_200_OK)


class SetCurrentQuestionView(APIView):
    """
    HTTP fallback for host to change question (if WS blocked).
    POST /api/pq/sessions/<session_code>/set-current-question/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, session_code):
        session = get_object_or_404(
            QuizSession.objects.select_related("quiz"), session_code=session_code
        )
        if session.host_id != request.user.id and not request.user.is_staff and not request.user.is_superuser:
            return Response({"detail": "Not host."}, status=status.HTTP_403_FORBIDDEN)

        question_id = request.data.get("question_id")
        try:
            question = Question.objects.get(id=question_id, quiz=session.quiz)
        except Question.DoesNotExist:
            return Response(
                {"detail": "Question not part of this quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark session live when host selects the first question
        if session.status == QuizSession.STATUS_NOT_STARTED:
            session.start()

        session.current_question = question
        session.save(update_fields=["current_question"])

        channel_layer = get_channel_layer()
        question_payload = {
            "question_id": question.id,
            "question_text": question.text,
            "option_a": question.option_a,
            "option_b": question.option_b,
            "option_c": question.option_c,
            "option_d": question.option_d,
            "order": question.order,
            "time_limit": question.effective_time_limit(),
        }

        async_to_sync(channel_layer.group_send)(
            f"pq_session_{session.session_code}",
            {
                "type": "broadcast_event",
                "event": "current_question_changed",
                "data": question_payload,
            },
        )

        stats = compute_question_stats(session, question)
        async_to_sync(channel_layer.group_send)(
            f"pq_session_{session.session_code}",
            {
                "type": "broadcast_event",
                "event": "stats_update",
                "data": stats,
            },
        )

        return Response({"detail": "Question broadcast."}, status=status.HTTP_200_OK)


class SubmitAnswerView(APIView):
    """
    POST /api/pq/sessions/<session_code>/answer/
    Body: { "question_id": ..., "selected_option": "A", "time_taken_seconds": 3.2 }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, session_code):
        session = get_object_or_404(QuizSession, session_code=session_code)

        # Total quiz timer enforcement
        if session.total_time_expires_at and timezone.now() > session.total_time_expires_at:
            participant = ParticipantSession.objects.filter(
                session=session, user=request.user
            ).first()
            if participant:
                missing = list(
                    session.quiz.questions.exclude(
                        answers__participant=participant
                    ).values_list("id", flat=True)
                )
                participant.completed = True
                participant.completed_reason = "time_expired"
                participant.not_done_questions = missing
                participant.save(update_fields=["completed", "completed_reason", "not_done_questions", "last_active_at"])
            return Response(
                {"detail": "Quiz time is over. Unanswered questions marked as not done."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If host hasn't explicitly started, allow first submission to start it
        if session.status == QuizSession.STATUS_NOT_STARTED:
            session.start()

        if session.status != QuizSession.STATUS_LIVE:
            return Response(
                {"detail": "Session is not live."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participant, _ = ParticipantSession.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={},
        )

        data = request.data or {}
        question_id = data.get("question_id")
        if question_id in [None, ""]:
            # Fallback to the session's current question if not provided
            question_id = getattr(session, "current_question_id", None)
        try:
            question_id = int(question_id)
        except Exception:
            return Response(
                {"detail": "question_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_option = (data.get("selected_option") or "").upper()
        if selected_option not in {"A", "B", "C", "D"}:
            return Response(
                {"detail": "selected_option must be one of A, B, C, D."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            time_taken = float(data.get("time_taken_seconds", 0)) or 0.0
        except Exception:
            time_taken = 0.0

        question = get_object_or_404(Question, id=question_id, quiz=session.quiz)

        score = 0.0
        if question.correct_option and selected_option == question.correct_option:
            score = 1.0
        # For 8PQ we will use weights later

        answer, created = AnswerRecord.objects.update_or_create(
            participant=participant,
            question=question,
            defaults={
                "selected_option": selected_option,
                "time_taken_seconds": time_taken,
                "within_time": True,
                "score": score,
            },
        )

        # Mark completion if all questions answered
        remaining = (
            session.quiz.questions.exclude(answers__participant=participant)
            .exclude(id=question.id)
            .count()
        )
        if remaining == 0:
            participant.completed = True
            participant.completed_reason = "answered_all"
            participant.not_done_questions = []
            participant.save(
                update_fields=["completed", "completed_reason", "not_done_questions", "last_active_at"]
            )

        channel_layer = get_channel_layer()
        payload = compute_question_stats(session, question)
        async_to_sync(channel_layer.group_send)(
            f"pq_session_{session.session_code}",
            {
                "type": "broadcast_event",
                "event": "stats_update",
                "data": payload,
            },
        )

        return Response(
            AnswerRecordSerializer(answer, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class MyResultsView(APIView):
    """
    GET /api/pq/my/results/
    List of ParticipantSessions for current user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        participant_sessions = ParticipantSession.objects.filter(user=request.user)
        data = ParticipantSessionSerializer(
            participant_sessions, many=True, context={"request": request}
        ).data
        return Response(data)


class MyResultDetailView(APIView):
    """
    GET /api/pq/my/results/<participant_id>/
    Detailed answers for a specific ParticipantSession that belongs to the user.
    """

    permission_classes = [IsAuthenticated, IsSelfParticipant]

    def get_object(self, request, participant_id):
        participant = get_object_or_404(ParticipantSession, id=participant_id)
        self.check_object_permissions(request, participant)
        return participant

    def get(self, request, participant_id):
        participant = self.get_object(request, participant_id)
        answers = participant.answers.select_related("question").all()
        data = {
            "participant": ParticipantSessionSerializer(
                participant, context={"request": request}
            ).data,
            "answers": AnswerRecordSerializer(
                answers, many=True, context={"request": request}
            ).data,
        }
        return Response(data)
    
class MySessionResultView(APIView):
    """
    GET /api/pq/sessions/<session_code>/my-answers/
    Returns this user's answers for a given session (question_id + selected_option).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, session_code):
      session = get_object_or_404(QuizSession, session_code=session_code)
      participant = get_object_or_404(
          ParticipantSession, session=session, user=request.user
      )
      answers = participant.answers.values("question_id", "selected_option")
      return Response({"answers": list(answers)}, status=status.HTTP_200_OK)



class SessionStatsView(APIView):
    """
    GET /api/pq/sessions/<session_code>/stats/current-question/
    Returns aggregated stats for the current question in a session.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, session_code):
        session = get_object_or_404(QuizSession, session_code=session_code)

        question = session.current_question
        if not question:
            return Response(
                {"detail": "No active question for this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = compute_question_stats(session, question)
        serializer = AggregatedStatsSerializer(payload)
        return Response(serializer.data)


def compute_question_stats(session: QuizSession, question: Question):
    """
    Compute aggregated stats for a question within a session.
    """

    answers = AnswerRecord.objects.filter(
        question=question,
        participant__session=session,
    )

    agg = answers.aggregate(
        total_responses=Count("id"),
        avg_time=Avg("time_taken_seconds"),
        a_count=Count("id", filter=Q(selected_option="A")),
        b_count=Count("id", filter=Q(selected_option="B")),
        c_count=Count("id", filter=Q(selected_option="C")),
        d_count=Count("id", filter=Q(selected_option="D")),
    )

    total = agg["total_responses"] or 0

    # compute percentages safely
    if total > 0:
        a_pct = (agg["a_count"] or 0) * 100.0 / total
        b_pct = (agg["b_count"] or 0) * 100.0 / total
        c_pct = (agg["c_count"] or 0) * 100.0 / total
        d_pct = (agg["d_count"] or 0) * 100.0 / total
    else:
        a_pct = b_pct = c_pct = d_pct = 0.0

    return {
        "question_id": question.id,
        "total_responses": total,
        "average_time": agg["avg_time"] or 0.0,
        "option_a_count": agg["a_count"] or 0,
        "option_b_count": agg["b_count"] or 0,
        "option_c_count": agg["c_count"] or 0,
        "option_d_count": agg["d_count"] or 0,
        "option_a_pct": a_pct,
        "option_b_pct": b_pct,
        "option_c_pct": c_pct,
        "option_d_pct": d_pct,
    }
