# report/analyst/export_registry.py
EXPORT_REGISTRY = {}


def register_exporter(module_name):
    def decorator(func):
        EXPORT_REGISTRY[module_name] = func
        return func
    return decorator


def get_exporter(module_name):
    exporter = EXPORT_REGISTRY.get(module_name)
    if not exporter:
        raise ValueError(f"No exporter registered for module '{module_name}'")
    return exporter