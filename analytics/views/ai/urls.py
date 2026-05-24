from django.urls import path

from .chat import ai_chat
from .chat_stream import ai_chat_stream
from .task_result import get_ai_task_result

urlpatterns = [
    path("chat/", ai_chat),
    path("task/<str:task_id>/",get_ai_task_result),
    path("chat-stream/", ai_chat_stream),
]