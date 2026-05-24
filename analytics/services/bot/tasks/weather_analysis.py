from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.weather_service import (
    get_weather_review_service
)

from analytics.services.bot.prompts.weather_prompt import (
    weather_review_prompt
)

from analytics.services.bot.utils.ai_client import (
    ask_openai
)


@shared_task
def generate_weather_review(schema_name, params):
    with schema_context(schema_name):
        language = params.pop("language", "id")
        params.pop("chat_context", None)

        data = get_weather_review_service(params)

        prompt = weather_review_prompt(
            data=data,
            language=language
        )

        return ask_openai(prompt)