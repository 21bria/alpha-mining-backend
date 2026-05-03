from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connection
import pandas as pd


# @login_required
def get_data_crm_roa_plot_json(request):
    iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    type_crm = request.GET.get("filterTypeCrm")

    query = """
        SELECT
            oreas_name,
            ni, fe, mgo, sio2,
            sample_number,
            sampling_deskripsi,
            sample_id,
            release_date,
            roa_ni, roa_fe, roa_mgo, roa_sio2
        FROM view_sample_crm_diff_roa
        WHERE release_date >= %s
          AND release_date <= %s
          AND oreas_name = %s
    """
    params = [start_date, end_date, type_crm]

    if iup_filter not in (None, "", "null", "undefined"):
        query += " AND iup_id = %s"
        params.append(iup_filter)

    query += " ORDER BY release_date, sample_number"

    df = pd.read_sql_query(query, connection, params=params)

    if df.empty:
        return JsonResponse({
            "summary": {
                "jml_row": 0,
                "acceptedNi": 0,
                "errorNi": 0,
                "acceptedFe": 0,
                "errorFe": 0,
                "acceptedMgo": 0,
                "errorMgo": 0,
                "acceptedSio2": 0,
                "errorSio2": 0,
            },
            "ni": {"x": [], "crm": [], "roa": [], "plus_10": [], "plus_5": [], "min_5": [], "min_10": []},
            "fe": {"x": [], "crm": [], "roa": [], "plus_10": [], "plus_5": [], "min_5": [], "min_10": []},
            "mgo": {"x": [], "crm": [], "roa": [], "plus_10": [], "plus_5": [], "min_5": [], "min_10": []},
            "sio2": {"x": [], "crm": [], "roa": [], "plus_10": [], "plus_5": [], "min_5": [], "min_10": []},
        })

    for key in ["ni", "fe", "mgo", "sio2"]:
        df[f"cek_{key}"] = (
            (df[f"roa_{key}"] < df[key] + (df[key] * -0.1)) |
            (df[f"roa_{key}"] > df[key] + (df[key] *  0.1))
        ).astype(int)

        df[f"plus_{key}_10"] = (df[key] + (df[key] * 0.10)).round(3)
        df[f"plus_{key}_5"] = (df[key] + (df[key] * 0.05)).round(3)
        df[f"min_{key}_5"] = (df[key] + (df[key] * -0.05)).round(3)
        df[f"min_{key}_10"] = (df[key] + (df[key] * -0.10)).round(3)

    response = {
        "summary": {
            "jml_row": len(df),
            "acceptedNi": int((df["cek_ni"] == 0).sum()),
            "errorNi": int((df["cek_ni"] == 1).sum()),
            "acceptedFe": int((df["cek_fe"] == 0).sum()),
            "errorFe": int((df["cek_fe"] == 1).sum()),
            "acceptedMgo": int((df["cek_mgo"] == 0).sum()),
            "errorMgo": int((df["cek_mgo"] == 1).sum()),
            "acceptedSio2": int((df["cek_sio2"] == 0).sum()),
            "errorSio2": int((df["cek_sio2"] == 1).sum()),
        },
        "ni": {
            "x": df["sample_number"].fillna("-").tolist(),
            "crm": df["ni"].tolist(),
            "roa": df["roa_ni"].tolist(),
            "plus_10": df["plus_ni_10"].tolist(),
            "plus_5": df["plus_ni_5"].tolist(),
            "min_5": df["min_ni_5"].tolist(),
            "min_10": df["min_ni_10"].tolist(),
        },
        "fe": {
            "x": df["sample_number"].fillna("-").tolist(),
            "crm": df["fe"].tolist(),
            "roa": df["roa_fe"].tolist(),
            "plus_10": df["plus_fe_10"].tolist(),
            "plus_5": df["plus_fe_5"].tolist(),
            "min_5": df["min_fe_5"].tolist(),
            "min_10": df["min_fe_10"].tolist(),
        },
        "mgo": {
            "x": df["sample_number"].fillna("-").tolist(),
            "crm": df["mgo"].tolist(),
            "roa": df["roa_mgo"].tolist(),
            "plus_10": df["plus_mgo_10"].tolist(),
            "plus_5": df["plus_mgo_5"].tolist(),
            "min_5": df["min_mgo_5"].tolist(),
            "min_10": df["min_mgo_10"].tolist(),
        },
        "sio2": {
            "x": df["sample_number"].fillna("-").tolist(),
            "crm": df["sio2"].tolist(),
            "roa": df["roa_sio2"].tolist(),
            "plus_10": df["plus_sio2_10"].tolist(),
            "plus_5": df["plus_sio2_5"].tolist(),
            "min_5": df["min_sio2_5"].tolist(),
            "min_10": df["min_sio2_10"].tolist(),
        },
        "rows": df.to_dict(orient="records"),
    }

    return JsonResponse(response)