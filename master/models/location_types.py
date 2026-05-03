from django.db import models
from django.contrib.gis.db import models as geomodels
from django.contrib.auth import get_user_model

User = get_user_model()
# LOCATION_TYPE = (
#         ("CAMP", "Camp"),
#         ("OFFICE", "Office"),
#         ("JETTY", "Jetty"),
#         ("PORT", "Port"),
#         ("FUEL", "Fuel Station"),
#         ("WB", "Weighbridge"),
#         ("CRUSHER", "Crusher"),
#         ("OTHER", "Other"),
#     )

class LocationType(models.Model):
    code = models.CharField(max_length=50, unique=True)  # SED_POND
    name = models.CharField(max_length=100)              # Sediment Pond

    GEOM_KIND = (
        ("POINT", "Point"),
        ("LINE", "Line"),
        ("POLYGON", "Polygon"),
    )
    geom_kind = models.CharField(max_length=10, choices=GEOM_KIND)

    icon   = models.CharField(max_length=50, null=True, blank=True)  # untuk map
    color  = models.CharField(max_length=20, null=True, blank=True)
    active = models.BooleanField(default=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = "master_location_types"
        indexes = [
            models.Index(fields=["geom_kind"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name