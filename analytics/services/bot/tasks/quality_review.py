from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.quality_service import get_quality_review_service
from analytics.services.bot.utils.ai_client import ask_openai
from analytics.services.bot.prompts.quality_prompt import quality_review_prompt


@shared_task
def generate_quality_review(schema_name, params):
    with schema_context(schema_name):
        language = params.pop("language", "id")

        data = get_quality_review_service(params)

        prompt = quality_review_prompt(
            data=data,
            language=language
        )

        result = ask_openai(prompt)

        return result