# reports/views.py
from io import BytesIO
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from datetime import date,datetime
from collections import defaultdict
import xlsxwriter
from .get_compare_coa import (
    fetch_official_split,
    fetch_official_split_year,
)
from analytics.views.barging.split_sample.range_monitoring import get_samples_data
from analytics.views.barging.split_sample.range_summary import get_samples_monitoring
from analytics.views.barging.split_sample.range_re_assay import get_samples_re_assay_summary
from analytics.views.barging.split_sample.range_shipment import (
    get_shipment_summary_buyer,
    get_shipment_summary_month,
)

def export_excel_coa(request):
    iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter"),
    mode       = request.GET.get("mode") or "range"   # default: range
    date_start = request.GET.get("date_start") or str(date.today().replace(day=1))
    date_end   = request.GET.get("date_end")   or str(date.today())
    year       = request.GET.get("year")       # untuk mode=year
    material   = request.GET.get("material") 

    # Inisialisasi default
    data_coa = []
    samples_data = []
    monitoring_data_original = []
    monitoring_data_reassay = []
    monitoring_by_shipment = []
    monitoring_by_month = []

    # Ambil data
    if mode == "range":
        data_coa = fetch_official_split(date_start, date_end, material,iup_filter=iup_filter)
        samples_data = get_samples_data(typeFilter=material, startDate=date_start, endDate=date_end,iup_filter=iup_filter)
        monitoring_data_original = get_samples_monitoring(typeFilter=material, startDate=date_start, endDate=date_end,iup_filter=iup_filter)
        monitoring_data_reassay = get_samples_re_assay_summary(typeFilter=material, startDate=date_start, endDate=date_end,iup_filter=iup_filter)
        monitoring_by_shipment = get_shipment_summary_buyer(typeFilter=material, startDate=date_start, endDate=date_end,iup_filter=iup_filter)
        monitoring_by_month = get_shipment_summary_month(startDate=date_start, endDate=date_end,iup_filter=iup_filter)

    elif mode == "year" and year:
        try:
            year = int(year)
        except ValueError:
            return HttpResponseBadRequest("Invalid year parameter")
        data_coa = fetch_official_split_year(year, material)
    else:
        return HttpResponseBadRequest("Invalid mode or missing parameters")

    # Setup workbook
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    # Styles
    fmt_title = workbook.add_format({'bold': True, 'font_size': 14})
    fmt_th    = workbook.add_format({'bold': True, 'bg_color': '#F3F4F6', 'border': 1})
    fmt_td    = workbook.add_format({'border': 1,'align': 'left','valign': 'vleft'})
    fmt_num   = workbook.add_format({'border': 1, 'num_format': '#,##0'})
    fmt_dec2  = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
    fmt_small = workbook.add_format({'font_size': 9, 'italic': True, 'font_color': '#6B7280'})
    fmt_date  = workbook.add_format({'num_format': 'yyyy-mm-dd', 'border': 1})

    

    # === Sheet Monitoring ===
    ws_mon = workbook.add_worksheet("Monitoring")
    headers_mon = ["No", "Code Lot", "Barge Code", "Quantity", "Sample source",
                   "Ni", "Fe", "Co", "MgO", "SiO2", "S/M"]
    ws_mon.write_row(0, 0, headers_mon, fmt_th)

    row_idx = 1
    no = 1
    for r in samples_data:
        qty = r.get("tonnage_split") or 0
        samples = [
            {"source": "Plan", "ni": r.get("ni_plan"), "fe": r.get("fe_plan"),
             "co": r.get("co_plan"), "mgo": r.get("mgo_plan"), "sio2": r.get("sio2_plan")},
            {"source": "Monitoring", "ni": r.get("ni_monitoring"), "fe": r.get("fe_monitoring"),
             "co": r.get("co_monitoring"), "mgo": r.get("mgo_monitoring"), "sio2": r.get("sio2_monitoring")},
            {"source": "Split", "ni": r.get("ni_split"), "fe": r.get("fe_split"),
             "co": r.get("co_split"), "mgo": r.get("mgo_split"), "sio2": r.get("sio2_split")},
        ]
        if r.get("officials"):
            for i, o in enumerate(r["officials"]):
                samples.append({
                    "source": f"COA - {i}",
                    "ni": o.get("ni"),
                    "fe": o.get("fe"),
                    "co": o.get("co"),
                    "mgo": o.get("mgo"),
                    "sio2": o.get("sio2")
                })

        first = samples[0]
        sm_val = (first["sio2"] / first["mgo"]) if first["mgo"] else 0
        ws_mon.write(row_idx, 0, no,fmt_td)
        ws_mon.write(row_idx, 1, r.get("code_lot"),fmt_td)
        ws_mon.write(row_idx, 2, r.get("barge_code"),fmt_td)
        ws_mon.write_number(row_idx, 3, qty, fmt_dec2)
        ws_mon.write(row_idx, 4, first["source"],fmt_td)
        ws_mon.write_number(row_idx, 5, first["ni"] or 0, fmt_dec2)
        ws_mon.write_number(row_idx, 6, first["fe"] or 0, fmt_dec2)
        ws_mon.write_number(row_idx, 7, first["co"] or 0, fmt_dec2)
        ws_mon.write_number(row_idx, 8, first["mgo"] or 0, fmt_dec2)
        ws_mon.write_number(row_idx, 9, first["sio2"] or 0, fmt_dec2)
        ws_mon.write_number(row_idx, 10, sm_val, fmt_dec2)
        row_idx += 1

        for s in samples[1:]:
            sm_val = (s["sio2"] / s["mgo"]) if s["mgo"] else 0
            ws_mon.write(row_idx, 4, s["source"],fmt_td)
            ws_mon.write_number(row_idx, 5, s["ni"] or 0, fmt_dec2)
            ws_mon.write_number(row_idx, 6, s["fe"] or 0, fmt_dec2)
            ws_mon.write_number(row_idx, 7, s["co"] or 0, fmt_dec2)
            ws_mon.write_number(row_idx, 8, s["mgo"] or 0, fmt_dec2)
            ws_mon.write_number(row_idx, 9, s["sio2"] or 0, fmt_dec2)
            ws_mon.write_number(row_idx, 10, sm_val, fmt_dec2)
            row_idx += 1

        no += 1

    ws_mon.set_column('A:A', 5)
    ws_mon.set_column('B:C', 15)
    ws_mon.set_column('D:D', 12)
    ws_mon.set_column('E:E', 20)
    ws_mon.set_column('F:J', 12)
    ws_mon.set_column('K:K', 10)

    # === Sheet Summary Reconcile ===
    ws_sum  = workbook.add_worksheet("Reconcile")
    fmt_th  = workbook.add_format({'bold': True, 'bg_color': "#E0E0DF", 'border': 1})
    fmt_th_center = workbook.add_format({
    'bold': True,
    'bg_color': "#AEAFAC",
    'border': 1,
    'align': 'center',     # center horizontal
    'valign': 'vcenter'    # center vertical
    })
    fmt_th_right = workbook.add_format({
    'bold': True,
    'bg_color': "#E0E0DF",
    'border': 1,
    'align': 'right',     # right horizontal
    'valign': 'vright'    # right vertical
    })
    fmt_dec2 = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    fmt_date = workbook.add_format({''
    'num_format': 'yyyy-mm-dd', 
    'border': 1,
    'align': 'left',
    'valign': 'vleft'
    })
    fmt_txt  = workbook.add_format({ 'border': 1})
    row_cursor = 0

    def write_table(ws, start_row, data, subtotal_keys=None, title=None):
        """Menulis tabel dengan header multi-level Ni/Fe/S-M"""
        # Judul tabel
        if title:
            ws.merge_range(start_row, 0, start_row, 15, title, fmt_th)
            start_row += 1

        # Header utama
        ws.merge_range(start_row, 0, start_row+1, 0, "No", fmt_th_center)
        ws.merge_range(start_row, 1, start_row+1, 1, "Completed", fmt_th_center)
        ws.merge_range(start_row, 2, start_row+1, 2, "Tagboat", fmt_th_center)
        ws.merge_range(start_row, 3, start_row+1, 3, "Quantity", fmt_th_center)
        ws.merge_range(start_row, 4, start_row, 7, "Ni", fmt_th_center)
        ws.merge_range(start_row, 8, start_row, 11, "Fe", fmt_th_center)
        ws.merge_range(start_row, 12, start_row, 15, "S/M", fmt_th_center)

        # Sub-header
        sub_headers = ["Internal", "COA", "diff", "%diff"] * 3
        ws.write_row(start_row+1, 4, sub_headers, fmt_th_right)

        # Data
        r_idx = start_row + 2
        for i, r in enumerate(data, start=1):
            ws.write(r_idx, 0, i,fmt_txt)
            # ws.write(r_idx, 1, r.get("date_barge_out") or "")
            date_val = r.get("date_barge_out")
            if date_val:
                try:
                    # jika sudah datetime
                    ws_sum.write_datetime(r_idx, 1, date_val, fmt_date)
                except Exception:
                    try:
                        # coba parse string "YYYY-MM-DD"
                        parsed = datetime.strptime(str(date_val), "%Y-%m-%d")
                        ws_sum.write_datetime(r_idx, 1, parsed, fmt_date)
                    except:
                        # fallback: tulis string
                        ws_sum.write(r_idx, 1, str(date_val))
            else:
                ws_sum.write(r_idx, 1, "")
            ws.write(r_idx, 2, r.get("barge_name") or "",fmt_txt)
            ws.write_number(r_idx, 3, r.get("tonnage_official") or 0, fmt_dec2)

            # Ni
            ws.write_number(r_idx, 4, r.get("ni_split") or 0, fmt_dec2)
            ws.write_number(r_idx, 5, r.get("ni_official") or 0, fmt_dec2)
            ws.write_number(r_idx, 6, r.get("ni_diff") or 0, fmt_dec2)
            ws.write_number(r_idx, 7, r.get("ni_diff_perc") or 0, fmt_dec2)

            # Fe
            ws.write_number(r_idx, 8, r.get("fe_split") or 0, fmt_dec2)
            ws.write_number(r_idx, 9, r.get("fe_official") or 0, fmt_dec2)
            ws.write_number(r_idx,10, r.get("fe_diff") or 0, fmt_dec2)
            ws.write_number(r_idx,11, r.get("fe_diff_perc") or 0, fmt_dec2)

            # S/M
            ws.write_number(r_idx,12, r.get("sm_split") or 0, fmt_dec2)
            ws.write_number(r_idx,13, r.get("sm_official") or 0, fmt_dec2)
            ws.write_number(r_idx,14, r.get("sm_diff") or 0, fmt_dec2)
            ws.write_number(r_idx,15, r.get("sm_diff_perc") or 0, fmt_dec2)

            r_idx += 1

        # Grand Total
        if subtotal_keys:
            ws.write(r_idx, 1, "Grand Total", fmt_th)
            for idx, key in enumerate(subtotal_keys, start=3):
                total = sum(r.get(key, 0) or 0 for r in data)
                ws.write_number(r_idx, idx, total, fmt_dec2)
            r_idx += 2

        return r_idx

    # Keys untuk subtotal
    subtotal_keys1 = ["tonnage_official","ni_split","ni_official","ni_diff","ni_diff_perc",
                    "fe_split","fe_official","fe_diff","fe_diff_perc",
                    "sm_split","sm_official","sm_diff","sm_diff_perc"]

    # Tulis semua tabel
    row_cursor = write_table(ws_sum, row_cursor, monitoring_data_original, subtotal_keys1, title="All Selling Original")
    row_cursor = write_table(ws_sum, row_cursor, monitoring_data_reassay, subtotal_keys1, title="All Shipment after Re-Assay")

    # ==== Tabel per Buyer ====
    grouped_by_buyer = defaultdict(list)
    for r in monitoring_by_shipment:
        buyer_name = r.get("buyer") or "Unknown"
        grouped_by_buyer[buyer_name].append(r)

    for buyer, data_by_buyer in grouped_by_buyer.items():
        row_cursor = write_table(ws_sum, row_cursor, data_by_buyer, subtotal_keys1, title=f"Shipment to {buyer}")

    # Atur lebar kolom
    ws_sum.set_column('A:A', 5)    # No
    ws_sum.set_column('B:B', 15)   # Completed
    ws_sum.set_column('C:C', 27)   #  Tagboat
    ws_sum.set_column('D:P', 12)   # Quantity + Ni/Fe/S-M


   # === Sheet Finally ===
    ws_final = workbook.add_worksheet("Finally")
    fmt_th_center = workbook.add_format({'bold': True, 'bg_color': "#C1C1C0", 'border':1, 'align':'center', 'valign':'vcenter'})
    fmt_dec2_center = workbook.add_format({'num_format':'#,##0.00', 'border':1, 'align':'center'})
    fmt_txt  = workbook.add_format({'border': 1})
    fmt_bold = workbook.add_format({'bold': True})
    fmt_th = fmt_th_center  # untuk subtotal

    row_cursor = 0

    # Header
    headers = ["No", "Month", "Type", "Destination", "Barge", "Quantity",
            "Ni", "Fe", "S/M", "Ni", "Fe", "S/M"]
    ws_final.write_row(row_cursor, 0, headers, fmt_th_center)
    row_cursor += 1

    # Group per month
    grouped_by_month = defaultdict(list)

    # pastikan iterable
    rows_to_iterate = monitoring_by_month.get("data", []) if isinstance(monitoring_by_month, dict) else monitoring_by_month

    for r in rows_to_iterate:
        grouped_by_month[r["month_name"]].append(r)

    no = 1
    grand_totals = {"tonnage_split":0, "ni_split":0, "fe_split":0, "sm_split":0,
                    "ni_official":0, "fe_official":0, "sm_official":0}

    for month, rows in grouped_by_month.items():
        month_start_row = row_cursor
        month_totals = {"tonnage_split":0, "ni_split":0, "fe_split":0, "sm_split":0,
                        "ni_official":0, "fe_official":0, "sm_official":0}
        for r in rows:
            ws_final.write_number(row_cursor, 0, no, fmt_txt)
            ws_final.write(row_cursor, 1, month, fmt_txt)
            ws_final.write(row_cursor, 2, "Limonite" if r["type_selling"]=="LIS" else "Saprolite", fmt_txt)
            ws_final.write(row_cursor, 3, r["buyer"], fmt_txt)
            ws_final.write_number(row_cursor, 4, r["total_barge"], fmt_txt)
            ws_final.write_number(row_cursor, 5, r.get("tonnage_split",0), fmt_dec2_center)
            ws_final.write_number(row_cursor, 6, r.get("ni_split",0), fmt_dec2_center)
            ws_final.write_number(row_cursor, 7, r.get("fe_split",0), fmt_dec2_center)
            ws_final.write_number(row_cursor, 8, r.get("sm_split",0), fmt_dec2_center)
            ws_final.write_number(row_cursor, 9, r.get("ni_official",0), fmt_dec2_center)
            ws_final.write_number(row_cursor,10, r.get("fe_official",0), fmt_dec2_center)
            ws_final.write_number(row_cursor,11, r.get("sm_official",0), fmt_dec2_center)
            
            # update subtotal
            for key in month_totals.keys():
                month_totals[key] += r.get(key,0)
            for key in grand_totals.keys():
                grand_totals[key] += r.get(key,0)
            
            row_cursor += 1
            no += 1

        # Tulis subtotal per bulan
        ws_final.merge_range(row_cursor, 0, row_cursor, 4, f"Total {month}", fmt_th)
        ws_final.write_number(row_cursor, 5, month_totals["tonnage_split"], fmt_dec2_center)
        ws_final.write_number(row_cursor, 6, month_totals["ni_split"], fmt_dec2_center)
        ws_final.write_number(row_cursor, 7, month_totals["fe_split"], fmt_dec2_center)
        ws_final.write_number(row_cursor, 8, month_totals["sm_split"], fmt_dec2_center)
        ws_final.write_number(row_cursor, 9, month_totals["ni_official"], fmt_dec2_center)
        ws_final.write_number(row_cursor,10, month_totals["fe_official"], fmt_dec2_center)
        ws_final.write_number(row_cursor,11, month_totals["sm_official"], fmt_dec2_center)
        row_cursor += 2

    # Tulis Grand Total
    ws_final.merge_range(row_cursor, 0, row_cursor, 4, "Grand Total", fmt_bold)
    ws_final.write_number(row_cursor, 5, grand_totals["tonnage_split"], fmt_dec2_center)
    ws_final.write_number(row_cursor, 6, grand_totals["ni_split"], fmt_dec2_center)
    ws_final.write_number(row_cursor, 7, grand_totals["fe_split"], fmt_dec2_center)
    ws_final.write_number(row_cursor, 8, grand_totals["sm_split"], fmt_dec2_center)
    ws_final.write_number(row_cursor, 9, grand_totals["ni_official"], fmt_dec2_center)
    ws_final.write_number(row_cursor,10, grand_totals["fe_official"], fmt_dec2_center)
    ws_final.write_number(row_cursor,11, grand_totals["sm_official"], fmt_dec2_center)

    # Kolom lebar
    ws_final.set_column('A:A', 5)
    ws_final.set_column('B:B', 10)
    ws_final.set_column('C:C', 12)
    ws_final.set_column('D:D', 15)
    ws_final.set_column('E:E', 6)
    ws_final.set_column('F:L', 12)


    # === Sheet Official vs Split ===
    ws_coa = workbook.add_worksheet("Official_vs_Split")
    headers = [
        "Date In","Code Lot","Barge Code","Barge Name","Tonnage Split","Ni Split","Fe Split","MgO Split","SiO₂ Split",
        "Tonnage Official","Ni Official","Fe Official","MgO Official","SiO₂ Official",
        "Tonnage Diff","Ni Diff %","Fe Diff %","MgO Diff %","SiO₂ Diff %"
    ]
    ws_coa.write_row(0, 0, headers, fmt_th)

    for row_idx, r in enumerate(data_coa["rows"], start=1):
        date_val = r.get("date_barge_in")
        if date_val:
            try:
                ws_coa.write_datetime(row_idx, 0, date_val, fmt_date)
            except Exception:
                try:
                    parsed = datetime.strptime(str(date_val), "%Y-%m-%d")
                    ws_coa.write_datetime(row_idx, 0, parsed, fmt_date)
                except:
                    ws_coa.write(row_idx, 0, str(date_val))
        else:
            ws_coa.write(row_idx, 0, "")

        ws_coa.write(row_idx, 1, r.get("code_lot"),fmt_td)
        ws_coa.write(row_idx, 2, r.get("barge_code"),fmt_td)
        ws_coa.write(row_idx, 3, r.get("barge_name"),fmt_td)
        ws_coa.write_number(row_idx, 4, r.get("tonnage_split") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 5, r.get("ni_split") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 6, r.get("fe_split") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 7, r.get("mgo_split") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 8, r.get("sio2_split") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 9, r.get("tonnage_official") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 10, r.get("ni_official") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 11, r.get("fe_official") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 12, r.get("mgo_official") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 13, r.get("sio2_official") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 14, r.get("tonnage_diff") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 15, r.get("ni_diff") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 16, r.get("fe_diff") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 17, r.get("mgo_diff") or 0,fmt_dec2)
        ws_coa.write_number(row_idx, 18, r.get("sio2_diff") or 0,fmt_dec2)

    ws_coa.set_column('A:A', 15)
    ws_coa.set_column('B:B', 15)
    ws_coa.set_column('C:C', 16)
    ws_coa.set_column('D:D', 25)
    ws_coa.set_column('E:S', 14)

    # === Sheet Chart ===
    ws_sum_coa = workbook.add_worksheet('Chart')
    ws_sum_coa.hide_gridlines(2)
    ws_sum_coa.write('A1', 'Official vs Split COA', fmt_title)
    ws_sum_coa.write('A2', f'Range: {date_start} → {date_end}', fmt_small)

    total_split_ni  = sum(r["ni_split"]  or 0 for r in data_coa["rows"])
    total_split_fe  = sum(r["fe_split"]  or 0 for r in data_coa["rows"])
    total_split_mgo = sum(r["mgo_split"] or 0 for r in data_coa["rows"])
    total_split_sio2= sum(r["sio2_split"]or 0 for r in data_coa["rows"])
    total_off_ni  = sum(r["ni_official"]  or 0 for r in data_coa["rows"])
    total_off_fe  = sum(r["fe_official"]  or 0 for r in data_coa["rows"])
    total_off_mgo = sum(r["mgo_official"] or 0 for r in data_coa["rows"])
    total_off_sio2= sum(r["sio2_official"]or 0 for r in data_coa["rows"])

    ni_diff  = ((total_split_ni - total_off_ni) / total_off_ni * 100) if total_off_ni else 0
    fe_diff  = ((total_split_fe - total_off_fe) / total_off_fe * 100) if total_off_fe else 0
    mgo_diff = ((total_split_mgo - total_off_mgo) / total_off_mgo * 100) if total_off_mgo else 0
    sio2_diff= ((total_split_sio2 - total_off_sio2) / total_off_sio2 * 100) if total_off_sio2 else 0

    rows_summary = [
        ("Ni", total_split_ni, total_off_ni, ni_diff),
        ("Fe", total_split_fe, total_off_fe, fe_diff),
        ("MgO", total_split_mgo, total_off_mgo, mgo_diff),
        ("SiO₂", total_split_sio2, total_off_sio2, sio2_diff),
    ]

    

    # === Chart Ni Internal vs Official ===
    chart_ni = workbook.add_chart({'type': 'column'})
    chart_ni.set_title({'name': 'Internal vs Official (Ni%)'})
    chart_ni.set_legend({'position': 'bottom'})

    chart_ni.add_series({
        'name': 'Ni Internal',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$F$2:$F${len(data_coa['rows'])+1}",
        'fill': {'color': '#3b82f6'}  # biru
    })
    chart_ni.add_series({
        'name': 'Ni Official',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$K$2:$K${len(data_coa['rows'])+1}",
        'fill': {'color': '#f59e0b'}  # oranye
    })

    # Insert ke Summary
    ws_sum_coa.insert_chart('B5', chart_ni, {'x_scale': 1.7, 'y_scale': 1.2})


    


    # === Chart Fe Internal vs Official ===
    chart_fe = workbook.add_chart({'type': 'column'})
    chart_fe.set_title({'name': 'Internal vs Official (Fe%)'})
    chart_fe.set_legend({'position': 'bottom'})

    chart_fe.add_series({
        'name': 'Fe Internal',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$G$2:$G${len(data_coa['rows'])+1}",
        'fill': {'color': '#3b82f6'}
    })
    chart_fe.add_series({
        'name': 'Fe Official',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$L$2:$L${len(data_coa['rows'])+1}",
        'fill': {'color': '#f59e0b'}
    })

    # Insert ke Summary (letakkan agak bawah)
    ws_sum_coa.insert_chart('P5', chart_fe, {'x_scale': 1.7, 'y_scale': 1.2})

    # === Chart MgO Internal vs Official ===
    chart_mgo = workbook.add_chart({'type': 'column'})
    chart_mgo.set_title({'name': 'Internal vs Official (MgO%)'})
    chart_mgo.set_legend({'position': 'bottom'})

    chart_mgo.add_series({
        'name': 'MgO Internal',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$H$2:$H${len(data_coa['rows'])+1}",
        'fill': {'color': '#3b82f6'}
    })
    chart_mgo.add_series({
        'name': 'MgO Official',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$M$2:$M${len(data_coa['rows'])+1}",
        'fill': {'color': '#f59e0b'}
    })

    # Insert ke Summary (letakkan agak bawah)
    ws_sum_coa.insert_chart('B25', chart_mgo, {'x_scale': 1.7, 'y_scale': 1.2})

     # === Chart SiO2 Internal vs Official ===
    chart_sio2 = workbook.add_chart({'type': 'column'})
    chart_sio2.set_title({'name': 'Internal vs Official (SiO2%)'})
    chart_sio2.set_legend({'position': 'bottom'})

    chart_sio2.add_series({
        'name': 'SiO2 Internal',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$I$2:$I${len(data_coa['rows'])+1}",
        'fill': {'color': '#3b82f6'}
    })
    chart_sio2.add_series({
        'name': 'SiO2 Official',
        'categories': f"=Official_vs_Split!$C$2:$C${len(data_coa['rows'])+1}",
        'values':     f"=Official_vs_Split!$N$2:$N${len(data_coa['rows'])+1}",
        'fill': {'color': '#f59e0b'}
    })

    # Insert ke Summary (letakkan agak bawah)
    ws_sum_coa.insert_chart('P25', chart_sio2, {'x_scale': 1.7, 'y_scale': 1.2})


    # Close workbook
    workbook.close()
    output.seek(0)

    filename = f"KQMS-summary_COA_{date_start}_to_{date_end}.xlsx"
    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp
