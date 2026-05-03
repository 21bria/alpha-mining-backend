def make_header_config(required, allowed=None, aliases=None):
    return {
        "required": set(required),
        "allowed": set(allowed or required),
        "aliases": aliases or {},
    }