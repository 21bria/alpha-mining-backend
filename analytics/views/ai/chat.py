# views/ai/chat.py

from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from analytics.models import AIChatSession, AIChatMessage, AIReport

from analytics.services.bot.parsers.intent_parser import is_allowed_question, is_greeting
from analytics.services.bot.parsers.language_parser import detect_language
from analytics.services.bot.parsers.query_parser import parse_query

from analytics.services.bot.tasks.production_review import generate_production_review
from analytics.services.bot.tasks.quality_review import generate_quality_review
from analytics.services.bot.tasks.barging_review import generate_barging_review
from analytics.services.bot.tasks.inventory_review import generate_inventory_review
from analytics.services.bot.tasks.operational_analysis import generate_operational_analysis
from analytics.services.bot.tasks.fuel_analysis import generate_fuel_review
from analytics.services.bot.tasks.weather_analysis import generate_weather_review
from analytics.services.bot.tasks.equipment_review import generate_equipment_review
from analytics.services.bot.tasks.blending_review import  generate_blending_review

# Memory call recennt :
from analytics.services.bot.utils.chat_memory import get_recent_chat_context


def get_or_create_session(request, message):
    session_id = request.data.get("session_id")

    if session_id:
        session = AIChatSession.objects.filter(id=session_id).first()
        if session:
            return session

    return AIChatSession.objects.create(
        user=request.user if request.user.is_authenticated else None,
        title=message[:100] or "New Chat"
    )


def save_direct_reply(session, message, reply, intent="direct_reply"):
    AIChatMessage.objects.create(
        session=session,
        role="user",
        message=message,
        intent=intent
    )

    AIChatMessage.objects.create(
        session=session,
        role="assistant",
        message=reply,
        intent=intent
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def ai_chat(request):
    message = request.data.get("message", "").strip()

    if not message:
        return Response({
            "blocked": True,
            "direct_reply": True,
            "message": "Message tidak boleh kosong."
        }, status=200)

    session = get_or_create_session(request, message)

    language = request.data.get("language") or detect_language(message)

    if is_greeting(message):
        reply = (
            "Hello, I am Alpha Assistant — AI Assistant for mining operational analysis. "
            "I can help analyze production, quality, barging, selling, inventory, KPI, "
            "equipment, fuel, and weather operational impacts."
            if language == "en"
            else
            "Halo, saya Alpha Assistant — AI Assistant untuk analisa operasional mining. "
            "Saya dapat membantu analisa production, quality, barging, selling, inventory, KPI, "
            "equipment, fuel, dan dampak cuaca terhadap operasional tambang."
        )

        save_direct_reply(session, message, reply, "greeting")

        return Response({
            "blocked": False,
            "direct_reply": True,
            "session_id": str(session.id),
            "message": reply
        }, status=200)

    if not is_allowed_question(message):
        reply = (
            "Sorry, Alpha Assistant only supports mining operational analysis, "
            "including production, quality, barging, selling, inventory, KPI, "
            "equipment, fuel, and weather operational impacts."
            if language == "en"
            else
            "Maaf, Alpha Assistant hanya dapat membantu analisa operasional mining "
            "seperti production, quality, barging, selling, inventory, KPI, equipment, "
            "fuel, dan dampak cuaca terhadap operasional tambang."
        )

        save_direct_reply(session, message, reply, "blocked")

        return Response({
            "blocked": True,
            "direct_reply": True,
            "session_id": str(session.id),
            "message": reply
        }, status=200)

    parsed = parse_query(message)

    intent = parsed["intent"]
    domains = parsed.get("domains", [])
    params = parsed["params"]

    params["iup_id"] = request.data.get("iup_id")
    params["language"] = language

    chat_context = get_recent_chat_context(session)

    params["chat_context"] = chat_context

    AIChatMessage.objects.create(
        session=session,
        role="user",
        message=message,
        intent=intent
    )

    if intent == "operational_analysis":
        task = generate_operational_analysis.delay(connection.schema_name, params, domains)
    elif intent == "quality_review":
        task = generate_quality_review.delay(connection.schema_name, params)
    elif intent == "barging_review":
        task = generate_barging_review.delay(connection.schema_name, params)
    elif intent == "inventory_review":
        task = generate_inventory_review.delay(connection.schema_name, params)
    elif intent == "fuel_review":
        task = generate_fuel_review.delay(connection.schema_name, params)
    elif intent == "equipment_review":
        task = generate_equipment_review.delay(connection.schema_name, params)
    elif intent == "weather_review":
        task = generate_weather_review.delay(connection.schema_name, params)
    elif intent == "blending_review":
        task = generate_blending_review.delay(connection.schema_name,params)
    else:
        task = generate_production_review.delay(connection.schema_name, params)

    report = AIReport.objects.create(
        session=session,
        task_id=task.id,
        report_type=intent,
        intent=intent,
        params=params,
        status="PENDING",
        created_by=request.user if request.user.is_authenticated else None
    )

    return Response({
        "task_id": task.id,
        "session_id": str(session.id),
        "report_id": str(report.id),
        "intent": intent
    })