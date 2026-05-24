from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.production_service import get_summary_service
from analytics.services.bot.utils.ai_client import ask_openai
from analytics.services.bot.utils.clean_params import clean_service_params
from analytics.services.bot.prompts.production_prompt import production_review_prompt

@shared_task
def generate_production_review(schema_name, params):
    with schema_context(schema_name):
        language = params.pop("language", "id")
        params.pop("chat_context", None)

        data = get_summary_service(**params)

        prompt = production_review_prompt(
            data=data,
            language=language,
        )

        return ask_openai(prompt)