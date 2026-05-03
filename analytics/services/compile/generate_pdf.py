# reports/views.py
from io import BytesIO
from django.http import HttpResponse, HttpResponseBadRequest
from datetime import date,datetime
from django.utils import timezone
from django.utils.timezone import localtime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib.colors import HexColor
from reportlab.graphics.charts.legends import Legend
from decimal import Decimal

def safe_float(v):
    try:
        return float(Decimal(v))
    except:
        return 0.0
    
# === Data Range (untuk mode range) ===
from .data_range_quality import (
    fetch_production_quality,
    fetch_production_grade,
)
from .data_range_barging import (
    fetch_selling,
    fetch_barging,
)
from .data_range_mining import (
    fetch_production_mining,
)
from .data_range_inventory import (
    fetch_inventory_balance,
    fetch_inventory_dome,
)
from .data_range_fueling import (
    fetch_fueling_to_date,
)
from .data_range_summary import (
    fetch_summary_to_date,
)

# === Data Year (untuk mode year) ===
from .data_year_quality import (
    fetch_production_quality_year, 
    fetch_production_grade_year,
)
from .data_year_barging import (
    fetch_selling_year,
    fetch_barging_year,
)
from .data_year_mining import (
    fetch_production_mining_year,
)
from .data_year_inventory import (
    fetch_inventory_balance_year,
    fetch_inventory_dome_year,
)
from .data_year_fueling import (
    fetch_fueling_year
)
from .data_year_summary import (
    fetch_summary_to_year,
)

def parse_label(dt_val):
    if isinstance(dt_val, date):          # datetime.date / datetime
        return dt_val.day                 # kalau range (daily)
    if isinstance(dt_val, str) and len(dt_val) == 7:  # "YYYY-MM"
        return datetime.strptime(dt_val, "%Y-%m").month
    if isinstance(dt_val, str) and len(dt_val) == 10: # "YYYY-MM-DD"
        return datetime.strptime(dt_val, "%Y-%m-%d").day
    return dt_val


def pdf_unified_summary(request):
    mode       = request.GET.get("mode") or "range"
    iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
    date_start = request.GET.get("date_start") or str(date.today().replace(day=1))
    date_end   = request.GET.get("date_end")   or str(date.today())
    year       = request.GET.get("year")

    # === Ambil data (sama dengan Excel) ===
    if mode == "range":
        mining  = fetch_production_mining(date_start, date_end, iup_filter=iup_filter)
        prod    = fetch_production_quality(date_start, date_end, iup_filter=iup_filter)
        grade   = fetch_production_grade(date_start, date_end, iup_filter=iup_filter)
        sell    = fetch_selling(date_start, date_end, iup_filter=iup_filter)
        barging = fetch_barging(date_start, date_end, iup_filter=iup_filter)
        inv     = fetch_inventory_balance(date_start, date_end, iup_filter=iup_filter)
        fuel    = fetch_fueling_to_date(date_start, date_end, iup_filter=iup_filter)
        summary = fetch_summary_to_date(date_end, iup_filter=iup_filter)
    elif mode == "year" and year:
        year = int(year)
        mining  = fetch_production_mining_year(year, iup_filter=iup_filter)
        prod    = fetch_production_quality_year(year, iup_filter=iup_filter)
        grade   = fetch_production_grade_year(year, iup_filter=iup_filter)
        sell    = fetch_selling_year(year, iup_filter=iup_filter)
        barging = fetch_barging_year(year, iup_filter=iup_filter)
        inv     = fetch_inventory_balance_year(year, iup_filter=iup_filter)
        fuel    = fetch_fueling_year(year, iup_filter=iup_filter)
        summary = fetch_summary_to_year(year, iup_filter=iup_filter)
    else:
        return HttpResponseBadRequest("Invalid mode or missing parameters")

    def safe_float(val):
        try:
            return float(val or 0)
        except:
            return 0.0

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        topMargin=25,    # margin atas diperkecil
        bottomMargin=20  # margin bawah diperkecil
    )

    elements = []
    styles = getSampleStyleSheet()

  # Tambah style kanan kecil
    styles.add(ParagraphStyle(
        name="RightSmall",
        parent=styles["Normal"],
        fontSize=8,
        # alignment=TA_RIGHT
    ))

    # === Header PDF ===
    elements.append(Paragraph("KQMS Unified Report - Summary", styles['Title']))
    if mode == "range":
        header_info = Paragraph(
            f"Range: {date_start} → {date_end}<br/>"
            f"Generated: {localtime(timezone.now()).strftime('%Y-%m-%d, %H:%M:%S')}",
            styles['RightSmall']
        )
    else:
        header_info = Paragraph(
            f"Year: {year}<br/>"
            f"Generated: {localtime(timezone.now()).strftime('%Y-%m-%d, %H:%M:%S')}",
            styles['RightSmall']
        )

    elements.append(header_info)
    elements.append(Spacer(1, 4))

    # Fungsi bantu untuk auto scale axis
    def auto_scale_axis(series, n_ticks=6):
        from math import ceil
        max_val = max((max(s) for s in series if s), default=0)
        if max_val == 0:
            return (0, 100, 20)
        step = max(1, round(max_val / (n_ticks - 1), -2))
        vmax = ceil(max_val / step) * step
        return (0, vmax, step)

    def add_section_with_summary(title, metrics, rows, categories, series, line_series=None, breakdown=None, bar_color="#1f2937"):
        elements.append(Paragraph(title, styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Tabel ringkas
        table = Table(metrics, colWidths=[200, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            # Kolom Metric rata kiri
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            # Kolom Value rata kanan
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

        if rows:
            d = Drawing(700, 300)

            # auto-scale
            combined = list(series)
            if line_series:
                combined.append([safe_float(v) for v in line_series])
            vmin, vmax, vstep = auto_scale_axis(combined)

            # === Bar chart ===
            bc = VerticalBarChart()
            bc.x, bc.y = 50, 50
            bc.height, bc.width = 200, 550
            bc.data = series
            bc.categoryAxis.categoryNames = [str(c) for c in categories]
            bc.barWidth = 12
            
            # rapikan label tanggal biar tidak numpuk
            bc.categoryAxis.labels.angle = 45            # miring 45 derajat
            bc.categoryAxis.labels.boxAnchor = 'ne'      # anchor ke atas kanan
            bc.categoryAxis.labels.dy = -3              # geser ke atas sedikit
            bc.categoryAxis.labels.fontSize = 9          # perkecil font biar muat
            bc.categoryAxis.labels.fillColor = HexColor("#9ca3af")  # warna abu

        
            # Style axis
            bc.valueAxis.valueMin  = vmin
            bc.valueAxis.valueMax  = vmax
            bc.valueAxis.valueStep = vstep
            bc.valueAxis.strokeColor = HexColor("#9ca3af")
            bc.valueAxis.labels.fillColor = HexColor("#6b7280")
            bc.categoryAxis.strokeColor = HexColor("#fdfeff")
            bc.categoryAxis.labels.fillColor = HexColor("#676a6e")
            bc.categoryAxis.visibleTicks = 0

            # Bar color
            bc.bars[0].fillColor = HexColor(bar_color)
            for i in range(len(bc.bars)):
                bc.bars[i].strokeColor = None

            d.add(bc)

            # === Marker only (Plan) ===
             # === Line Chart (Plan) – tanpa scaling, pakai sumbu yang sama ===
            if line_series:
                lp = LinePlot()
                lp.x, lp.y = 50, 50
                lp.height, lp.width = 200, 550

                # data X numerik 0..N-1 agar sejajar bar
                lp.data = [list(enumerate([safe_float(v) for v in line_series]))]

                # definisikan axis numeric dan samakan rentang Y
                lp.xValueAxis.valueMin  = 0
                lp.xValueAxis.valueMax  = max(1, len(categories)-1)
                lp.xValueAxis.valueStep = max(1, len(categories)//10)

                # >>> matikan label & ticks di X axis (biar 0-28 hilang) <<<
                lp.xValueAxis.labels.fontSize = 0       # sembunyikan tulisan
                lp.xValueAxis.visibleTicks = 0          # sembunyikan garis tick
                # lp.xValueAxis.strokeColor = colors.white  # bikin invisible
                lp.xValueAxis.strokeColor = HexColor("#9ca3af")  # abu-abu halus

                # Y axis tetap jalan
                lp.yValueAxis.valueMin  = vmin
                lp.yValueAxis.valueMax  = vmax
                lp.yValueAxis.valueStep = vstep
                lp.yValueAxis.strokeColor = HexColor("#9ca3af")
                lp.yValueAxis.labels.fillColor = HexColor("#6b7280")

                lp.lines[0].strokeColor = HexColor("#ef4444")
                lp.lines[0].strokeWidth = 2
                lp.lines[0].symbol = makeMarker('Circle')

                d.add(lp)


            elements.append(d)

        # breakdown tambahan
        if breakdown:
            elements.append(Spacer(1, 12))
            btable = Table(breakdown, colWidths=[78] * len(breakdown[0]))
            btable.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('ALIGN', (0,1), (-1,-1), 'CENTER'),
            ]))
            elements.append(btable)

        elements.append(PageBreak())

    def add_ore_section(title, metrics, rows, categories, bar_series, line_series):
        elements.append(Paragraph(title, styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Metrics table
        table = Table(metrics, colWidths=[120, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            # Kolom Metric rata kiri
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            # Kolom Value rata kanan
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))

        if rows:
            # d = Drawing(700, 200)
            d = Drawing(400, 200)   # lebih kecil agar muat di samping
            # === Bar Chart (Production In & Selling Out) ===
            bc = VerticalBarChart()
            bc.x, bc.y = 30, 30
            bc.height, bc.width = 170, 550
            bc.data = bar_series
            bc.categoryAxis.categoryNames = [str(c) for c in categories]
            bc.barWidth = 8

            # auto scale bar axis
            vmin, vmax, vstep = auto_scale_axis(bar_series)
            bc.valueAxis.valueMin = vmin
            bc.valueAxis.valueMax = vmax
            bc.valueAxis.valueStep = vstep

            bc.bars[0].fillColor = HexColor("#eab672")  # orange
            bc.bars[1].fillColor = HexColor("#a0c481")  # green


            bc.valueAxis.strokeColor = HexColor("#9ca3af")
            bc.valueAxis.labels.fillColor = HexColor("#6b7280")
            bc.categoryAxis.strokeColor = HexColor("#9ca3af")
            bc.categoryAxis.labels.fillColor = HexColor("#676a6e")


            # hilangkan outline (stroke) cukup di level series
            bc.bars[0].strokeColor = None
            bc.bars[0].strokeWidth = 0
            bc.bars[1].strokeColor = None
            bc.bars[1].strokeWidth = 0


            d.add(bc)

            # === Line Chart (Running Balance, pakai axis kanan) ===
            if line_series:
                lp = LinePlot()
                lp.x, lp.y = 50, 50
                lp.height, lp.width = 200, 550
                lp.data = [list(enumerate([safe_float(v) for v in line_series]))]

                lp.lines[0].strokeColor = HexColor("#ef4444")
                lp.lines[0].strokeWidth = 2
                lp.lines[0].symbol = makeMarker('Circle')
                d.add(lp)

                # --- Axis kanan manual ---
                max_line = max(line_series) if line_series else 0
                if max_line > 0:
                    step_line = max(1, round(max_line / 5, -3))  # step ribuan

                    # garis axis kanan
                    d.add(Line(bc.x + bc.width, bc.y, bc.x + bc.width, bc.y + bc.height))

                    # label axis kanan
                    for i in range(0, int(max_line) + 1, int(step_line)):
                        y = bc.y + (i / max_line) * bc.height
                        d.add(String(bc.x + bc.width + 10, y, f"{i:,}", fontSize=7, fillColor=HexColor("#ef4444")))

            # --- Legend di atas chart ---
            legend = Legend()
            legend.x = bc.x + bc.width/2 - 150   # posisikan agak tengah
            legend.y = bc.y + bc.height + 40     # taruh di atas grafik
            legend.dx = 12                       # ukuran kotak warna
            legend.dy = 12
            legend.fontName = 'Helvetica'
            legend.fontSize = 9
            legend.boxAnchor = 'n'
            legend.columnMaximum = 3             # biar semua item 1 baris
            legend.deltax = 100                  # jarak antar item
            legend.deltay = 0                    # jangan bertingkat

            legend.colorNamePairs = [
                (HexColor("#eab672"), "Limonite"),
                (HexColor("#a0c481"), "Saprolite"),
            ]

            d.add(legend)
            elements.append(d)

        elements.append(PageBreak()) 

    def add_inventory_section(title, metrics, rows, categories, bar_series, line_series):
        elements.append(Paragraph(title, styles['Heading2']))
        elements.append(Spacer(1, 6))

        # Metrics table
        table = Table(metrics, colWidths=[120, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            # Kolom Metric rata kiri
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            # Kolom Value rata kanan
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))

        if rows:
            # d = Drawing(700, 200)
            d = Drawing(400, 200)   # lebih kecil agar muat di samping
            # === Bar Chart (Production In & Selling Out) ===
            bc = VerticalBarChart()
            bc.x, bc.y = 30, 30
            bc.height, bc.width = 170, 550
            bc.data = bar_series
            bc.categoryAxis.categoryNames = [str(c) for c in categories]
            bc.barWidth = 8

            # auto scale bar axis
            vmin, vmax, vstep = auto_scale_axis(bar_series)
            bc.valueAxis.valueMin = vmin
            bc.valueAxis.valueMax = vmax
            bc.valueAxis.valueStep = vstep

            bc.bars[0].fillColor = HexColor("#add2bb")  # green
            bc.bars[1].fillColor = HexColor("#eab672")  # orange


            bc.valueAxis.strokeColor = HexColor("#9ca3af")
            bc.valueAxis.labels.fillColor = HexColor("#6b7280")
            bc.categoryAxis.strokeColor = HexColor("#9ca3af")
            bc.categoryAxis.labels.fillColor = HexColor("#676a6e")


            # hilangkan outline (stroke) cukup di level series
            bc.bars[0].strokeColor = None
            bc.bars[0].strokeWidth = 0
            bc.bars[1].strokeColor = None
            bc.bars[1].strokeWidth = 0


            d.add(bc)

            # === Line Chart (Running Balance, pakai axis kanan) ===
            if line_series:
                lp = LinePlot()
                lp.x, lp.y = 50, 50
                lp.height, lp.width = 200, 550
                lp.data = [list(enumerate([safe_float(v) for v in line_series]))]

                lp.lines[0].strokeColor = HexColor("#ef4444")
                lp.lines[0].strokeWidth = 2
                lp.lines[0].symbol = makeMarker('Circle')
                d.add(lp)

                # --- Axis kanan manual ---
                max_line = max(line_series) if line_series else 0
                if max_line > 0:
                    step_line = max(1, round(max_line / 5, -3))  # step ribuan

                    # garis axis kanan
                    d.add(Line(bc.x + bc.width, bc.y, bc.x + bc.width, bc.y + bc.height))

                    # label axis kanan
                    for i in range(0, int(max_line) + 1, int(step_line)):
                        y = bc.y + (i / max_line) * bc.height
                        d.add(String(bc.x + bc.width + 10, y, f"{i:,}", fontSize=7, fillColor=HexColor("#ef4444")))

            # --- Legend di atas chart ---
            legend = Legend()
            legend.x = bc.x + bc.width/2 - 150   # posisikan agak tengah
            legend.y = bc.y + bc.height + 40     # taruh di atas grafik
            legend.dx = 12                       # ukuran kotak warna
            legend.dy = 12
            legend.fontName = 'Helvetica'
            legend.fontSize = 9
            legend.boxAnchor = 'n'
            legend.columnMaximum = 3             # biar semua item 1 baris
            legend.deltax = 100                  # jarak antar item
            legend.deltay = 0                    # jangan bertingkat

            legend.colorNamePairs = [
                (HexColor("#add2bb"), "Production In"),
                (HexColor("#eab672"), "Selling Out"),
            ]

            d.add(legend)
            elements.append(d)

        elements.append(PageBreak()) 

    def add_fuel_section( title,metrics,rows, categories, series, breakdown,line_series=None, bar_color="#1f2937"):
        elements.append(Paragraph(title, styles['Heading2']))
        elements.append(Spacer(1, 6))

        # === Summary Table ===
        table = Table(metrics, colWidths=[200, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('ALIGN', (0,0), (0,-1), 'LEFT'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))

        # === Chart (PAKAI LOGIKA YANG SAMA) ===
        if rows:
            d = Drawing(700, 300)

            combined = list(series)
            vmin, vmax, vstep = auto_scale_axis(combined)

            bc = VerticalBarChart()
            bc.x, bc.y = 50, 50
            bc.height, bc.width = 200, 550
            bc.data = series
            bc.categoryAxis.categoryNames = categories
            bc.barWidth = 12

            bc.categoryAxis.labels.angle = 45
            bc.categoryAxis.labels.fontSize = 9
            bc.categoryAxis.labels.fillColor = HexColor("#6b7280")

            bc.valueAxis.valueMin = vmin
            bc.valueAxis.valueMax = vmax
            bc.valueAxis.valueStep = vstep

            bc.bars[0].fillColor = HexColor(bar_color)
            
            bc.valueAxis.strokeColor = HexColor("#9ca3af")
            bc.valueAxis.labels.fillColor = HexColor("#6b7280")
            bc.categoryAxis.strokeColor = HexColor("#9ca3af")
            bc.categoryAxis.labels.fillColor = HexColor("#676a6e")


            # hilangkan outline (stroke) cukup di level series
            bc.bars[0].strokeColor = None
            bc.bars[0].strokeWidth = 0
            bc.bars[1].strokeColor = None
            bc.bars[1].strokeWidth = 0
            d.add(bc)

            elements.append(d)

        # === Breakdown Fuel (KHUSUS) ===
        if breakdown and breakdown[0]:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(
                "Fuel Consumption by Category",
                styles['Heading5']
            ))
            elements.append(Spacer(1, 4))

            col_count = len(breakdown[0])

            col_width = min(70, 680 / col_count)

            btable = Table(
                breakdown,
                colWidths=[col_width] * col_count
            )

            btable.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.4, colors.black),
                ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))

            elements.append(btable)


   # === Summary Section ===
    summary_title = Paragraph("Project Summary To-Date", styles['Heading4'])
    elements.append(summary_title)
    elements.append(Spacer(1, 6))

    # --- Mining ---
    mining_table = Table([
        ["Metric", "Value"],
        ["Total Actual", f"{summary['mining'].get('actual_total', 0):,.0f}"],
        ["Ore (Lim + Sap)", f"{summary['mining'].get('ore', 0):,.0f}"],
        ["Non Ore", f"{summary['mining'].get('non_ore', 0):,.0f}"],
    ], colWidths=[120, 100])

    mining_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
         # Kolom Metric rata kiri
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        # Kolom Value rata kanan
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    # --- Quality ---
    quality_table = Table([
        ["Metric", "Value"],
        ["Total Tonnage", f"{summary['quality'].get('total', 0):,.0f}"],
        ["LIM (total)",   f"{summary['quality'].get('lim', 0):,.0f}"],
        # ["LIM (%)",       f"{(summary['quality'].get('lim', 0)/(summary['quality'].get('total',1))*100):.2f}%"],
        ["SAP (total)",   f"{summary['quality'].get('sap', 0):,.0f}"],
        # ["SAP (%)",       f"{(summary['quality'].get('sap', 0)/(summary['quality'].get('total',1))*100):.2f}%"],
    ], colWidths=[120, 100])

    quality_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
         # Kolom Metric rata kiri
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        # Kolom Value rata kanan
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    # --- Selling ---
    actual = summary['selling'].get('actual', 0) or 0
    plan   = summary['selling'].get('plan', 0) or 0
    lim_actual = summary['selling'].get('lim_actual', 0) or 0
    sap_actual = summary['selling'].get('sap_actual', 0) or 0

    # achievement = f"{(actual / plan * 100):.0f}%" if plan > 0 else "0%"

    selling_table = Table([
        ["Metric", "Value"],
        ["Total Actual", f"{actual:,.0f}"],
        # ["Total Plan",   f"{plan:,.0f}"],
        # ["Achievement",  achievement],
        ["LIM Actual",   f"{lim_actual:,.0f}"],
        ["SAP Actual",   f"{sap_actual:,.0f}"],
    ], colWidths=[120, 100])


    selling_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        # Kolom Metric rata kiri
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        # Kolom Value rata kanan
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    # --- Inventory ---
    inv_table = Table([
        ["Metric", "Value"],
        ["Production In", f"{summary['inventory'].get('in', 0):,.0f}"],
        ["Selling Out",   f"{summary['inventory'].get('out', 0):,.0f}"],
        ["Current Stock", f"{summary['inventory'].get('current_stock', 0):,.0f}"],
    ], colWidths=[120, 100])

    inv_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        # Kolom Metric rata kiri
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        # Kolom Value rata kanan
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    # === Gabung jadi 2 kolom ===
    left_col = [Paragraph("Mining", styles['Heading5']), mining_table,
                Spacer(1,4),
                Paragraph("Material Type", styles['Heading5']), quality_table]

    right_col = [Paragraph("Selling", styles['Heading5']), selling_table,
                Spacer(1,4),
                Paragraph("Inventory", styles['Heading5']), inv_table]

    two_col = Table([
        [left_col, right_col]
    ], colWidths=[250, 250])

    elements.append(two_col)
    elements.append(Spacer(1, 10))

    # --- Breakdown Mining ---
    breakdown_table = Table([
        ["Total LIM", "Total SAP", "Total Waste", "Total Quarry",
        "Total Topsoil", "Total OB", "Total Ballast", "Total Biomass"],
        [
            f"{summary['mining'].get('lim_total', 0):,.0f}",
            f"{summary['mining'].get('sap_total', 0):,.0f}",
            f"{summary['mining'].get('waste_total', 0):,.0f}",
            f"{summary['mining'].get('quarry_total', 0):,.0f}",
            f"{summary['mining'].get('topsoil_total', 0):,.0f}",
            f"{summary['mining'].get('ob_total', 0):,.0f}",
            f"{summary['mining'].get('ballast_total', 0):,.0f}",
            f"{summary['mining'].get('biomass_total', 0):,.0f}",
        ]
    ], colWidths=[65,65,65,70,70,70,70,70])

    breakdown_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),     # kecilkan font
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),  # rapatkan tabel
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))

    elements.append(Paragraph("Productions Mining by Materials", styles['Heading5']))
    elements.append(Spacer(1, 6))
    elements.append(breakdown_table)
    elements.append(PageBreak())

    # === Mining Section ===
    total_actual = sum(safe_float(r.get("actual_total")) for r in mining["rows"])
    total_plan   = sum(safe_float(r.get("plan_total")) for r in mining["rows"])

    # hitung AVG & Achievement
    avg_actual   = total_actual / len(mining["rows"]) if mining["rows"] else 0
    achievement  = (total_actual / total_plan * 100) if total_plan > 0 else 0

    mining_metrics = [
        ["Metric", "Value"],
        ["Total Actual", f"{total_actual:,.0f}"],
        ["Ore (Lim + Sap)",f"{total_plan:,.0f}"],
        ["Non Ore",f"{avg_actual:,.0f}"],
    ]


    # === Hitung Breakdown Mining ===
    lim_total     = sum(safe_float(r.get("lim")) for r in mining["rows"])
    sap_total     = sum(safe_float(r.get("sap")) for r in mining["rows"])
    waste_total   = sum(safe_float(r.get("waste")) for r in mining["rows"])
    quarry_total  = sum(safe_float(r.get("quarry")) for r in mining["rows"])
    topsoil_total = sum(safe_float(r.get("topsoil")) for r in mining["rows"])
    ob_total      = sum(safe_float(r.get("ob")) for r in mining["rows"])
    ballast_total = sum(safe_float(r.get("ballast")) for r in mining["rows"])
    biomass_total = sum(safe_float(r.get("biomass")) for r in mining["rows"])


    # --- Buat judul dinamis ---
    if mode == "range":
        mining_title    = f"Mining by Period (Range: {date_start} → {date_end})"
        quality_title   = f"Material Type by Period (Range: {date_start} → {date_end})"
        grade_title     = f"Daily Ore by Period (Range: {date_start} → {date_end})"
        selling_title   = f"Selling by Period (Range: {date_start} → {date_end})"
        barging_title   = f"Barging by Period (Range: {date_start} → {date_end})"
        inventory_title = f"Inventory by Period (Range: {date_start} → {date_end})"
        fuel_title      = f"Fuel Consumption by Period (Range: {date_start} → {date_end})"
    elif mode == "year":
        mining_title    = f"Mining by Period (Year: {year})"
        quality_title   = f"Material Type by Period (Year: {year})"
        grade_title     = f"Daily Ore by Period  (Year: {year})"
        selling_title   = f"Selling by Period (Year: {year})"
        barging_title   = f"Barging by Period (Year: {year})"
        inventory_title = f"Inventory by Period (Year: {year})"
        fuel_title      = f"Fuel Consumption by Period (Year: {year})"
    else:
        mining_title    = "Mining by Period"
        quality_title   = "Material Type by Period"
        grade_title     = "Daily Ore by Period "
        selling_title   = "Selling by Period"
        barging_title   = "Barging by Period"
        inventory_title = "Inventory by Period"
        fuel_title      = "Fuel Consumption by Period"


    # Mining pakai summary + breakdown
    add_section_with_summary(
        mining_title,
        mining_metrics,
        mining["rows"],
        # [str(r['dt'].day).zfill(2) for r in mining["rows"]],
        [str(parse_label(r['dt'])).zfill(2) for r in mining["rows"]],
        [[safe_float(r.get("actual_total")) for r in mining["rows"]]],
        line_series=[safe_float(r.get("plan_total")) for r in mining["rows"]],
        bar_color="#335871",

        # --- Breakdown Mining ---
        breakdown = [
            ["Total LIM", "Total SAP", "Total Waste", "Total Quarry",
            "Total Topsoil", "Total OB", "Total Ballast", "Total Biomass"],
            [
                f"{lim_total:,.0f}",
                f"{sap_total:,.0f}",
                f"{waste_total:,.0f}",
                f"{quarry_total:,.0f}",
                f"{topsoil_total:,.0f}",
                f"{ob_total:,.0f}",
                f"{ballast_total:,.0f}",
                f"{biomass_total:,.0f}",
            ]
        ]
        
    )

    # === Quality Section ===
    prod_total = sum(safe_float(r.get("prod_total")) for r in prod["rows"])
    prod_lim   = sum(safe_float(r.get("prod_lim")) for r in prod["rows"])
    prod_sap   = sum(safe_float(r.get("prod_sap")) for r in prod["rows"])

    quality_metrics = [
        ["Metric", "Value"],
        ["Total Tonnage", f"{prod_total:,.0f}"],
        ["LIM",    f"{prod_lim:,.0f}"],
        ["SAP",    f"{prod_sap:,.0f}"],

    ]

    quality_series = [
                    [safe_float(r.get("prod_lim")) for r in prod["rows"]],
                    [safe_float(r.get("prod_sap")) for r in prod["rows"]],
                      ]
    add_ore_section(
        quality_title, 
        quality_metrics, prod["rows"],
        # [str(r['dt'].day).zfill(2) for r in prod["rows"]],
        [str(parse_label(r['dt'])).zfill(2) for r in prod["rows"]],
        quality_series,
        line_series=None,
        # bar_color=["#fac849","#9ec57c"]
        )

    # === Daily Grade Detail (auto page break if long) ===
    # grade = fetch_production_grade(date_start, date_end)
    grade_rows = grade["rows"]

    if grade_rows:
        elements.append(Paragraph(grade_title, styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        
        data = [["Date","Material","Tonnage", "Ni", "Co", "Fe", "MgO", "SiO2", "SM"]]
        for r in grade_rows:
            data.append([
                r["dt"],
                r["nama_material"],    
                f"{safe_float(r['total_ore']):,.0f}",
                f"{safe_float(r['ni']):.2f}",
                f"{safe_float(r['co']):.2f}",
                f"{safe_float(r['fe']):.2f}",
                f"{safe_float(r['mgo']):.2f}",
                f"{safe_float(r['sio2']):.2f}",
                f"{safe_float(r['sm']):.2f}",
            ])

        tbl2 = Table(
            data, 
            repeatRows=1, 
            colWidths=[80,100,80,60,60,60,60,60,60]
        )
        tbl2.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#e5e7eb")),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('GRID',(0,0),(-1,-1),0.3,colors.black),

            # Default semua kanan
            ('ALIGN',(0,1),(-1,-1),'RIGHT'),

            # Override Date kiri
            ('ALIGN',(0,1),(0,-1),'LEFT'),

            # Override Material kiri
            ('ALIGN',(1,1),(1,-1),'LEFT'),
        ]))
        elements.append(tbl2)
        elements.append(Spacer(1, 10))

    # === Page break BEFORE selling ===
    elements.append(PageBreak())


    # === Selling Section ===
    rows    = sell["rows"]
    summary = sell["summary"]

    actual_total = summary.get("actual_total", 0)
    lim_actual   = summary.get("lim_actual", 0)
    sap_actual   = summary.get("sap_actual", 0)

    selling_metrics = [
        ["Metric", "Value"],
        ["Total Actual", f"{actual_total:,.0f}"],
        ["LIM Actual",   f"{lim_actual:,.0f}"],
        ["SAP Actual",   f"{sap_actual:,.0f}"],
    ]

    selling_series = [
        [safe_float(r.get("actual_lim")) for r in sell["rows"]],
        [safe_float(r.get("actual_sap")) for r in sell["rows"]]
        ]
    add_ore_section(
        selling_title, 
        selling_metrics, 
        sell["rows"],
        # [str(r['dt'].day).zfill(2) for r in sell["rows"]],
        [str(parse_label(r['dt'])).zfill(2) for r in sell["rows"]],
        selling_series,
        line_series=None,
        )
    
    # === Barging Section ===
    rows    = barging["rows"]
    summary = barging["summary"]

    actual_total = summary.get("actual_total", 0)
    lim_actual   = summary.get("lim_actual", 0)
    sap_actual   = summary.get("sap_actual", 0)

    barging_metrics = [
        ["Metric", "Value"],
        ["Total Actual", f"{actual_total:,.0f}"],
        ["LIM Actual",   f"{lim_actual:,.0f}"],
        ["SAP Actual",   f"{sap_actual:,.0f}"],
    ]

    # 2 BAR SERIES
    barging_series = [
        [safe_float(r.get("actual_lim")) for r in barging["rows"]],
        [safe_float(r.get("actual_sap")) for r in barging["rows"]],
    ]

    add_ore_section(
        barging_title,
        barging_metrics,
        inv["rows"],
        # [str(r['dt'].day).zfill(2) for r in inv["rows"]],
        [str(parse_label(r['dt'])).zfill(2) for r in inv["rows"]],
        barging_series,
        line_series=None, 
    )

    # === Inventory Section ===
    inv_sum = inv["summary"]
    inv_metrics = [
        ["Metric", "Value"],
        ["Opening Stock", f"{safe_float(inv_sum.get('opening_balance')):,.2f}"],
        ["Production In", f"{safe_float(inv_sum.get('total_in')):,.2f}"],
        ["Selling Out", f"{safe_float(inv_sum.get('total_out')):,.2f}"],
        ["Closing Stock", f"{safe_float(inv_sum.get('closing_balance')):,.2f}"],
    ]

    # 2 bar series
    inv_series = [
        [safe_float(r.get("total_in")) for r in inv["rows"]],
        [safe_float(r.get("total_out")) for r in inv["rows"]],
    ]

    add_inventory_section(
        inventory_title,
        inv_metrics,
        inv["rows"],
        # [str(r['dt'].day).zfill(2) for r in inv["rows"]],
        [str(parse_label(r['dt'])).zfill(2) for r in inv["rows"]],
        bar_series=inv_series,
        line_series=None  # ⬅ Hilangkan line
    )

    # === Fuel Consumption Section === 
    fuel_metrics = [
        ["Metric", "Value"],
        ["Total Fuel", f"{safe_float(fuel['daily']['total']):,.2f}"],
    ]

    # Chart data
    x_labels = [
        r["date"].strftime("%d") if hasattr(r["date"], "strftime")
        else str(r["date"])[-2:]
        for r in fuel["daily"]["series"]
    ]

    bar_series = [
        [safe_float(r["volume"]) for r in fuel["daily"]["series"]]
    ]

    # Breakdown Fuel (DATA ONLY — ikut mining)
    category_series = fuel["category"]["series"]

    add_fuel_section(
        fuel_title,
        fuel_metrics,
        fuel["daily"]["series"],
        x_labels,
        bar_series,
        breakdown=[
            [f"{r['category']}" for r in category_series],
            [f"{safe_float(r['volume']):,.0f}" for r in category_series],
        ],
        bar_color="#7c91a2",
        line_series=None, 
    )

    # === Build PDF ===
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="KQMS-summary.pdf"'  # selalu preview
    response.write(pdf)
    return response
