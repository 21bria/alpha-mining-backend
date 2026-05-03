from datetime import datetime, date, time
def json_safe_dict(data: dict) -> dict:
    safe = {}

    for k, v in data.items():
        if isinstance(v, (datetime, date, time)):
            safe[k] = v.isoformat()
        else:
            safe[k] = v

    return safe