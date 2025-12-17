# backend/pq_test/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClassroomViewSet,
    QuizViewSet,
    QuestionViewSet,
    QuizSessionViewSet,
    JoinSessionView,
    SetCurrentQuestionView,
    SubmitAnswerView,
    MyResultsView,
    MyResultDetailView,
    SessionStatsView,
    MySessionResultView,
)

router = DefaultRouter()
router.register(r"classrooms", ClassroomViewSet, basename="classroom")
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"sessions", QuizSessionViewSet, basename="quizsession")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "sessions/<str:session_code>/join/",
        JoinSessionView.as_view(),
        name="pq-join-session",
    ),
    path(
        "sessions/<str:session_code>/set-current-question/",
        SetCurrentQuestionView.as_view(),
        name="pq-set-current-question",
    ),
    path(
        "sessions/<str:session_code>/answer/",
        SubmitAnswerView.as_view(),
        name="pq-submit-answer",
    ),
    path("my/results/", MyResultsView.as_view(), name="pq-my-results"),
    path(
        "my/results/<int:participant_id>/",
        MyResultDetailView.as_view(),
        name="pq-my-result-detail",
    ),
    path(
        "sessions/<str:session_code>/stats/current-question/",
        SessionStatsView.as_view(),
        name="pq-session-stats-current",
    ),
    path(
    "sessions/<str:session_code>/my-answers/",
    MySessionResultView.as_view(),
    name="pq_my_session_answers",
),
]
