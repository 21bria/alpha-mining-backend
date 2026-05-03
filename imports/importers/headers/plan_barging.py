# imports/header_configs/fuel.py
from .base import make_header_config

PLAN_BARGING_TRANSPOSE_HEADERS = make_header_config(
    required=[
        "iup_code",
        "plan_date",
    ],
    allowed=[
        "iup_code",
        "plan_date",
    ],
    aliases={
        "iup": "iup_code",
        "iup code": "iup_code",
        "iup_code": "iup_code",
        "plan_date": "plan_date",
        "date": "date",
    },
)