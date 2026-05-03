# reports/views.py
from io import BytesIO
from django.http import HttpResponse, HttpResponseBadRequest
from datetime import date,datetime
from django.utils import timezone
from django.utils.timezone import localtime
import xlsxwriter
from ..safe_chart import safe_chart_multi
from decimal import Decimal

def to_decimal(v):
    return Decimal(str(v or 0))

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

def excel_unified_summary(request):
    mode       = request.GET.get("mode") or "range"
    iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
    date_start = request.GET.get("date_start") or str(date.today().replace(day=1))
    date_end   = request.GET.get("date_end") or str(date.today())
    year       = request.GET.get("year")

    if mode == "range":
        mining  = fetch_production_mining(date_start, date_end, iup_filter=iup_filter)
        prod    = fetch_production_quality(date_start, date_end, iup_filter=iup_filter)
        grade   = fetch_production_grade(date_start, date_end, iup_filter=iup_filter)
        sell    = fetch_selling(date_start, date_end, iup_filter=iup_filter)
        barging = fetch_barging(date_start, date_end, iup_filter=iup_filter)
        inv     = fetch_inventory_balance(date_start, date_end, iup_filter=iup_filter)
        invlist = fetch_inventory_dome(date_end, iup_filter=iup_filter)
        fuel    = fetch_fueling_to_date(date_start, date_end, iup_filter=iup_filter)
        summary = fetch_summary_to_date(date_end, iup_filter=iup_filter)

    elif mode == "year" and year:
        try:
            year = int(year)
        except ValueError:
            return HttpResponseBadRequest("Invalid year parameter")

        mining  = fetch_production_mining_year(year, iup_filter=iup_filter)
        prod    = fetch_production_quality_year(year, iup_filter=iup_filter)
        grade   = fetch_production_grade_year(year, iup_filter=iup_filter)
        sell    = fetch_selling_year(year, iup_filter=iup_filter)
        barging = fetch_barging_year(year, iup_filter=iup_filter)
        inv     = fetch_inventory_balance_year(year, iup_filter=iup_filter)
        invlist = fetch_inventory_dome_year(year, iup_filter=iup_filter)
        fuel    = fetch_fueling_year(year, iup_filter=iup_filter)
        summary = fetch_summary_to_year(year, iup_filter=iup_filter)
    else:
        return HttpResponseBadRequest("Invalid mode or missing parameters")
    
    output   = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Styles
    fmt_title = workbook.add_format({'bold': True, 'font_size': 14})
    fmt_th    = workbook.add_format({'bold': True, 'bg_color': '#F3F4F6', 'border': 1})
    fmt_td    = workbook.add_format({'border': 1})
    fmt_num   = workbook.add_format({'border': 1, 'num_format': '#,##0'})
    fmt_num2 = workbook.add_format({'border': 1,'num_format': '0.00'})
    fmt_dec2  = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
    fmt_small = workbook.add_format({'font_size': 9, 'italic': True, 'font_color': '#6B7280'})
    

    # === Sheet Data_Mining
    ws_mining = workbook.add_worksheet('Data_Mining')
    ws_mining.write_row('A1', ['Date','LIM','SAP','Waste','Quarry','Topsoil','OB','Ballast','Biomass','Actual Total','Plan Total'], fmt_th)
    for i, r in enumerate(mining["rows"], start=2):
        ws_mining.write(f'A{i}', str(r['dt']), fmt_td)
        ws_mining.write_number(f'B{i}', r['lim'] or 0, fmt_num)
        ws_mining.write_number(f'C{i}', r['sap'] or 0, fmt_num)
        ws_mining.write_number(f'D{i}', r['waste'] or 0, fmt_num)
        ws_mining.write_number(f'E{i}', r['quarry'] or 0, fmt_num)
        ws_mining.write_number(f'F{i}', r['topsoil'] or 0, fmt_num)
        ws_mining.write_number(f'G{i}', r['ob'] or 0, fmt_num)
        ws_mining.write_number(f'H{i}', r['ballast'] or 0, fmt_num)
        ws_mining.write_number(f'I{i}', r['biomass'] or 0, fmt_num)
        ws_mining.write_number(f'J{i}', r['actual_total'] or 0, fmt_num)
        ws_mining.write_number(f'K{i}', r['plan_total'] or 0, fmt_num)
    ws_mining.set_column('A:A', 12)
    ws_mining.set_column('B:K', 12)


    # === Sheet Data_Quality
    ws_quality = workbook.add_worksheet('Data_Quality')
    ws_quality.write_row('A1', ['Date', 'Total', 'LIM', 'SAP'], fmt_th)
    for i, r in enumerate(prod["rows"], start=2):
        ws_quality.write(f'A{i}', str(r['dt']), fmt_td)
        ws_quality.write_number(f'B{i}', r['prod_total'] or 0, fmt_num)
        ws_quality.write_number(f'C{i}', r.get('prod_lim', 0) or 0, fmt_num)
        ws_quality.write_number(f'D{i}', r.get('prod_sap', 0) or 0, fmt_num)
    ws_quality.set_column('A:A', 12)
    ws_quality.set_column('B:D', 12)

    # === Sheet Grade_Daily (
    ws_grade = workbook.add_worksheet('Daily_Grade')
    ws_grade.write_row(
        'A1',
        ['Date','Material','Ton','Ni','Co','Fe','MgO','SiO2','SM'],
        fmt_th
    )

    for i, r in enumerate(grade["rows"], start=2):
        ws_grade.write(f'A{i}', str(r['dt']), fmt_td)
        ws_grade.write(f'B{i}', r['nama_material'], fmt_td)
        ws_grade.write_number(f'C{i}', safe_float(r.get('total_ore')), fmt_num)
        ws_grade.write_number(f'D{i}', safe_float(r.get('ni')), fmt_num2)
        ws_grade.write_number(f'E{i}', safe_float(r.get('co')), fmt_num2)
        ws_grade.write_number(f'F{i}', safe_float(r.get('fe')), fmt_num2)
        ws_grade.write_number(f'G{i}', safe_float(r.get('mgo')), fmt_num2)
        ws_grade.write_number(f'H{i}', safe_float(r.get('sio2')), fmt_num2)
        ws_grade.write_number(f'I{i}', safe_float(r.get('sm')), fmt_num2)

    ws_grade.set_column('A:A', 12)      # Date
    ws_grade.set_column('B:B', 12)      # Material
    ws_grade.set_column('C:C', 12)      # Ton
    ws_grade.set_column('D:I', 10)      # Ni..SM


    # === Sheet Data_Selling
    ws_sell = workbook.add_worksheet('Data_Selling')
    ws_sell.write_row(
        'A1',
        ['Date', 'Actual LIM', 'Actual SAP', 'Actual Total', 'Plan LIM', 'Plan SAP', 'Plan Total'],
        fmt_th
    )

    for i, r in enumerate(sell["rows"], start=2):
        ws_sell.write(f'A{i}', str(r['dt']), fmt_td)
        ws_sell.write_number(f'B{i}', r.get('actual_lim', 0) or 0, fmt_num)
        ws_sell.write_number(f'C{i}', r.get('actual_sap', 0) or 0, fmt_num)
        ws_sell.write_number(f'D{i}', r.get('actual_total', 0) or 0, fmt_num)
        # ws_sell.write_number(f'E{i}', r.get('plan_lim', 0) or 0, fmt_num)
        # ws_sell.write_number(f'F{i}', r.get('plan_sap', 0) or 0, fmt_num)
        # ws_sell.write_number(f'G{i}', r.get('plan_total', 0) or 0, fmt_num)

    ws_sell.set_column('A:A', 12)
    ws_sell.set_column('B:G', 15)

  
    # === Sheet Barging ====
    ws_barging = workbook.add_worksheet('Barging')
    ws_barging.write_row(
        'A1',
        ['Date', 'Actual LIM', 'Actual SAP', 'Actual Total',
        'Plan LIM', 'Plan SAP', 'Plan Total', 'By Barge JSON'],
        fmt_th
    )

    for i, r in enumerate(barging["rows"], start=2):
        ws_barging.write(f'A{i}', r['label'], fmt_td)
        ws_barging.write_number(f'B{i}', r['actual_lim'] or 0, fmt_num)
        ws_barging.write_number(f'C{i}', r['actual_sap'] or 0, fmt_num)
        ws_barging.write_number(f'D{i}', r['actual_total'] or 0, fmt_num)
        # ws_barging.write_number(f'E{i}', r['plan_lim'] or 0, fmt_num)
        # ws_barging.write_number(f'F{i}', r['plan_sap'] or 0, fmt_num)
        # ws_barging.write_number(f'G{i}', r['plan_total'] or 0, fmt_num)
        ws_barging.write(f'H{i}', str(r['summary_by_barge']), fmt_td)  # simpan JSON string

    ws_barging.set_column('A:A', 12)
    ws_barging.set_column('B:G', 15)
    ws_barging.set_column('H:H', 120)  # kolom JSON panjang

    # === Sheet Barging_ByBarge
    ws_barging_b = workbook.add_worksheet('Barging_ByBarge')
    ws_barging_b.write('A1', 'Date', fmt_th)

    # Ambil semua barge_code unik dari seluruh rows
    barge_codes = set()
    for r in barging["rows"]:
        for b in r["summary_by_barge"]:
            barge_codes.add(b["barge_code"])

    barge_codes = sorted(barge_codes)  # biar urut
    for idx, code in enumerate(barge_codes, start=2):
        ws_barging_b.write(0, idx-1, code, fmt_th)  # header barge_code (kolom B,C,D...)

    # Isi data per tanggal
    for row_idx, r in enumerate(barging["rows"], start=2):
        ws_barging_b.write(f'A{row_idx}', r['label'], fmt_td)
        barge_map = {b["barge_code"]: b["total"] for b in r["summary_by_barge"]}
        for col_idx, code in enumerate(barge_codes, start=2):
            ws_barging_b.write_number(row_idx-1, col_idx-1, barge_map.get(code, 0), fmt_num)

    ws_barging_b.set_column('A:A', 12)
    ws_barging_b.set_column('B:Z', 14)


    # === Sheet Stock_Opname
    ws_inv = workbook.add_worksheet('Stock_Opname')
    ws_inv.write_row('A1', ['Date', 'Production In', 'Selling Out', 'Stock Opname'], fmt_th)

    row = 2

    # Opening Stock (ambil dari inv["summary"]["opening_balance"])
    opening_stock = inv["summary"].get("opening_balance", 0)
    ws_inv.write('A2', 'Opening Stock', fmt_th)
    ws_inv.write_number('D2', opening_stock, fmt_num)
    row += 1

    # Daily records
    for r in inv["rows"]:
        ws_inv.write(f'A{row}', str(r['dt']), fmt_td)
        ws_inv.write_number(f'B{row}', r['total_in'] or 0, fmt_num)        # Production In
        ws_inv.write_number(f'C{row}', r['total_out'] or 0, fmt_num)       # Selling Out
        ws_inv.write_number(f'D{row}', r['running_balance'] or 0, fmt_num) # Stock Opname
        row += 1

    # Closing summary
    closing_stock = to_decimal(inv["summary"].get("closing_balance", 0))
    total_in      = to_decimal(inv["summary"].get("total_in", 0))
    total_out     = to_decimal(inv["summary"].get("total_out", 0))
    net_movement  = total_in - total_out

    ws_inv.write(f'A{row}', 'Closing Stock', fmt_th)
    ws_inv.write_number(f'D{row}', closing_stock, fmt_num); row += 1

    ws_inv.write(f'A{row}', 'Net Movement', fmt_th)
    ws_inv.write_number(f'D{row}', net_movement, fmt_num); row += 1

    ws_inv.write(f'A{row}', 'Opening Stock (Next)', fmt_th)
    ws_inv.write_number(f'D{row}', closing_stock, fmt_num); row += 1

    # Set lebar kolom
    ws_inv.set_column('A:A', 20)
    ws_inv.set_column('B:D', 16)


    # === Sheet Data_Inventory (by dome / pile)
    ws_invlist = workbook.add_worksheet('Data_Inventory')
    ws_invlist.write_row(
        'A1',
        ['Stockpile', 'Dome', 'Material', 'Total Ore', 'Released',
        'Total Selling', 'Balance', 'Ni', 'Co', 'Fe', 'MgO', 'SiO2', 'SM'],
        fmt_th
    )

    for i, r in enumerate(invlist["rows"], start=2):
        ws_invlist.write(f'A{i}', r['stockpile'], fmt_td)
        ws_invlist.write(f'B{i}', r['pile_id'], fmt_td)
        ws_invlist.write(f'C{i}', r['nama_material'], fmt_td)
        ws_invlist.write_number(f'D{i}', r['total_ore'] or 0, fmt_num)
        ws_invlist.write_number(f'E{i}', r['released'] or 0, fmt_num)
        ws_invlist.write_number(f'F{i}', r['total_selling'] or 0, fmt_num)
        ws_invlist.write_number(f'G{i}', r['balance'] or 0, fmt_num)
        ws_invlist.write_number(f'H{i}', float(r['ni'] or 0), fmt_dec2)
        ws_invlist.write_number(f'I{i}', float(r['co'] or 0), fmt_dec2)
        ws_invlist.write_number(f'J{i}', float(r['fe'] or 0), fmt_dec2)
        ws_invlist.write_number(f'K{i}', float(r['mgo'] or 0), fmt_dec2)
        ws_invlist.write_number(f'L{i}', float(r['sio2'] or 0), fmt_dec2)
        ws_invlist.write_number(f'M{i}', float(r['sm'] or 0), fmt_dec2)
        # ws_invlist.write(f'N{i}', r['direct_sale'], fmt_td)

    ws_invlist.set_column('A:C', 14)   # stockpile, pile id, material
    ws_invlist.set_column('D:G', 14)   # total ore, released, selling, balance
    ws_invlist.set_column('H:N', 10)   # Ni, Co, Fe, MgO, SiO2, SM,Direct


   # === Sheet Data_Fueling
    ws_fuellist = workbook.add_worksheet('Data_Fueling')

    # Header Date & Volume
    ws_fuellist.write_row(0, 0, ['Date', 'Volume'], fmt_th)

    # Category setup
    categories = [c["category"] for c in fuel["category"]["series"]]
    category_map = {c["category"]: c["volume"] for c in fuel["category"]["series"]}

    start_col = 4  # Kolom E

    # Header category (row 0)
    for idx, cat in enumerate(categories):
        ws_fuellist.write(0, start_col + idx, cat, fmt_th)

    # Daily data
    for i, r in enumerate(fuel["daily"]["series"], start=1):
        ws_fuellist.write(i, 0, str(r['date']), fmt_td)
        ws_fuellist.write_number(i, 1, r['volume'] or 0, fmt_num)

    # Isi TOTAL category hanya di baris pertama data (row 1)
    for idx, cat in enumerate(categories):
        ws_fuellist.write_number(
            1,  # hanya satu baris
            start_col + idx,
            category_map.get(cat, 0),
            fmt_num
        )

    # Column width
    ws_fuellist.set_column('A:A', 14)  # Date
    ws_fuellist.set_column('B:B', 12)  # Volume

    col_count = len(categories)
    col_width = min(70, 120 / max(col_count, 1))
    ws_fuellist.set_column(start_col, start_col + col_count - 1, col_width)

    # tambahkan blok summary Quality, Selling, Mining :
    # === Sheet Summary
    ws_sum = workbook.add_worksheet('Summary')
    ws_sum.hide_gridlines(2)   # 2 = hide both screen & print
    ws_sum.write('A1', 'KQMS Unified Report', fmt_title)
    if mode == "range":
        ws_sum.write('A2', f'Range: {date_start} → {date_end}', fmt_small)
    elif mode == "year":
        ws_sum.write('A2', f'Year: {year}', fmt_small)

    ws_sum.write('D2', f"Generated: {localtime(timezone.now()).strftime('%Y-%m-%d, %H:%M:%S')}", fmt_small)

    # === Project Summary To-Date ===
    ws_sum.write('A4', 'Project Summary to Date', fmt_title)

    # ---------- Mining (kolom A–B, vertikal) ----------
    ws_sum.write('A6', 'Mining', fmt_th)
    ws_sum.write_row('A7', ['Metric','Value'], fmt_th)
    ws_sum.write('A8',  'Total Actual', fmt_td); ws_sum.write_number('B8', summary['mining']['actual_total'], fmt_num)
    # ws_sum.write('A9',  'Total Plan',   fmt_td); ws_sum.write_number('B9', summary['mining']['plan_total'], fmt_num)
    # ws_sum.write('A10', 'Achievement',  fmt_td); ws_sum.write('B10', f"{(summary['mining']['actual_total']/summary['mining']['plan_total']*100 if summary['mining']['plan_total'] else 0):.0f}%", fmt_td)
    ws_sum.write('A9', 'Total LIM',    fmt_td); ws_sum.write_number('B9', summary['mining']['lim_total'], fmt_num)
    ws_sum.write('A10', 'Total SAP',    fmt_td); ws_sum.write_number('B10', summary['mining']['sap_total'], fmt_num)
    ws_sum.write('A11', 'Total Waste',  fmt_td); ws_sum.write_number('B11', summary['mining']['waste_total'], fmt_num)
    ws_sum.write('A12', 'Total Quarry', fmt_td); ws_sum.write_number('B12', summary['mining']['quarry_total'], fmt_num)
    ws_sum.write('A13', 'Total Topsoil',fmt_td); ws_sum.write_number('B13', summary['mining']['topsoil_total'], fmt_num)
    ws_sum.write('A14', 'Total OB',     fmt_td); ws_sum.write_number('B14', summary['mining']['ob_total'], fmt_num)
    ws_sum.write('A15', 'Total Ballast',fmt_td); ws_sum.write_number('B15', summary['mining']['ballast_total'], fmt_num)
    ws_sum.write('A16', 'Total Biomass',fmt_td); ws_sum.write_number('B16', summary['mining']['biomass_total'], fmt_num)



    # ---------- Quality (kolom D–I, horizontal) ----------
    ws_sum.write('D6', 'Material Type', fmt_th)
    # ws_sum.write_row('D7', ['Metric','Total','LIM (total)','LIM (%)','SAP (total)','SAP (%)'], fmt_th)
    ws_sum.write_row('D7', ['Metric','Total','LIM (total)','SAP (total)'], fmt_th)

    ws_sum.write('D8', 'Value', fmt_td)
    ws_sum.write_number('E8', summary['quality']['total'] or 0, fmt_num)
    ws_sum.write_number('F8', summary['quality']['lim'] or 0, fmt_num)
    # ws_sum.write('G8', f"{(summary['quality']['lim']/summary['quality']['total']*100):.2f}%" if summary['quality']['total'] else "0%", fmt_td)
    ws_sum.write_number('G8', summary['quality']['sap'] or 0, fmt_num)
    # ws_sum.write('I8', f"{(summary['quality']['sap']/summary['quality']['total']*100):.2f}%" if summary['quality']['total'] else "0%", fmt_td)

    # ---------- Selling (kolom D–I, horizontal) ----------
    ws_sum.write('D10', 'Selling', fmt_th)
    ws_sum.write_row('D11', ['Metric','Total Actual','LIM Actual','SAP Actual'], fmt_th)

    ws_sum.write('D12', 'Value', fmt_td)
    ws_sum.write_number('E12', summary['selling']['actual'] or 0, fmt_num)
    # ws_sum.write_number('F12', summary['selling']['plan'] or 0, fmt_num)
    # ws_sum.write('G12', f"{(summary['selling']['actual']/summary['selling']['plan']*100):.0f}%" if summary['selling']['plan'] else "0%", fmt_td)
    ws_sum.write_number('F12', summary['selling']['lim_actual'] or 0, fmt_num)
    ws_sum.write_number('G12', summary['selling']['sap_actual'] or 0, fmt_num)

    # ---------- Inventory (kolom D–H, horizontal) ----------
    ws_sum.write('D14', 'Inventory', fmt_th)
    ws_sum.write_row('D15', ['Metric','Production In','Selling Out','Current Stock'], fmt_th)

    ws_sum.write('D16', 'Value', fmt_td)
    ws_sum.write_number('E16', summary['inventory']['in'] or 0, fmt_num)
    ws_sum.write_number('F16', summary['inventory']['out'] or 0, fmt_num)
    ws_sum.write_number('G16', summary['inventory']['current_stock'] or 0, fmt_num)  # pakai closing balance


    # Atur lebar kolom D–I (Quality & Selling)
    ws_sum.set_column('D:I', 12)

    # Atur lebar kolom D–H (Inventory)
    ws_sum.set_column('D:H', 12)

     # --- Buat judul dinamis ---
    if mode == "range":
        mining_title    = f"Mining by Period (Range: {date_start} → {date_end})"
        quality_title   = f"Material Type by Period (Range: {date_start} → {date_end})"
        # grade_title     = f"Daily Ore by Period (Range: {date_start} → {date_end})"
        selling_title   = f"Selling by Period (Range: {date_start} → {date_end})"
        barging_title   = f"Barging by Period (Range: {date_start} → {date_end})"
        inventory_title = f"Inventory by Period (Range: {date_start} → {date_end})"
        fuel_title      = f"Fuel Consumption by Period (Range: {date_start} → {date_end})"
    elif mode == "year":
        mining_title    = f"Mining by Period (Year: {year})"
        quality_title   = f"Material Type by Period (Year: {year})"
        # grade_title     = f"Daily Ore by Period  (Year: {year})"
        selling_title   = f"Selling by Period (Year: {year})"
        barging_title   = f"Barging by Period (Year: {year})"
        inventory_title = f"Inventory by Period (Year: {year})"
        fuel_title      = f"Fuel Consumption by Period (Year: {year})"
    else:
        mining_title    = "Mining by Period"
        quality_title   = "Material Type by Period"
        # grade_title     = "Daily Ore by Period "
        selling_title   = "Selling by Period"
        barging_title   = "Barging by Period"
        inventory_title = "Inventory by Period"
        fuel_title      = "Fuel Consumption by Period"


    # ---------------- Mining Section ----------------
    ws_sum.write('A20', mining_title, fmt_title)
    ws_sum.write_row('A21', ['Metric', 'Value'], fmt_th)
    row = 22 # mulai dari baris 22

    total_actual = sum(r["actual_total"] for r in mining["rows"]) if mining["rows"] else 0
    # total_plan   = sum(r["plan_total"] for r in mining["rows"]) if mining["rows"] else 0
    max_day = max(mining["rows"], key=lambda r: r["actual_total"]) if mining["rows"] else None
    min_day = min(mining["rows"], key=lambda r: r["actual_total"]) if mining["rows"] else None

    ws_sum.write(f'A{row}', 'Total Actual', fmt_td); ws_sum.write_number(f'B{row}', total_actual, fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'Total Plan', fmt_td); ws_sum.write_number(f'B{row}', total_plan, fmt_num); row += 1
    if max_day:
        ws_sum.write(f'A{row}', 'Max day', fmt_td)
        ws_sum.write(f'B{row}', f"{max_day['dt']} • {max_day['actual_total']:.2f}", fmt_td)
        row += 1
    if min_day:
        ws_sum.write(f'A{row}', 'Min day', fmt_td)
        ws_sum.write(f'B{row}', f"{min_day['dt']} • {min_day['actual_total']:.2f}", fmt_td)
        row += 1

    # --- Tambahan: total by material ---
    total_lim     = sum(r["lim"] for r in mining["rows"])
    total_sap     = sum(r["sap"] for r in mining["rows"])
    total_waste   = sum(r["waste"] for r in mining["rows"])
    total_quarry  = sum(r["quarry"] for r in mining["rows"])
    total_topsoil = sum(r["topsoil"] for r in mining["rows"])
    total_ob      = sum(r["ob"] for r in mining["rows"])
    total_ballast = sum(r["ballast"] for r in mining["rows"])
    total_biomass = sum(r["biomass"] for r in mining["rows"])

    ws_sum.write(f'A{row}', 'Total LIM', fmt_td); ws_sum.write_number(f'B{row}', total_lim, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total SAP', fmt_td); ws_sum.write_number(f'B{row}', total_sap, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total Waste', fmt_td); ws_sum.write_number(f'B{row}', total_waste, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total Quarry', fmt_td); ws_sum.write_number(f'B{row}', total_quarry, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total Topsoil', fmt_td); ws_sum.write_number(f'B{row}', total_topsoil, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total OB', fmt_td); ws_sum.write_number(f'B{row}', total_ob, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total Ballast', fmt_td); ws_sum.write_number(f'B{row}', total_ballast, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Total Biomass', fmt_td); ws_sum.write_number(f'B{row}', total_biomass, fmt_num); row += 1

    # Chart Mining (stacked bar + line plan)
    material_colors = {
            'LIM'       : "#f5d8aa",      # kuning
            'SAP'       : "#b1dcb5",      # hijau
            'Waste'     : "#d4c399", 
            'Quarry'    : '#365e58',   
            'Topsoil'   : "#b79d46", 
            'OB'        : "#f29b5d",      
            'Ballast'   : "#7f7f7f",  
            'Biomass'   : '#f4b0ad', 
        }   

    if mining["rows"]:
        first, last = 2, len(mining["rows"]) + 1
        categories = f'=Data_Mining!$A${first}:$A${last}'

        series_defs = []
        for col, name in zip("BCDEFGHI", ['LIM','SAP','Waste','Quarry','Topsoil','OB','Ballast','Biomass']):
            series_defs.append({
                'name': name,
                'values': f'=Data_Mining!${col}${first}:${col}${last}',
                'fill': {'color': material_colors.get(name, '#999999')}  # default abu2 kalau gak ketemu
            })

        line_defs = [{
            'name': 'Plan',
            'values': f'=Data_Mining!$K${first}:$K${last}',
            'line': {'color': "#ea5e5e", 'width': 2.25}
        }]
    else:
        categories = None
        series_defs = None
        line_defs = None

    safe_chart_multi(
        workbook,
        ws_sum,
        pos='D21',
        title='Mining Trend',
        rows=mining["rows"],
        categories=categories,
        series_defs=series_defs,
        line_defs=line_defs,   # langsung combine line plan
        scale=(2.07, 1.32),
        stacked=True,
        legend_pos='top'
    )


    # ================= Quality Summary =================
    ws_sum.write('A43', quality_title, fmt_title)
    ws_sum.write_row('A44', ['Metric', 'Value'], fmt_th)
    row = 45    # mulai dari baris 45

    total_all = sum(r["prod_total"] for r in prod["rows"]) if prod["rows"] else 0
    total_lim = sum(r.get("prod_lim", 0) for r in prod["rows"])
    total_sap = sum(r.get("prod_sap", 0) for r in prod["rows"])
    avg_daily = total_all / len(prod["rows"]) if prod["rows"] else 0
    max_day = max(prod["rows"], key=lambda r: r["prod_total"]) if prod["rows"] else None
    min_day = min(prod["rows"], key=lambda r: r["prod_total"]) if prod["rows"] else None
    pct_lim = (100 * total_lim / total_all) if total_all else 0
    pct_sap = (100 * total_sap / total_all) if total_all else 0

    ws_sum.write(f'A{row}', 'Total tonnage', fmt_td); ws_sum.write_number(f'B{row}', total_all, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Average per day', fmt_td); ws_sum.write_number(f'B{row}', avg_daily, fmt_dec2); row += 1
    ws_sum.write(f'A{row}', 'LIM (total)', fmt_td); ws_sum.write_number(f'B{row}', total_lim, fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'LIM (%)', fmt_td); ws_sum.write(f'B{row}', f'{pct_lim:.2f}%', fmt_td); row += 1
    ws_sum.write(f'A{row}', 'SAP (total)', fmt_td); ws_sum.write_number(f'B{row}', total_sap, fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'SAP (%)', fmt_td); ws_sum.write(f'B{row}', f'{pct_sap:.2f}%', fmt_td); row += 1
    if max_day:
        ws_sum.write(f'A{row}', 'Max day', fmt_td); ws_sum.write(f'B{row}', f"{max_day['dt']} • {max_day['prod_total']:.2f}", fmt_td); row += 1
    if min_day:
        ws_sum.write(f'A{row}', 'Min day', fmt_td); ws_sum.write(f'B{row}', f"{min_day['dt']} • {min_day['prod_total']:.2f}", fmt_td); row += 1

    # Chart Quality

    if prod["rows"]:
        first, last = 2, len(prod["rows"]) + 1
        categories  = f'=Data_Quality!$A${first}:$A${last}'

        series_defs = [
            {
                'name': 'LIM',
                'values': f'=Data_Quality!$C${first}:$C${last}',
                'fill': {'color': "#f8dfb7"}
            },
            {
                'name': 'SAP',
                'values': f'=Data_Quality!$D${first}:$D${last}',
                'fill': {'color': '#bdddc0'}
            }
        ]
    else:
        categories = None
        series_defs = None

    chart_q = safe_chart_multi(
        workbook,
        ws_sum,
        pos='D44',
        title='Material Type',
        rows=prod["rows"],
        categories=categories,
        series_defs=series_defs,
        scale=(2.07, 1.32),
        stacked=True,
        legend_pos='top'
    )


   # ================= Selling Summary =================
    ws_sum.write('A65', selling_title, fmt_title)
    ws_sum.write_row('A66', ['Metric', 'Value'], fmt_th)
    row = 67    # mulai dari baris 65

    total_actual = sum(r["actual_total"] for r in sell["rows"]) if sell["rows"] else 0
    # total_plan   = sum(r["plan_total"] for r in sell["rows"]) if sell["rows"] else 0
    lim_actual   = sum(r["actual_lim"] for r in sell["rows"]) if sell["rows"] else 0
    sap_actual   = sum(r["actual_sap"] for r in sell["rows"]) if sell["rows"] else 0
    # lim_plan     = sum(r["plan_lim"] for r in sell["rows"]) if sell["rows"] else 0
    # sap_plan     = sum(r["plan_sap"] for r in sell["rows"]) if sell["rows"] else 0

    avg_actual   = total_actual / len(sell["rows"]) if sell["rows"] else 0
    max_day = max(sell["rows"], key=lambda r: r["actual_total"]) if sell["rows"] else None
    min_day = min(sell["rows"], key=lambda r: r["actual_total"]) if sell["rows"] else None

    ws_sum.write(f'A{row}', 'Total Actual', fmt_td); ws_sum.write_number(f'B{row}', total_actual, fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'Total Plan', fmt_td); ws_sum.write_number(f'B{row}', total_plan, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'LIM Actual', fmt_td); ws_sum.write_number(f'B{row}', lim_actual, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'SAP Actual', fmt_td); ws_sum.write_number(f'B{row}', sap_actual, fmt_num); row += 1
    ws_sum.write(f'A{row}', 'Average Actual / day', fmt_td); ws_sum.write_number(f'B{row}', avg_actual, fmt_dec2); row += 1
    # ws_sum.write(f'A{row}', 'LIM Plan', fmt_td); ws_sum.write_number(f'B{row}', lim_plan, fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'SAP Plan', fmt_td); ws_sum.write_number(f'B{row}', sap_plan, fmt_num); row += 1
    if max_day:
        ws_sum.write(f'A{row}', 'Max Actual Day', fmt_td)
        ws_sum.write(f'B{row}', f"{max_day['dt']} • {max_day['actual_total']:.2f}", fmt_td); row += 1
    if min_day:
        ws_sum.write(f'A{row}', 'Min Actual Day', fmt_td)
        ws_sum.write(f'B{row}', f"{min_day['dt']} • {min_day['actual_total']:.2f}", fmt_td); row += 1

 
    if sell["rows"]:
        first, last = 2, len(sell["rows"]) + 1
        categories = f'=Data_Selling!$A${first}:$A${last}'

        # Series stacked bar
        series_defs = [
            {
                'name': 'LIM',
                'values': f'=Data_Selling!$B${first}:${"B"}${last}',
                'fill': {'color': '#ffedd1'}
            },
            {
                'name': 'SAP',
                'values': f'=Data_Selling!$C${first}:${"C"}${last}',
                'fill': {'color': "#bdddc0"}
            }
        ]

        # Series line
        # line_defs = [
        #     {
        #         'name': 'Plan Total',
        #         'values': f'=Data_Selling!$G${first}:${"G"}${last}',
        #         'line': {'color': "#fe927a", 'width': 2.25}
        #     }
        # ]
    else:
        categories = None
        series_defs = None
        line_defs = None

    safe_chart_multi(
        workbook,
        ws_sum,
        pos='D66',
        title='Selling Trend',
        rows=sell["rows"],
        categories=categories,
        series_defs=series_defs,
        line_defs=None,   #  line langsung combine
        scale=(2.07, 1.32),
        stacked=True,
        legend_pos='top'
    )


    # ================= Barging Summary =================
    ws_sum.write('A87', barging_title, fmt_title)
    ws_sum.write_row('A88', ['Metric', 'Value'], fmt_th)
    row = 89

    summary_b = barging["summary"]

    ws_sum.write(f'A{row}', 'Actual Total', fmt_td); ws_sum.write_number(f'B{row}', summary_b["actual_total"], fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'Plan Total', fmt_td); ws_sum.write_number(f'B{row}', summary_b["plan_total"], fmt_num); row += 1
    ws_sum.write(f'A{row}', 'LIM Actual', fmt_td); ws_sum.write_number(f'B{row}', summary_b["lim_actual"], fmt_num); row += 1
    ws_sum.write(f'A{row}', 'SAP Actual', fmt_td); ws_sum.write_number(f'B{row}', summary_b["sap_actual"], fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'LIM Plan', fmt_td); ws_sum.write_number(f'B{row}', summary_b["lim_plan"], fmt_num); row += 1
    # ws_sum.write(f'A{row}', 'SAP Plan', fmt_td); ws_sum.write_number(f'B{row}', summary_b["sap_plan"], fmt_num); row += 1

    # Palet warna 
    palette = [
        "#72b1ab",  # biru
        "#a4c3f4",  # biru
        "#bddddc",  # hijau
        "#ffedd1",  # kuning
        "#fe927a",  # ungu
        "#d0b97f",  # teal
        "#365e58",  # oranye
        "#8192aa",  # abu2
    ]


    if barging["rows"]:
        first, last = 2, len(barging["rows"]) + 1
        categories  = f'=Barging_ByBarge!$A${first}:$A${last}'
        series_defs = []
        for idx, code in enumerate(barge_codes, start=2):
            color = palette[(idx - 2) % len(palette)]  # ambil warna dari palet
            series_defs.append({
                'name': code,
                'values': f'=Barging_ByBarge!${chr(64+idx)}${first}:${chr(64+idx)}${last}',
                'fill': {'color': color} 
            })
    else:
        categories = None
        series_defs = None

    safe_chart_multi(
        workbook,
        ws_sum,
        pos='D88',
        title='Barging by Barge Code',
        rows=barging["rows"],
        categories=categories,
        series_defs=series_defs,
        scale=(2.07, 1.32),
        stacked=True,
        legend_pos='top'
    )

    
    # ================= Inventory Summary =================
    ws_sum.write('A109', inventory_title, fmt_title)
    ws_sum.write_row('A110', ['Metric', 'Value'], fmt_th)
    row = 111  # mulai dari baris 109

    opening_stock = to_decimal(inv["summary"].get("opening_balance"))
    closing_stock = to_decimal(inv["summary"].get("closing_balance"))
    total_in      = to_decimal(inv["summary"].get("total_in"))
    total_out     = to_decimal(inv["summary"].get("total_out"))
    net_movement  = total_in - total_out

    ws_sum.write(f'A{row}', 'Opening Stock', fmt_td)
    ws_sum.write_number(f'B{row}', opening_stock, fmt_num); row += 1

    ws_sum.write(f'A{row}', 'Production In', fmt_td)
    ws_sum.write_number(f'B{row}', total_in, fmt_num); row += 1

    ws_sum.write(f'A{row}', 'Selling Out', fmt_td)
    ws_sum.write_number(f'B{row}', total_out, fmt_num); row += 1

    ws_sum.write(f'A{row}', 'Closing Stock', fmt_td)
    ws_sum.write_number(f'B{row}', closing_stock, fmt_num); row += 1

    ws_sum.write(f'A{row}', 'Net Movement', fmt_td)
    ws_sum.write_number(f'B{row}', net_movement, fmt_num); row += 1

    # buat carry forward
    ws_sum.write(f'A{row}', 'Opening Stock (Next)', fmt_td)
    ws_sum.write_number(f'B{row}', closing_stock, fmt_num); row += 1

   
    if inv["rows"]:
        first, last = 2, len(inv["rows"]) + 1
        categories = f'=Stock_Opname!$A${first}:$A${last}'

        series_defs = [
            {
                'name': 'Production In',
                'values': f'=Stock_Opname!$B${first}:$B${last}',
                # 'fill': {'color': '#bddddc', 'transparency': 75},
                'fill': {'color': '#bddddc', 'transparency': 25},
                'smooth': True
            },
            {
                'name': 'Selling Out',
                'values': f'=Stock_Opname!$C${first}:$C${last}',
                'fill': {'color': '#ffedd1', 'transparency': 30},
                'smooth': True
            }
        ]

        line_defs = [
            {
                'name': 'Stock Opname',
                'values': f'=Stock_Opname!$D${first}:$D${last}',
                'line': {'color': '#fe927a', 'width': 2.5, 'dash_type': 'dash'},
                'y2_axis': True,
                'smooth': True
            }
        ]
    else:
        categories = None
        series_defs = None
        line_defs = None

    safe_chart_multi(
        workbook,
        ws_sum,
        pos='D110',
        title='Inventory Trend',
        rows=inv["rows"],
        categories=categories,
        series_defs=series_defs,
        line_defs=line_defs,
        scale=(2.07, 1.32),
        chart_type='area' if mode == "range" else 'column',
        stacked=True if mode == "range" else False,
        legend_pos='top',
        y_axis={'name': 'Production / Selling'},
        y2_axis={'name': 'Stock Opname'}
    )

    # Lebarkan kolom summary
    ws_sum.set_column('A:A', 21)
    ws_sum.set_column('B:B', 25)

   # ================= Fueling Summary =================
    ws_sum.write('A131', fuel_title, fmt_title)
    row = 133

    # ambil baris terakhir data fueling (Data_Fueling!B)
    last_row = len(fuel["daily"]["series"]) + 1

    # ---------------- Total Fuel ----------------
    ws_sum.write(f'A{row}', 'Total Fuel', fmt_td)
    ws_sum.write_formula(
        f'B{row}',
        f'=SUM(Data_Fueling!$B$2:$B${last_row})',
        fmt_num
    )
    row += 2


    # ================= Fuel by Category =================
    ws_sum.write(f'A{row}', 'Fuel by Category', fmt_title)
    row += 1

    # header tabel
    ws_sum.write_row(f'A{row}', ['Category', 'Total Volume'], fmt_th)
    row += 1

    category_start_row = row

    # isi tabel kategori
    for c in fuel["category"]["series"]:
        ws_sum.write(f'A{row}', c['category'], fmt_td)
        ws_sum.write_number(f'B{row}', c['volume'], fmt_num)
        row += 1

    # category_end_row = row - 1
    category_end_row = 131
    trend_chart_row = category_end_row + 2

    # ================= Fuel by Category Chart =================
    # chart_category = workbook.add_chart({'type': 'bar'})

    # chart_category.add_series({
    #     'name': 'Fuel Volume',
    #     'categories': f"=Summary!$A${category_start_row}:$A${category_end_row}",
    #     'values':     f"=Summary!$B${category_start_row}:$B${category_end_row}",
    #     'data_labels': {'value': True},
    #     'fill': {'color': '#bddddc'},
    # })

    # chart_category.set_title({'name': 'Fuel by Category'})
    # chart_category.set_x_axis({'name': 'Volume'})
    # chart_category.set_y_axis({'reverse': True})
    # chart_category.set_legend({'none': True})
    # chart_category.set_style(10)

    # ws_sum.insert_chart(
    #     f'D{category_start_row}',
    #     chart_category,
    #     {'x_scale': 1.4, 'y_scale': 1.3}
    # )


    # ================= Fuel Trend by Date Chart =================
    chart_type = 'column' if mode == "range" else 'column'
    chart_date = workbook.add_chart({'type': chart_type})

    chart_date.add_series({
        'name': 'Fuel Volume',
        'categories': f'=Data_Fueling!$A$2:$A${last_row}',
        'values':     f'=Data_Fueling!$B$2:$B${last_row}',
        'fill': {'color': '#9cc3c1', 'transparency': 20},
        'smooth': True if chart_type == 'column' else False,
    })

    chart_date.set_title({'name': 'Fuel Consumption'})
    chart_date.set_x_axis({
        'name': 'Date',
        'num_font': {'rotation': 45, 'bold': True, 'size': 10},
    })
    chart_date.set_y_axis({'name': 'Volume'})
    chart_date.set_legend({'none': True})
    chart_date.set_style(10)

    # posisi: DI BAWAH chart category
    ws_sum.insert_chart(
        # f'D{category_end_row + 18}',
        f'D{trend_chart_row}',
        chart_date,
        {'x_scale': 2.07, 'y_scale': 1.32}  
    )


    # ================= Column Width =================
    ws_sum.set_column('A:A', 21)
    ws_sum.set_column('B:B', 25)


  
    # Close workbook
    workbook.close()
    output.seek(0)

    filename = f"KQMS-summary_{date_start}_to_{date_end}.xlsx"
    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

