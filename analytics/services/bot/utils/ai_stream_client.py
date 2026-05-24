# analytics/services/bot/utils/ai_stream_client.py

import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def stream_openai(prompt):
    stream = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        stream=True,
    )

    for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta