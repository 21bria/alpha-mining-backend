from decimal import Decimal

from django.http import JsonResponse

from analytics.models_report_management import ReportManagement


def d(value):
    return Decimal(str(value or 0))


def get_manpower_management(request):
    """
    Mengambil Site POB dan manpower per contractor
    dari ReportManagementManpower.

    Query yang didukung:
    - iup_id
    - filter_type: weekly | monthly | yearly | range
    - year
    - month / monthly
    - week / weekly
    - period_start / date_start
    - period_end / date_end
    """

    iup_id = request.GET.get("iup_id")
    filter_type = (
        request.GET.get("filter_type")
        or request.GET.get("period_type")
        or "range"
    ).lower()

    year = (
        request.GET.get("year")
        or request.GET.get("yearly")
    )

    month = (
        request.GET.get("month")
        or request.GET.get("monthly")
    )

    week = (
        request.GET.get("week")
        or request.GET.get("weekly")
    )

    period_start = (
        request.GET.get("period_start")
        or request.GET.get("date_start")
    )

    period_end = (
        request.GET.get("period_end")
        or request.GET.get("date_end")
    )

    if not iup_id:
        return JsonResponse(
            {
                "success": False,
                "message": "iup_id is required.",
            },
            status=400,
        )

    queryset = (
        ReportManagement.objects
        .filter(
            iup_id=iup_id,
            is_deleted=False,
        )
        .prefetch_related("manpower_rows")
        .order_by("-period_end", "-created_at")
    )

    if filter_type == "weekly":
        if not year or not week:
            return JsonResponse(
                {
                    "success": False,
                    "message": "year and week are required.",
                },
                status=400,
            )

        queryset = queryset.filter(
            period_type="weekly",
            year=int(year),
            week=int(week),
        )

    elif filter_type == "monthly":
        if not year or not month:
            return JsonResponse(
                {
                    "success": False,
                    "message": "year and month are required.",
                },
                status=400,
            )

        queryset = queryset.filter(
            period_type="monthly",
            year=int(year),
            month=int(month),
        )

    elif filter_type == "yearly":
        if not year:
            return JsonResponse(
                {
                    "success": False,
                    "message": "year is required.",
                },
                status=400,
            )

        queryset = queryset.filter(
            period_type="yearly",
            year=int(year),
        )

    elif filter_type == "range":
        if not period_start or not period_end:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "period_start and period_end are required."
                    ),
                },
                status=400,
            )

        queryset = queryset.filter(
            period_start=period_start,
            period_end=period_end,
        )

    else:
        return JsonResponse(
            {
                "success": False,
                "message": f"Unsupported filter_type: {filter_type}.",
            },
            status=400,
        )

    report = queryset.first()

    if not report:
        return JsonResponse({
            "success": True,
            "filter_type": filter_type,
            "report_id": None,
            "summary": {
                "site_pob": 0,
                "contractor_count": 0,
            },
            "rows": [],
        })


    # ------------------------------------------------------------------
    # Previous Report
    # ------------------------------------------------------------------
    previous_queryset = (
        ReportManagement.objects
        .filter(
            iup_id=report.iup_id,
            period_type=report.period_type,
            is_deleted=False,
        )
    )

    if report.period_type == "weekly":
        previous_queryset = previous_queryset.filter(
            year=report.year,
            week__lt=report.week,
        )

    elif report.period_type == "monthly":
        previous_queryset = previous_queryset.filter(
            year=report.year,
            month__lt=report.month,
        )

    elif report.period_type == "yearly":
        previous_queryset = previous_queryset.filter(
            year__lt=report.year,
        )

    elif report.period_type == "range":
        previous_queryset = previous_queryset.filter(
            period_end__lt=report.period_start,
        )

    previous_report = (
        previous_queryset
        .prefetch_related("manpower_rows")
        .order_by("-period_end", "-created_at")
        .first()
    )

    previous_map = {}

    if previous_report:
        previous_map = {
            row.contractor: int(row.personnel or 0)
            for row in previous_report.manpower_rows.all()
        }


    # ------------------------------------------------------------------
    # Current Rows
    # ------------------------------------------------------------------
    manpower_queryset = (
        report.manpower_rows
        .all()
        .order_by("sort_order", "contractor")
    )

    rows = []

    for row in manpower_queryset:

        contractor = (row.contractor or "").strip()

        if contractor.lower() in {
            "man-hours",
            "man hours",
            "manhour",
            "manhours",
        }:
            continue

        current = int(row.personnel or 0)
        previous = previous_map.get(contractor, 0)

        change_value = current - previous

        if previous > 0:
            change_percent = round(
                (change_value / previous) * 100,
                2,
            )
        else:
            change_percent = 0

        if current > previous:
            status = "UP"
        elif current < previous:
            status = "DOWN"
        else:
            status = "STABLE"

        rows.append({
            "id": str(row.id),
            "contractor": contractor,
            "personnel": current,

            "previous_personnel": previous,
            "change_value": change_value,
            "change_percent": change_percent,

            "comparison_label": (
                f"vs {previous_report.report_code}"
                if previous_report
                else ""
            ),

            "status": status,

            "description": row.description or "",
            "source_module": row.source_module,
            "sort_order": row.sort_order,
        })


    site_pob = sum(
        row["personnel"]
        for row in rows
    )

    return JsonResponse({
        "success": True,
        "filter_type": filter_type,
        "report_id": str(report.id),
        "report_code": report.report_code,
        "period_type": report.period_type,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "summary": {
            "site_pob": site_pob,
            "contractor_count": len(rows),
        },
        "rows": rows,
    })