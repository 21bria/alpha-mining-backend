from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.inventory_service import get_inventory_review_service
from analytics.services.bot.services.barging_service import get_barging_review_service
from analytics.services.bot.services.quality_service import get_quality_review_service
from analytics.services.bot.services.production_service import get_summary_service
from analytics.services.bot.services.fuel_service import get_fuel_review_service
from analytics.services.bot.services.equipment_service import get_equipment_review_service
from analytics.services.bot.services.weather_service import get_weather_review_service

from analytics.services.bot.services.productivity_service import (
    get_productivity_service
)

from analytics.services.bot.prompts.operational_prompt import operational_prompt
from analytics.services.bot.utils.ai_client import ask_openai


@shared_task
def generate_operational_analysis(schema_name, params, domains):
    with schema_context(schema_name):
        language = params.pop("language", "id")

        context = {}

        if "production" in domains:
            context["production"] = get_summary_service(**params)

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

        prompt = operational_prompt(
            data=context,
            language=language
        )

        return ask_openai(prompt)