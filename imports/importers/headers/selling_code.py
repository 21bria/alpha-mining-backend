from .base import make_header_config

SELLING_CODE_HEADERS = make_header_config(
    required=[
        "iup_code",
        "code",
        "type",
    ],
    allowed=[
        "iup_code",
        "code",
        "type",
        "description",
        "active",
        "truck_factors",
        "sublot_close",
        "group_close",
        "ritase_max",
        "tonnage",
        "ni",
        "fe",
        "mgo",
        "sio2",
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
    },
)