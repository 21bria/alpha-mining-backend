# views/ai/chat_stream.py
# streaming ini tidak pakai Celery, jadi proses query + AI berjalan langsung di request.
#  Cocok untuk UX realtime, tapi untuk report sangat berat nanti tetap bisa pakai mode Celery.

import json

from django.db import connection
from django.http import StreamingHttpResponse

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from analytics.models import AIChatSession, AIChatMessage

from analytics.services.bot.parsers.intent_parser import (
    is_allowed_question,
    is_greeting,
)
from analytics.services.bot.parsers.language_parser import detect_language
from analytics.services.bot.parsers.query_parser import parse_query

from analytics.services.bot.utils.ai_stream_client import stream_openai
from analytics.services.bot.utils.clean_params import clean_service_params
from analytics.services.bot.utils.chat_memory import get_recent_chat_context

from analytics.services.bot.services.production_service import get_summary_service
from analytics.services.bot.services.quality_service import get_quality_review_service
from analytics.services.bot.services.barging_service import get_barging_review_service
from analytics.services.bot.services.inventory_service import get_inventory_review_service
from analytics.services.bot.services.fuel_service import get_fuel_review_service
from analytics.services.bot.services.weather_service import get_weather_review_service
from analytics.services.bot.services.equipment_service import get_equipment_review_service
from analytics.services.bot.services.blending_service import get_blending_review_service
from analytics.services.bot.services.productivity_service import get_productivity_service

from analytics.services.bot.prompts.production_prompt import production_review_prompt
from analytics.services.bot.prompts.quality_prompt import quality_review_prompt
from analytics.services.bot.prompts.barging_prompt import barging_review_prompt
from analytics.services.bot.prompts.inventory_prompt import inventory_review_prompt
from analytics.services.bot.prompts.fuel_prompt import fuel_review_prompt
from analytics.services.bot.prompts.weather_prompt import weather_review_prompt
from analytics.services.bot.prompts.equipment_prompt import equipment_review_prompt
from analytics.services.bot.prompts.blending_prompt import blending_review_prompt
from analytics.services.bot.prompts.operational_prompt import operational_prompt


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


def sse_event(payload):
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_operational_context(params, domains):
    context = {}

    service_params = clean_service_params(params)

    if "production" in domains:
        context["production"] = get_summary_service(**service_params)

    if "inventory" in domains:
        context["inventory"] = get_inventory_review_service(params)

    if "barging" in domains:
        context["barging"] = get_barging_review_service(params)

    if "quality" in domains:
        context["quality"] = get_quality_review_service(params)

    if "fuel" in domains:
        context["fuel"] = get_fuel_review_service(params)

    if "equipment" in domains:
        context["equipment"] = get_equipment_review_service(params)

    if "weather" in domains:
        context["weather"] = get_weather_review_service(params)

    if "productivity" in domains:
        context["productivity"] = get_productivity_service(params)

    return context


def build_prompt_by_intent(intent, domains, params, language):
    if intent == "operational_analysis":
        data = build_operational_context(params, domains)
        return operational_prompt(
            data=data,
            language=language,
        )

    if intent == "quality_review":
        data = get_quality_review_service(params)
        return quality_review_prompt(
            data=data,
            language=language,
        )

    if intent == "barging_review":
        data = get_barging_review_service(params)
        return barging_review_prompt(
            data=data,
            language=language,
        )

    if intent == "inventory_review":
        data = get_inventory_review_service(params)
        return inventory_review_prompt(
            data=data,
            language=language,
        )

    if intent == "fuel_review":
        data = get_fuel_review_service(params)
        return fuel_review_prompt(
            data=data,
            language=language,
        )

    if intent == "weather_review":
        data = get_weather_review_service(params)
        return weather_review_prompt(
            data=data,
            language=language,
        )

    if intent == "equipment_review":
        data = get_equipment_review_service(params)
        return equipment_review_prompt(
            data=data,
            language=language,
        )

    if intent == "blending_review":
        data = get_blending_review_service(params)
        return blending_review_prompt(
            data=data,
            language=language,
        )

    service_params = clean_service_params(params)

    data = get_summary_service(**service_params)

    return production_review_prompt(
        data=data,
        language=language,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def ai_chat_stream(request):
    message = request.data.get("message", "").strip()

    if not message:
        return StreamingHttpResponse(
            iter([
                sse_event({
                    "error": "Message tidak boleh kosong."
                })
            ]),
            content_type="text/event-stream"
        )

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

        AIChatMessage.objects.create(
            session=session,
            role="user",
            message=message,
            intent="greeting"
        )

        AIChatMessage.objects.create(
            session=session,
            role="assistant",
            message=reply,
            intent="greeting"
        )

        return StreamingHttpResponse(
            iter([
                sse_event({
                    "session_id": str(session.id)
                }),
                sse_event({
                    "text": reply
                }),
                sse_event({
                    "done": True
                }),
            ]),
            content_type="text/event-stream"
        )

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

        AIChatMessage.objects.create(
            session=session,
            role="user",
            message=message,
            intent="blocked"
        )

        AIChatMessage.objects.create(
            session=session,
            role="assistant",
            message=reply,
            intent="blocked"
        )

        return StreamingHttpResponse(
            iter([
                sse_event({
                    "session_id": str(session.id)
                }),
                sse_event({
                    "text": reply
                }),
                sse_event({
                    "done": True
                }),
            ]),
            content_type="text/event-stream"
        )

    parsed = parse_query(message)

    intent = parsed["intent"]
    domains = parsed.get("domains", [])
    params = parsed["params"]

    params["iup_id"] = request.data.get("iup_id")
    params["language"] = language
    params["chat_context"] = get_recent_chat_context(session)

    AIChatMessage.objects.create(
        session=session,
        role="user",
        message=message,
        intent=intent
    )

    def event_stream():
        full_text = ""

        try:
            yield sse_event({
                "session_id": str(session.id),
                "intent": intent,
                "domains": domains,
            })

            prompt = build_prompt_by_intent(
                intent=intent,
                domains=domains,
                params=params,
                language=language,
            )

            for chunk in stream_openai(prompt):
                full_text += chunk

                yield sse_event({
                    "text": chunk
                })

            AIChatMessage.objects.create(
                session=session,
                role="assistant",
                message=full_text,
                intent=intent
            )

            yield sse_event({
                "done": True
            })

        except Exception as e:
            yield sse_event({
                "error": str(e)
            })

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )

    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"

    return response