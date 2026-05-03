# reports/views.py
from io import BytesIO
from django.http import HttpResponse,HttpResponseBadRequest
from datetime import date
import xlsxwriter

from .get_raw_data import (
 export_production_mining,
 export_production_quality,
 export_selling_quality,
 export_inventory_dome
)

def export_module_excel(request):
    iup_filter = request.GET.get("iup_id") or request.GET.get("iup_filter")
    module     = request.GET.get("module")   # mining / quality / selling / inventory
    date_start = request.GET.get("date_start") or str(date.today().replace(day=1))
    date_end   = request.GET.get("date_end") or str(date.today())

    if not module:
        return HttpResponseBadRequest("Missing module parameter")

    if module == "mining":
        data     = export_production_mining(date_start, date_end,iup_filter=iup_filter)   # FIXED
        output   = mining_excel(data["rows"])
        filename = f"Mining_{date_start}_to_{date_end}.xlsx"
    
    elif module == "quality":
        data     = export_production_quality(date_start, date_end,iup_filter=iup_filter)
        output   = quality_excel(data["rows"])
        filename = f"Quality_{date_start}_to_{date_end}.xlsx"

    elif module == "selling":
        data   = export_selling_quality(date_start, date_end,iup_filter=iup_filter)
        output = selling_excel(data["rows"])
        filename = f"Selling_{date_start}_to_{date_end}.xlsx"

    elif module == "inventory":
        data     = export_inventory_dome(date_end,iup_filter=iup_filter)
        output   = inventory_excel(data["rows"])
        filename = f"Inventory_cut_of_{date_end}.xlsx"

    # nanti tinggal tambahkan quality/selling/inventory case
    else:
        return HttpResponseBadRequest("Invalid module parameter")

    resp = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

def mining_excel(rows):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Mining')

    # Format Header Bold + Background
    fmt_th = workbook.add_format({'bold': True, 'bg_color': '#F3F4F6', 'border': 1})
    fmt_td = workbook.add_format({'border': 1})

    raw_headers = [
        "date_production","shift","vendors","loader","bucket",
        "hauler","loader_class","loading_point","dumping_point",
        "category_mine","time_loading","mine_block","nama_material",
        "ritase","tonnage","direct","remarks"
    ]

    headers = [h.replace("_", " ").title() for h in raw_headers]

    # Tulis header dengan format bold
    ws.write_row(0, 0, headers, fmt_th)

    # Tulis isi tabel
    for i, r in enumerate(rows, start=1):
        ws.write(i, 0, str(r.get("date_production")), fmt_td)
        ws.write(i, 1, r.get("shift"), fmt_td)
        ws.write(i, 2, r.get("vendors"), fmt_td)
        ws.write(i, 3, r.get("loader"), fmt_td)
        ws.write(i, 4, r.get("bucket"), fmt_td)
        ws.write(i, 5, r.get("hauler"), fmt_td)
        ws.write(i, 6, r.get("hauler_class"), fmt_td)
        ws.write(i, 7, r.get("loading_point"), fmt_td)
        ws.write(i, 8, r.get("dumping_point"), fmt_td)
        ws.write(i, 9, r.get("category_mine"), fmt_td)
        ws.write(i, 10, str(r.get("time_loading")), fmt_td)
        ws.write(i, 11, r.get("mine_block"), fmt_td)
        ws.write(i, 12, r.get("nama_material"), fmt_td)
        ws.write_number(i, 13, r.get("ritase") or 0, fmt_td)
        ws.write_number(i, 14, r.get("tonnage") or 0, fmt_td)
        ws.write(i, 15, r.get("direct"), fmt_td)
        ws.write(i, 16, r.get("remarks"), fmt_td)

    # Set lebar kolom biar rapi
    ws.set_column('A:Q', 15)

    workbook.close()
    output.seek(0)
    return output

def quality_excel(rows):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Quality')

    # Format
    fmt_th = workbook.add_format({'bold': True, 'bg_color': '#F3F4F6', 'border': 1})
    fmt_td = workbook.add_format({'border': 1})

    raw_headers = [
        "tgl_production","category","shift","prospect_area","mine_block",
        "from_rl","to_rl","nama_material","ore_class","grade_control",
        "unit_truck","stockpile","pile_id","batch_code","increment",
        "batch_status","ritase","tonnage","pile_status","direct","remarks"
    ]

    headers = [h.replace("_", " ").title() for h in raw_headers]

    # Header row
    ws.write_row(0, 0, headers, fmt_th)

    # Isi data
    for i, r in enumerate(rows, start=1):
        ws.write(i, 0, str(r.get("tgl_production")), fmt_td)
        ws.write(i, 1, r.get("category"), fmt_td)
        ws.write(i, 2, r.get("shift"), fmt_td)
        ws.write(i, 3, r.get("prospect_area"), fmt_td)
        ws.write(i, 4, r.get("mine_block"), fmt_td)
        ws.write(i, 5, r.get("from_rl"), fmt_td)
        ws.write(i, 6, r.get("to_rl"), fmt_td)
        ws.write(i, 7, r.get("nama_material"), fmt_td)
        ws.write(i, 8, r.get("ore_class"), fmt_td)
        ws.write(i, 9, r.get("grade_control"), fmt_td)
        ws.write(i, 10, r.get("unit_truck"), fmt_td)
        ws.write(i, 11, r.get("stockpile"), fmt_td)
        ws.write(i, 12, r.get("pile_id"), fmt_td)
        ws.write(i, 13, r.get("batch_code"), fmt_td)
        ws.write(i, 14, r.get("increment"), fmt_td)
        ws.write(i, 15, r.get("batch_status"), fmt_td)
        ws.write_number(i, 16, r.get("ritase") or 0, fmt_td)
        ws.write_number(i, 17, r.get("tonnage") or 0, fmt_td)
        ws.write(i, 18, r.get("pile_status"), fmt_td)
        ws.write(i, 19, r.get("direct"), fmt_td)
        ws.write(i, 20, r.get("remarks"), fmt_td)

    # Set lebar kolom
    ws.set_column('A:U', 15)  # A sampai U = 21 kolom

    workbook.close()
    output.seek(0)
    return output

def selling_excel(rows):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Selling')

    # Format
    fmt_th = workbook.add_format({'bold': True, 'bg_color': '#F3F4F6', 'border': 1})
    fmt_td = workbook.add_format({'border': 1})
    fmt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

    raw_headers = [
        "date_barge_in","date_barge_out","date_hauling","shift","dome",
        "stockpile","material","barge_code","barge_name","tonnage",
        "batch","code_inc","code_lot","sale_adjust","sale_dome",
        "sample_number","ni","fe","mgo","sio2","mc","sm"
    ]

    headers = [h.replace("_", " ").title() for h in raw_headers]

    # Header row
    ws.write_row(0, 0, headers, fmt_th)

    # Isi data
    for i, r in enumerate(rows, start=1):
        ws.write(i, 0, str(r.get("date_barge_in")), fmt_td)
        ws.write(i, 1, str(r.get("date_barge_out")), fmt_td)
        ws.write(i, 2, str(r.get("date_hauling")), fmt_td)
        ws.write(i, 3, r.get("shift"), fmt_td)
        ws.write(i, 4, r.get("dome"), fmt_td)
        ws.write(i, 5, r.get("stockpile"), fmt_td)
        ws.write(i, 6, r.get("material"), fmt_td)
        ws.write(i, 7, r.get("barge_code"), fmt_td)
        ws.write(i, 8, r.get("barge_name"), fmt_td)
        ws.write_number(i, 9, r.get("tonnage") or 0, fmt_num)
        ws.write(i, 10, r.get("batch"), fmt_td)
        ws.write(i, 11, r.get("code_inc"), fmt_td)
        ws.write(i, 12, r.get("code_lot"), fmt_td)
        ws.write(i, 13, r.get("sale_adjust"), fmt_td)
        ws.write(i, 14, r.get("sale_dome"), fmt_td)
        ws.write(i, 15, r.get("sample_number"), fmt_td)
        ws.write_number(i, 16, float(r.get("ni") or 0), fmt_num)
        ws.write_number(i, 17, float(r.get("fe") or 0), fmt_num)
        ws.write_number(i, 18, float(r.get("mgo") or 0), fmt_num)
        ws.write_number(i, 19, float(r.get("sio2") or 0), fmt_num)
        ws.write_number(i, 20, float(r.get("mc") or 0), fmt_num)
        ws.write_number(i, 21, float(r.get("sm") or 0), fmt_num)

    # Set lebar kolom
    ws.set_column('A:V', 15)  # 22 kolom

    workbook.close()
    output.seek(0)
    return output

def inventory_excel(rows):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    ws = workbook.add_worksheet("Inventory")

    raw_headers = [
        "stockpile", "pile_id", "nama_material",
        "total_ore", "released", "total_selling",
        "balance", "ni", "co", "fe", "mgo", "sio2", "SM"
    ]

    headers  = [h.replace("_", " ").title() for h in raw_headers]
    fmt_th   = workbook.add_format({"bold": True, "bg_color": "#F3F4F6", "border": 1})
    fmt_td   = workbook.add_format({"border": 1})
    fmt_num  = workbook.add_format({"border": 1, "num_format": "#,##0"})
    fmt_dec2 = workbook.add_format({"border": 1, "num_format": "#,##0.00"})

    ws.write_row(0, 0, headers, fmt_th)

    for i, r in enumerate(rows, start=1):
        ws.write(i, 0, r.get("stockpile"), fmt_td)
        ws.write(i, 1, r.get("pile_id"), fmt_td)
        ws.write(i, 2, r.get("nama_material"), fmt_td)
        ws.write_number(i, 3, r.get("total_ore") or 0, fmt_num)
        ws.write_number(i, 4, r.get("released") or 0, fmt_num)
        ws.write_number(i, 5, r.get("total_selling") or 0, fmt_num)
        ws.write_number(i, 6, r.get("balance") or 0, fmt_num)
        ws.write_number(i, 7, float(r.get("ni") or 0), fmt_dec2)
        ws.write_number(i, 8, float(r.get("co") or 0), fmt_dec2)
        ws.write_number(i, 9, float(r.get("fe") or 0), fmt_dec2)
        ws.write_number(i, 10, float(r.get("mgo") or 0), fmt_dec2)
        ws.write_number(i, 11, float(r.get("sio2") or 0), fmt_dec2)
        ws.write_number(i, 12, float(r.get("sm") or 0), fmt_dec2)

    ws.set_column("A:M", 15)
    workbook.close()
    output.seek(0)
    return output


