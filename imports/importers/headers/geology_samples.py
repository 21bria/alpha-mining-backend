from .base import make_header_config

SAMPLES_GEOLOGY_HEADERS = make_header_config(
    required=[
        "iup_code",
        "date_sample",
        "shift",
        "sample_type",
        "sampling_method",
        "material",
        "sampling_area",
        "sampling_point",
        "sample_id"
    ],
    allowed=[
        "iup_code",
        "date_sample",
        "shift",
        "sample_type",
        "sampling_method",
        "material",
        "sampling_area",
        "sampling_point",
        "from","to",
        "batch",
        "increments",
        "fraction",
        "size",
        "sample_weight",
        "sample_id",
        "remark",
        "primer_raw",
        "duplicat_raw",
        "sampling_desc"
    ],
    aliases={
        "iup": "iup_code",
        "iup_code": "iup_code",
        "date": "date_sample",
        "sample_number": "sample_id",
    },
)