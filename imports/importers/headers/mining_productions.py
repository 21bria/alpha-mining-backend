from .base import make_header_config

PRODUCTIONS_MINING_HEADERS = make_header_config(
    required=[
    "up_code",
    "date_production",
    "vendors",
    "shift",
    "time_hauling",
    "loader",
    "parsing",
    "loader_class",
    "hauler",
    "loading_point",
    "dumping_point",
    "material",
    "category"

    ],
    allowed=[
    "iup_code",
    "date_production",
    "vendors",
    "shift",
    "time_hauling",
    "loader",
    "parsing",
    "loader_class",
    "hauler",
    "loading_point",
    "dumping_point",
    "dome",
    "material",
    "category",
    "distance",
    "block_id",
    "from_rl",
    "to_rl",
    "ritase",
    "direct",
    "remarks"
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
        "date": "date_production",
        "time": "time_hauling",
        "loading_point": "loading",
        "dumping": "dumping_point",
        "pile_id": "pile",
        "pile_id": "dome",
        "pile_id": "dome_point"
    },
)