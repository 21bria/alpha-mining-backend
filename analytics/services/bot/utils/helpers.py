def safe_pop(data, key, default=None):
    return data.pop(key, default) if isinstance(data, dict) else default