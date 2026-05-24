from celery import shared_task
from django_tenants.utils import schema_context

from analytics.services.bot.services.equipment_service import (
    get_equipment_review_service
)

from analytics.services.bot.prompts.equipment_prompt import (
    equipment_review_prompt
)

from analytics.services.bot.utils.ai_client import (
    ask_openai
)


@shared_task
def generate_equipment_review(schema_name, params):
    with schema_context(schema_name):
        language = params.pop("language", "id")

        data = get_equipment_review_service(params)

        prompt = equipment_review_prompt(
            data=data,
            language=language
        )

        result = ask_openai(prompt)

        return result