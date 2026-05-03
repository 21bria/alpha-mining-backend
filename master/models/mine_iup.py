from django.db import models
from django.contrib.gis.db import models as geomodels
from django.contrib.auth import get_user_model

User = get_user_model()
class MineIUP(models.Model):
    iup_code     = models.CharField(max_length=50, unique=True)
    iup_name     = models.CharField(max_length=100)
    geometry     = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)
    center_lat   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    center_lng   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    default_zoom = models.PositiveSmallIntegerField(default=14)
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)  

    def __str__(self):
        return f"{self.iup_code} - {self.iup_name}"

    class Meta:
        db_table = "master_mine_iup"
        indexes = [
            models.Index(fields=["iup_name"]),
        ]
