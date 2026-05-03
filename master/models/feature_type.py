from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class FeatureType(models.Model):
    GEOM_KIND = (
        ("POINT", "Point/Marker"),
        ("LINE", "Line (Road/Drainage)"),
        ("POLYGON", "Polygon (Area/Pond)"),
    )

    code = models.CharField(max_length=50, unique=True)   # e.g. SED_POND, HAUL_ROAD
    name = models.CharField(max_length=100)               # e.g. Sediment Pond
    geom_kind = models.CharField(max_length=10, choices=GEOM_KIND)

    # opsional untuk frontend (Leaflet/Map)
    icon = models.CharField(max_length=50, null=True, blank=True)  # e.g. "pond", "road"
    color = models.CharField(max_length=20, null=True, blank=True) # e.g. "#00A"
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = "master_feature_types"
        indexes = [models.Index(fields=["geom_kind"]), models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.code} - {self.name}"