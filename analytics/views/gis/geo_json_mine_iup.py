
from django.http import JsonResponse
from analytics.services.gis.iup_geojson_service import get_iup_with_sources_geojson

def api_iup_with_sources(request, iup_id):
    data = get_iup_with_sources_geojson(iup_id)

    if not data:
        return JsonResponse({"error": "Data tidak ditemukan"}, status=404)

    if "error" in data:
        return JsonResponse({"error": data["error"]}, status=data.get("status", 400))

    return JsonResponse(data, safe=False)