# services/bot/production_service.py

from analytics.views.mining.all_summary import (
    build_filter_clause,
    get_summary_dataframe,
    generate_summary
)


def get_summary_service(
    filter_type="monthly",
    year=None,
    month=None,
    week=None,
    filter_date=None,
    date_start=None,
    date_end=None,
    iup_id=None
):
    result = {}

    if filter_type == "monthly":
        wa, wp, ga, gp, params = build_filter_clause(
            "monthly", year, month, None, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["monthly"] = generate_summary(df, "MONTHLY")

        wa, wp, ga, gp, params = build_filter_clause(
            "mtd", year, month, None, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["mtd"] = generate_summary(df, "MTD")

    elif filter_type == "weekly":
        wa, wp, ga, gp, params = build_filter_clause(
            "weekly", year, month, week, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["weekly"] = generate_summary(df, "WEEKLY")

        wa, wp, ga, gp, params = build_filter_clause(
            "wtd", year, month, week, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["wtd"] = generate_summary(df, "WTD")

    elif filter_type == "yearly":
        wa, wp, ga, gp, params = build_filter_clause(
            "yearly", year, None, None, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["yearly"] = generate_summary(df, "YEARLY")

        wa, wp, ga, gp, params = build_filter_clause(
            "ytd", year, None, None, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["ytd"] = generate_summary(df, "YTD")

    elif filter_type == "daily":
        wa, wp, ga, gp, params = build_filter_clause(
            "daily", None, None, None, filter_date, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["daily"] = generate_summary(df, "DAILY")

    elif filter_type == "range":
        wa, wp, ga, gp, params = build_filter_clause(
            "range", None, None, None, None, date_start, date_end, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["range"] = generate_summary(df, "RANGE")

    elif filter_type == "all":
        wa, wp, ga, gp, params = build_filter_clause(
            "all", None, None, None, None, None, None, iup_id
        )
        df = get_summary_dataframe(wa, wp, ga, gp, params)
        result["all"] = generate_summary(df, "ALL")

    return result