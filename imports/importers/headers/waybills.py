from .base import make_header_config

WAYBILLS_HEADERS = make_header_config(
    required=[
        "iup_code",
        "tgl_deliver",
        "delivery_time",
        "waybill_number",
        "sample_id",
        "qty",
        "mral_order",
        "roa_order",
    ],
    allowed=[
        "iup_code",
        "tgl_deliver",
        "delivery_time",
        "waybill_number",
        "sample_id",
        "qty",
        "mral_order",
        "roa_order",
        "remarks"
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
    },
)