# analytics/services/bot/utils/chat_memory.py

def get_recent_chat_context(session, limit=6):

    messages = session.messages.order_by(
        "-created_at"
    )[:limit]

    return [
        {
            "role": msg.role,
            "message": msg.message,
            "intent": msg.intent,
        }
        for msg in reversed(messages)
    ]