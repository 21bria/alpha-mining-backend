from .base import make_header_config

SELLING_OFFICIAL_HEADERS = make_header_config(
    required=[
        "iup_code",
        "type_selling",
        "product_code",
        "name_surveyor",
    ],
    allowed=[
        "iup_code",
        "type_selling",
        "product_code",
        "factory_stock",
        "name_surveyor",
        "tonnage",
        "so_number",
        "barge_code",
        "ni",
        "co",
        "al2o3",
        "cao",
        "cr2o3",
        "fe",
        "mgo",
        "sio2",
        "mno",
        "mc",
        "start_date",
        "end_date",
        "description",
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
    },
)