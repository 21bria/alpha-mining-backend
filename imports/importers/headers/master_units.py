from .base import make_header_config

MASTER_UNIT_HEADERS = make_header_config(
    required=[
        "iup_code",
        "unit_code",
        "unit_model",
        "category",
        "vendors"
    ],
    allowed=[
        "iup_code",
        "unit_code",
        "unit_model",
        "unit_class",
        "brand",
        "category",
        "vendors",
        "commisioning_date",
        "on_hire",
        "off_hire",
        "description",
        "iup_code",
        "start_date",
        "end_date"
    ],
    aliases={
        "iup": "iup_code",
        "code_unit": "unit_code",
        "vemdor": "vendors",
    },
)