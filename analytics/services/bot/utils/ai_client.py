# services/bot/utils/ai_client.py
import os
from openai import OpenAI

def get_openai_client():
    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )


def ask_openai(prompt):
    client = get_openai_client()
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    return response.output_text