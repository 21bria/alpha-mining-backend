from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model
User = get_user_model()
class OreTruckFactorAdjust(BaseTenantModel):
    unit_truck   = models.CharField(max_length=25)  # jangan null kalau dipakai unique
    sources      = models.IntegerField(null=True, blank=True)
    material     = models.IntegerField(null=True, blank=True)
    date_start   = models.DateField()
    date_end     = models.DateField()
    ton          = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    reference_tf = models.CharField(max_length=150, null=True, blank=True)
    status       = models.CharField(max_length=50, default="ACTIVE")
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


    class Meta:
        db_table = "geology_ore_truck_factors_adjust"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "unit_truck", "sources", "material", "date_start", "date_end"],
                name="uniq_ore_tf_adjust_period"
            )
        ]
        indexes = [
            models.Index(fields=["iup", "date_start", "date_end"]),
            models.Index(fields=["unit_truck"]),
        ]