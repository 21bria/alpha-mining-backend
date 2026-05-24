# analytics/services/bot/tasks/blending_review.py

from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.blending_service import (
    get_blending_review_service
)

from analytics.services.bot.prompts.blending_prompt import (
    blending_review_prompt
)

from analytics.services.bot.utils.ai_client import (
    ask_openai
)


@shared_task
def generate_blending_review(schema_name, params):
    with schema_context(schema_name):
        language = params.pop("language", "id")

        data = get_blending_review_service(params)

        prompt = blending_review_prompt(
            data=data,
            language=language
        )

        return ask_openai(prompt)