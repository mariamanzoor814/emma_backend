# backend/pq_test/consumers.py
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from .models import QuizSession, Question
from .views import compute_question_stats


class QuizSessionConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket for a live quiz session.

    Group name: pq_session_<session_code>

    Incoming actions:
    - "join"                -> client says "I'm here"
    - "host_set_question"   -> host changes current question
    - "host_show_results"   -> host shows results without ending
    - "host_end"            -> host ends the session

    Outgoing events:
    - event: "joined"
    - event: "current_question_changed"
    - event: "stats_update"
    - event: "session_ended"
    """

    async def connect(self):
        self.session_code = self.scope["url_route"]["kwargs"]["session_code"]
        self.group_name = f"pq_session_{self.session_code}"

        user = self.scope.get("user")
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close(code=4401)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        user = self.scope.get("user")

        if action == "join":
            await self.send_json({"event": "joined", "data": {"user_id": user.id}})
            return

        if action == "host_set_question":
            await self._handle_host_set_question(user, content)
        elif action == "host_show_results":
            await self._handle_host_show_results(user)
        elif action == "host_end":
            await self._handle_host_end(user)

    async def _handle_host_set_question(self, user, content):
        session = await self._get_session()

        if session.host_id != user.id and not user.is_staff and not user.is_superuser:
            await self.send_json({"event": "error", "data": {"detail": "Not host"}})
            return

        question_id = content.get("question_id")
        if not question_id:
            await self.send_json(
                {"event": "error", "data": {"detail": "question_id required"}}
            )
            return

        question = await self._get_question(session, question_id)
        if not question:
            await self.send_json(
                {"event": "error", "data": {"detail": "Question not part of this quiz"}}
            )
            return

        await self._set_current_question(session, question)

        # compute time limit inside sync context to avoid async DB access
        time_limit = await database_sync_to_async(lambda: question.effective_time_limit())()

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_event",
                "event": "current_question_changed",
                "data": {
                    "question_id": question.id,
                    "question_text": question.text,
                    "option_a": question.option_a,
                    "option_b": question.option_b,
                    "option_c": question.option_c,
                    "option_d": question.option_d,
                    "time_limit": time_limit,
                    "order": question.order,
                },
            },
        )

        stats = await self._compute_stats(session, question)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_event",
                "event": "stats_update",
                "data": stats,
            },
        )

    async def _handle_host_end(self, user):
        session = await self._get_session()

        if session.host_id != user.id and not user.is_staff and not user.is_superuser:
            await self.send_json({"event": "error", "data": {"detail": "Not host"}})
            return

        await self._end_session(session)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_event",
                "event": "session_ended",
                "data": {},
            },
        )

    async def _handle_host_show_results(self, user):
        session = await self._get_session()

        if session.host_id != user.id and not user.is_staff and not user.is_superuser:
            await self.send_json({"event": "error", "data": {"detail": "Not host"}})
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "broadcast_event",
                "event": "session_results",
                "data": {},
            },
        )

    async def broadcast_event(self, event):
        await self.send_json(
            {
                "event": event["event"],
                "data": event.get("data", {}),
            }
        )

    @database_sync_to_async
    def _get_session(self):
        return QuizSession.objects.select_related("quiz").get(
            session_code=self.session_code
        )

    @database_sync_to_async
    def _get_question(self, session, question_id):
        try:
            return (
                Question.objects.select_related("quiz")
                .filter(id=question_id, quiz=session.quiz)
                .get()
            )
        except Question.DoesNotExist:
            return None

    @database_sync_to_async
    def _set_current_question(self, session, question):
        session.current_question = question
        session.save(update_fields=["current_question"])

    @database_sync_to_async
    def _end_session(self, session):
        session.end()

    @database_sync_to_async
    def _compute_stats(self, session, question):
        return compute_question_stats(session, question)
