from django.contrib.gis.db.models.functions import AsGeoJSON
import json
from django.db.models import Sum
from collections import defaultdict
from django.db import connection
from master.models import MineIUP,SourceMines
from mining.models import mineProductions


def get_source_production_summary(iup_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                t1.sources_area AS source_id,
                m.name as nama_material,
                SUM(t1.tonnage) AS tonnage,
                SUM(SUM(t1.tonnage)) OVER (PARTITION BY t1.sources_area) AS total_source      
            FROM mining_productions t1
            JOIN master_mine_sources s ON s.id = t1.sources_area
            JOIN master_mine_iup mi ON mi.id = s.iup_id 
            JOIN master_materials m ON m.id = t1.id_material
            WHERE s.iup_id = %s
            GROUP BY t1.sources_area, m.name;  
        """, [iup_id])

        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

def get_iup_with_sources_geojson(iup_id):
    iup = MineIUP.objects.filter(id=iup_id).first()

    if not iup:
        return {"error": "IUP tidak ditemukan", "status": 404}

    if not iup.geometry:
        return {"error": "Geometry IUP masih kosong", "status": 400}

    iup_geojson = json.loads(
        MineIUP.objects
        .filter(id=iup_id)
        .annotate(geojson=AsGeoJSON('geometry'))
        .values_list('geojson', flat=True)[0]
    )

    production_rows = get_source_production_summary(iup_id)

    production_map = {}
    for row in production_rows:
        sid = row['source_id']
        production_map.setdefault(sid, {
            "total": 0,
            "materials": []
        })

        production_map[sid]["materials"].append({
            "material": row['nama_material'],
            "tonnage": float(row['tonnage'] or 0)
        })

        production_map[sid]["total"] = float(row['total_source'] or 0)

    sources = (
        SourceMines.objects
        .filter(
            geometry__within=iup.geometry,
            geometry__isnull=False
        )
        .annotate(geojson=AsGeoJSON('geometry'))
    )

    source_features = []

    for s in sources:
        extra = s.extra_properties or {}

        source_features.append({
            "type": "Feature",
            "geometry": json.loads(s.geojson),
            "properties": {
                "id": s.id,
                "sources_area": s.sources_area,
                "pit": extra.get("pit"),
                "luas_ha": extra.get("Luas"),
                # "status": s.status,
                "productions": production_map.get(s.id, {
                    "total": 0,
                    "materials": []
                })
            }
        })

    return {
        "iup": {
            "type": "Feature",
            "geometry": iup_geojson,
            "properties": {
                "id": iup.id,
                "name": iup.iup_name,
            }
        },
        "sources": {
            "type": "FeatureCollection",
            "features": source_features
        },
        
    }