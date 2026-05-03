# # views.py
# import logging
# from django.http import JsonResponse
# from django.db import connection
# import pandas as pd
# from datetime import datetime, date, timedelta
# from django.db.utils import DatabaseError
# import calendar
# logger = logging.getLogger(__name__) 


# def safe_division(numerator, denominator):
#     return round(numerator / denominator * 100, 0) if denominator else 0

# def get_data_weather(request):
#     try:
#         filter_type = request.GET.get('filter_type')
#         year = request.GET.get('year')
#         month = request.GET.get('month')
#         week = request.GET.get('week')
#         date_start = request.GET.get('date_start')
#         date_end = request.GET.get('date_end')
#         filter_date= request.GET.get('filter_date')

#         filter_sql = "WHERE 1=1"
#         params = []

#         # Tentukan kondisi filter SQL dan parameter
#         if filter_type =='daily' and filter_date:
#             filter_sql += " AND date = %s"
#             params = [filter_date]

#         elif filter_type =='range' and date_start and date_end:  # Range
#             filter_sql += " AND date BETWEEN %s AND %s"
#             params = [date_start, date_end]

#         elif filter_type =='weekly' and year and month and week:  # Weekly
#             try:
#                 # Deteksi jika 'week' dalam format ISO (contoh: '2025-03')
#                 if '-' in str(week):
#                     year_str, week_str = str(week).split('-')
#                     year = int(year_str)
#                     week = int(week_str)

#                     # Hitung awal minggu (ISO): Senin minggu ke-X
#                     start_date = datetime.strptime(f'{year}-W{week:02}-1', "%G-W%V-%u")
#                     end_date = start_date + timedelta(days=6)
#                     print("Start:", start_date, "End:", end_date)

#                 else:
#                     # Parsing normal year, month, week
#                     year  = int(year)
#                     month = int(month)
#                     week  = int(week)

#                     if not (1 <= month <= 12):
#                         return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
#                     if not (1 <= week <= 5):
#                         return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

#                     first_day = datetime(year, month, 1)
#                     start_date = first_day + timedelta(days=(week - 1) * 7)
#                     end_date = start_date + timedelta(days=6)

#                     # Koreksi akhir bulan
#                     if end_date.month != month:
#                         next_month = datetime(year, month, 28) + timedelta(days=4)
#                         end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

#             except Exception as e:
#                 return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)
            
#             # Tambahkan WHERE clause filter mingguan
#             filter_sql += " AND date BETWEEN %s AND %s"
#             params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]

#         elif filter_type =='monthly' and year and month:  # Monthly
#             filter_sql += " AND EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s" \
#                 if db_vendor == 'postgresql' else " AND YEAR(date) = %s AND MONTH(date) = %s"
#             params = [year, month]

#         elif filter_type =='yearly' and year:  # Yearly
#             filter_sql += " AND EXTRACT(YEAR FROM date) = %s" \
#                 if db_vendor == 'postgresql' else " AND YEAR(date) = %s"
#             params = [year]

#         elif filter_type =='all':  # All
#             pass  # Tidak ada tambahan filter

#         else:
#             return JsonResponse({'error': 'Invalid or incomplete filter parameters'}, status=400)

#         # Query berdasarkan vendor
#         if db_vendor == 'postgresql':
#             query = f"""
#                 SELECT
#                     COALESCE(SUM(CASE WHEN category = 'Rain' THEN duration ELSE 0 END), 0)::numeric AS Rainy,
#                     COALESCE(SUM(CASE WHEN category = 'Slippery' THEN duration ELSE 0 END), 0)::numeric AS Slippery
#                 FROM mine_weather
#                 {filter_sql}
#             """
#         else:
#             raise ValueError(f"Unsupported database vendor: {db_vendor}")

#         with connection.cursor() as cursor:
#             cursor.execute(query, params)
#             row = cursor.fetchone()

#         rainy    = float(row[0] or 0)
#         slippery = float(row[1] or 0)

#         return JsonResponse({
#             'rainy': rainy,
#             'slippery': slippery
#         })


#     except Exception as e:
#         logger.exception("Unexpected error occurred.")
#         return JsonResponse({'error': str(e)}, status=500)

# def get_data_rainfall(request):
#     try:
#         filter_type = request.GET.get('filter_type')
#         year = request.GET.get('year')
#         month = request.GET.get('month')
#         week = request.GET.get('week')
#         date_start = request.GET.get('date_start')
#         date_end = request.GET.get('date_end')
#         filter_date= request.GET.get('filter_date')

#         filter_sql = "WHERE 1=1"
#         params = []

#         # Tentukan kondisi filter SQL dan parameter
#         if filter_type =='daily' and filter_date:
#             filter_sql += " AND date = %s"
#             params = [filter_date]

#         elif filter_type =='range' and date_start and date_end:  # Range
#             filter_sql += " AND date BETWEEN %s AND %s"
#             params = [date_start, date_end]

#         elif filter_type =='weekly' and year and month and week:  # Weekly
#             try:
#                 # Deteksi jika 'week' dalam format ISO (contoh: '2025-03')
#                 if '-' in str(week):
#                     year_str, week_str = str(week).split('-')
#                     year = int(year_str)
#                     week = int(week_str)

#                     # Hitung awal minggu (ISO): Senin minggu ke-X
#                     start_date = datetime.strptime(f'{year}-W{week:02}-1', "%G-W%V-%u")
#                     end_date = start_date + timedelta(days=6)
#                     print("Start:", start_date, "End:", end_date)

#                 else:
#                     # Parsing normal year, month, week
#                     year  = int(year)
#                     month = int(month)
#                     week  = int(week)

#                     if not (1 <= month <= 12):
#                         return JsonResponse({"error": "Bulan tidak valid (1–12)"}, status=400)
#                     if not (1 <= week <= 5):
#                         return JsonResponse({"error": "Minggu tidak valid (1–5)"}, status=400)

#                     first_day = datetime(year, month, 1)
#                     start_date = first_day + timedelta(days=(week - 1) * 7)
#                     end_date = start_date + timedelta(days=6)

#                     # Koreksi akhir bulan
#                     if end_date.month != month:
#                         next_month = datetime(year, month, 28) + timedelta(days=4)
#                         end_date = datetime(next_month.year, next_month.month, 1) - timedelta(days=1)

#             except Exception as e:
#                 return JsonResponse({"error": f"Format tahun/bulan/minggu tidak valid: {str(e)}"}, status=400)
            
#             # Tambahkan WHERE clause filter mingguan
#             filter_sql += " AND date BETWEEN %s AND %s"
#             params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]

#         elif filter_type =='monthly' and year and month:  # Monthly
#             filter_sql += " AND EXTRACT(YEAR FROM date) = %s AND EXTRACT(MONTH FROM date) = %s" \
#                 if db_vendor == 'postgresql' else " AND YEAR(date) = %s AND MONTH(date) = %s"
#             params = [year, month]

#         elif filter_type =='yearly' and year:  # Yearly
#             filter_sql += " AND EXTRACT(YEAR FROM date) = %s" \
#                 if db_vendor == 'postgresql' else " AND YEAR(date) = %s"
#             params = [year]

#         elif filter_type =='all':  # All
#             pass  # Tidak ada tambahan filter

#         else:
#             return JsonResponse({'error': 'Invalid or incomplete filter parameters'}, status=400)

#         # Query berdasarkan vendor
#         if db_vendor == 'postgresql':
#             query = f"""
#                 SELECT
#                     COALESCE(SUM(milimeter), 0)::numeric AS milimeter
#                 FROM mine_rainfall
#                 {filter_sql}
#             """
#         else:
#             raise ValueError(f"Unsupported database vendor: {db_vendor}")

#         with connection.cursor() as cursor:
#             cursor.execute(query, params)
#             row = cursor.fetchone()

#         milimeter = float(row[0] or 0)

#         return JsonResponse({
#             'milimeter': milimeter,
#         })


#     except Exception as e:
#         logger.exception("Unexpected error occurred.")
#         return JsonResponse({'error': str(e)}, status=500)
