from django.db import models
from django.contrib.gis.db import models as geomodels
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class BargeUnits(models.Model):
    barge_code  = models.CharField(max_length=25, unique=True)
    barge_name  = models.CharField(max_length=50, default=None, null=True, blank=True)
    capacity    = models.FloatField(default=None, null=True, blank=True)
    description = models.CharField(max_length=255, default=None, null=True, blank=True)
    active      = models.IntegerField(default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.barge_code

    class Meta:
        db_table  = 'master_barge'
        indexes   = [
            models.Index(fields=['barge_code']),
            models.Index(fields=['barge_name'])
        ]
        

class BargePort(BaseTenantModel):
    code_source_field = "port_name"

    port_name   = models.CharField(max_length=150)
    port_type   = models.CharField(max_length=50, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    active      = models.IntegerField(null=True, blank=True)
    # untuk pin di map
    location     = geomodels.PointField(srid=4326, null=True, blank=True)
    latitude     = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    longitude    = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    geometry     = geomodels.MultiPolygonField(srid=4326, null=True, blank=True)

    extra_properties = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "master_port"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "port_name"],
                name="uq_port_name_per_iup"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["port_name"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.port_name} ({self.iup.iup_code if self.iup else '-'})"