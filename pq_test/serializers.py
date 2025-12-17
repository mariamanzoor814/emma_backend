# backend/pq_test/serializers.py
from rest_framework import serializers

from .models import (
    Classroom,
    Quiz,
    Question,
    QuizSession,
    ParticipantSession,
    AnswerRecord,
)


class ClassroomSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")
    members_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Classroom
        fields = [
            "id",
            "name",
            "description",
            "owner",
            "join_code",
            "members_count",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "join_code", "created_at"]


class ClassroomJoinSerializer(serializers.Serializer):
    join_code = serializers.CharField(max_length=12)


class QuestionSerializer(serializers.ModelSerializer):
    effective_time_limit = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "quiz",
            "text",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "weights",
            "time_limit_seconds",
            "effective_time_limit",
            "order",
            "active",
        ]
        read_only_fields = ["id"]

    def get_effective_time_limit(self, obj):
        return obj.effective_time_limit()


class QuizSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")
    owner_username = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "category",
            "owner",
            "owner_username",
            "classroom",
            "status",
            "is_official",
            "default_time_limit_seconds",
            "total_time_limit_seconds",
            "created_at",
            "updated_at",
            "questions",
        ]
        read_only_fields = [
            "id",
            "owner",
            "is_official",
            "created_at",
            "updated_at",
        ]

    def get_owner_username(self, obj):
        return _display_username(obj.owner)


class QuizSessionSerializer(serializers.ModelSerializer):
    host = serializers.ReadOnlyField(source="host.id")
    host_username = serializers.SerializerMethodField()
    quiz_title = serializers.ReadOnlyField(source="quiz.title")
    is_host = serializers.SerializerMethodField()
    is_participant = serializers.SerializerMethodField()

    class Meta:
        model = QuizSession
        fields = [
            "id",
            "quiz",
            "quiz_title",
            "host",
            "host_username",
            "classroom",
            "session_code",
            "mode",
            "status",
            "allow_guests",
            "require_classroom_membership",
            "show_leaderboard",
            "show_names_on_projector",
            "is_public",
            "join_password",
            "current_question",
            "total_time_limit_seconds",
            "total_time_expires_at",
            "created_at",
            "started_at",
            "ended_at",
            "is_host",
            "is_participant",
        ]
        read_only_fields = [
            "id",
            "host",
            "session_code",
            "status",
            "total_time_limit_seconds",
            "total_time_expires_at",
            "created_at",
            "started_at",
            "ended_at",
        ]

    def get_is_host(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.host_id == request.user.id

    def get_is_participant(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # Use prefetched relation if available
        return obj.participants.filter(user=request.user).exists()

    def get_host_username(self, obj):
        return _display_username(obj.host)



class ParticipantSessionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.id")
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = ParticipantSession
        fields = [
            "id",
            "session",
            "user",
            "guest_name",
            "display_name",
            "joined_at",
            "last_active_at",
            "completed",
            "completed_reason",
            "not_done_questions",
        ]
        read_only_fields = [
            "id",
            "session",
            "user",
            "display_name",
            "joined_at",
            "last_active_at",
            "completed",
            "completed_reason",
            "not_done_questions",
        ]

    def get_display_name(self, obj):
        try:
            return obj.display_name()
        except Exception:
            return ""


class AnswerRecordSerializer(serializers.ModelSerializer):
    """
    Used ONLY for per-user result views, never for public stats.
    """

    question_text = serializers.ReadOnlyField(source="question.text")

    class Meta:
        model = AnswerRecord
        fields = [
            "id",
            "participant",
            "question",
            "question_text",
            "selected_option",
            "time_taken_seconds",
            "submitted_at",
            "within_time",
            "score",
        ]
        read_only_fields = [
            "id",
            "participant",
            "question",
            "question_text",
            "submitted_at",
        ]


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.ChoiceField(
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]
    )
    time_taken_seconds = serializers.FloatField(min_value=0.0)


class AggregatedStatsSerializer(serializers.Serializer):
    """
    Aggregated stats we return publicly (no per-user info).
    """

    question_id = serializers.IntegerField()
    total_responses = serializers.IntegerField()
    average_time = serializers.FloatField()
    option_a_count = serializers.IntegerField()
    option_b_count = serializers.IntegerField()
    option_c_count = serializers.IntegerField()
    option_d_count = serializers.IntegerField()
    option_a_pct = serializers.FloatField()
    option_b_pct = serializers.FloatField()
    option_c_pct = serializers.FloatField()
    option_d_pct = serializers.FloatField()
def _display_username(user):
    """
    Return a safe username for display; if the stored username looks like an email,
    strip everything after '@'.
    """
    username = (getattr(user, "username", "") or "").strip()
    if "@" in username:
        username = username.split("@", 1)[0]
    return username or None
