# backend/pq_test/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
import secrets
import string


def generate_join_code(length: int = 8) -> str:
    """
    Generate a random code used for joining classrooms or sessions.
    """
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


class Classroom(models.Model):
    """
    Any user can create a classroom and invite others via join_code.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_classrooms",
    )

    join_code = models.CharField(
        max_length=12,
        unique=True,
        default=generate_join_code,
        help_text="Code used to join this classroom.",
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="joined_classrooms",
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Quiz(models.Model):
    """
    Reusable quiz template (8PQ or any custom quiz).
    Owned by any user, optionally attached to a Classroom.
    """

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_quizzes",
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quizzes",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    is_official = models.BooleanField(
        default=False,
        help_text="Mark as official EMMA/8PQ template (admins only).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    default_time_limit_seconds = models.PositiveIntegerField(
        default=60,
        help_text="Default time limit per question in seconds.",
    )
    total_time_limit_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Optional total time limit for the whole quiz in seconds; 0 = no limit.",
    )

    def __str__(self) -> str:
        return self.title


class Question(models.Model):
    """
    Multiple-choice single-answer question.
    For 8PQ you can use `weights` JSON to map options to piston scores.
    """

    OPTION_A = "A"
    OPTION_B = "B"
    OPTION_C = "C"
    OPTION_D = "D"

    OPTION_CHOICES = [
        (OPTION_A, "A"),
        (OPTION_B, "B"),
        (OPTION_C, "C"),
        (OPTION_D, "D"),
    ]

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )

    text = models.TextField()

    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255, blank=True)
    option_d = models.CharField(max_length=255, blank=True)

    correct_option = models.CharField(
        max_length=1,
        choices=OPTION_CHOICES,
        blank=True,
    )

    weights = models.JSONField(blank=True, null=True)

    time_limit_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Per-question limit in seconds; 0 = use quiz default.",
    )

    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def effective_time_limit(self) -> int:
        if self.time_limit_seconds > 0:
            return self.time_limit_seconds
        return self.quiz.default_time_limit_seconds

    def __str__(self) -> str:
        return f"{self.quiz.title} Q{self.order + 1}"


class QuizSession(models.Model):
    """
    One live (or async) run of a quiz.
    Any user can host a session for quizzes they own or have access to.
    """

    is_public = models.BooleanField(
        default=False,
        help_text="If true, participants can join with just the session code (no password).",
    )
    join_password = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional password/key set by host. Leave empty for public sessions.",
    )

    MODE_LIVE = "live"
    MODE_ASYNC = "async"

    MODE_CHOICES = [
        (MODE_LIVE, "Live"),
        (MODE_ASYNC, "Async"),
    ]

    STATUS_NOT_STARTED = "not_started"
    STATUS_LIVE = "live"
    STATUS_PAUSED = "paused"
    STATUS_ENDED = "ended"

    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, "Not started"),
        (STATUS_LIVE, "Live"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_ENDED, "Ended"),
    ]

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="hosted_sessions",
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )

    session_code = models.CharField(
        max_length=16,
        unique=True,
        default=generate_join_code,
        help_text="Code participants use to join this session.",
    )

    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=MODE_LIVE,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
    )

    allow_guests = models.BooleanField(default=False)
    require_classroom_membership = models.BooleanField(default=False)
    show_leaderboard = models.BooleanField(default=True)

    show_names_on_projector = models.BooleanField(
        default=False,
        help_text="If False, projector view NEVER shows real names.",
    )

    total_time_limit_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Copied from quiz on start; 0 = no total limit.",
    )
    total_time_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the total quiz time ends for everyone.",
    )

    current_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    def start(self):
        if self.status == self.STATUS_NOT_STARTED:
            self.status = self.STATUS_LIVE
            self.started_at = timezone.now()
            self.save(update_fields=["status", "started_at"])

    def pause(self):
        if self.status == self.STATUS_LIVE:
            self.status = self.STATUS_PAUSED
            self.save(update_fields=["status"])

    def resume(self):
        if self.status == self.STATUS_PAUSED:
            self.status = self.STATUS_LIVE
            self.save(update_fields=["status"])

    def end(self):
        if self.status in {self.STATUS_LIVE, self.STATUS_PAUSED}:
            self.status = self.STATUS_ENDED
            self.ended_at = timezone.now()
            self.save(update_fields=["status", "ended_at"])

    def __str__(self) -> str:
        return f"{self.quiz.title} ({self.session_code})"


class ParticipantSession(models.Model):
    """
    One person's participation in a QuizSession.

    IMPORTANT:
    - Detailed results from this object + AnswerRecord will be exposed ONLY
      to this user via APIs.
    - Shared / projector analytics will use ONLY aggregated stats, never
      per-user data.
    """

    session = models.ForeignKey(
        QuizSession,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quiz_participations",
    )

    guest_name = models.CharField(max_length=100, blank=True)

    joined_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    completed = models.BooleanField(default=False)
    completed_reason = models.CharField(max_length=64, blank=True)
    not_done_questions = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["session", "user"],
                name="unique_user_per_session",
                condition=~models.Q(user=None),
            )
        ]

    def display_name(self) -> str:
        if self.user:
            return self.user.get_username()
        return self.guest_name or "Guest"

    def __str__(self) -> str:
        return f"{self.session.session_code} - {self.display_name()}"


class AnswerRecord(models.Model):
    """
    Single answer to a question by a participant.

    Used for:
      - per-user results (only that user can see via API)
      - aggregated stats (percentages per option, visible to others).
    """

    OPTION_CHOICES = Question.OPTION_CHOICES

    participant = models.ForeignKey(
        ParticipantSession,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    selected_option = models.CharField(
        max_length=1,
        choices=OPTION_CHOICES,
    )

    time_taken_seconds = models.FloatField(
        help_text="Client-measured time; validated server-side.",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    within_time = models.BooleanField(default=True)

    score = models.FloatField(default=0)

    class Meta:
        unique_together = ("participant", "question")

    def __str__(self) -> str:
        return f"{self.participant} - Q{self.question_id} ({self.selected_option})"
