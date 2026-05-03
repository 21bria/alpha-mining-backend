from .base import make_header_config

ASSAY_ROA_HEADERS = make_header_config(
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
        "ni","fe","al2o3","co","mgo","sio2","cao","mno","cr2o3","fe2o3","mc"
        #  "ni","co","al2o3","cao","cr2o3","fe2o3","fe","k2o","mgo","mno","na2o","p2o5",
        # "p","sio2","tio2","s","cu","zn","ci","so3","loi","total","wt_wet","wt_dry","mc","p75um",
        # "_5mm","problem",
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
    },
)