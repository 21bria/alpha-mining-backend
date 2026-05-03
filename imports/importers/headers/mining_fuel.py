# imports/header_configs/fuel.py
from .base import make_header_config

FUEL_TRANSPOSE_HEADERS = make_header_config(
    required=[
        "iup_code",
        "date",
    ],
    allowed=[
        "iup_code",
        "date",
    ],
    aliases={
        "iup": "iup_code",
        "iup code": "iup_code",
        "iup_code": "iup_code",
        "tanggal": "date",
        "date": "date",
    },
)