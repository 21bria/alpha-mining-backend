def safe_text(value):
    return "" if value is None else str(value)

def clean_params(params):
    return {
        k: v for k, v in params.items()
        if v not in [None, ""]
    }