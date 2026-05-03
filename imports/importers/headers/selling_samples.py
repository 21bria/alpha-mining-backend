from .base import make_header_config

SAMPLES_SELLING_HEADERS = make_header_config(
    required=[
        "iup_code",
        "date_sample",
        "shift",
        "sample_type",
        "sampling_method",
        "material",
        "code_lot",
        "sub_lot",
        "group",
        "sample_id"
    ],
    allowed=[
        "iup_code",
        "date_sample",
        "shift",
        "sample_type",
        "sampling_method",
        "material",
        "buyer",
        "code_lot",
        "sub_lot",
        "group",
        "sample_id",
        "sample_weight",
        "primer_raw",
        "duplicat_raw",
        "remark"
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
        "date": "date_sample",
        "sample_number": "sample_id",
    },
)