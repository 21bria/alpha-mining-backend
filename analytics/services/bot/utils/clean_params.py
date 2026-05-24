EXCLUDED_AI_PARAMS = [
    "language",
    "chat_context",
]


def clean_service_params(params):
    return {
        k: v
        for k, v in params.items()
        if k not in EXCLUDED_AI_PARAMS
    }