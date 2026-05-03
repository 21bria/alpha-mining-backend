from .base import make_header_config

ASSAY_MRAL_HEADERS = make_header_config(
    required=[
        "iup_code",
        "release_date",
        "release_time",
        "sample_id",
    ],
    allowed=[
        "iup_code",
        "release_date",
        "release_time",
        "job_number",

        "sample_id",
        "ni","fe","co","mgo","sio2","fe2o3"
  
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
    },
)