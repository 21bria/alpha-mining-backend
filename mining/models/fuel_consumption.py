from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class FuelConsumption(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    shift = models.CharField(max_length=10, null=True, blank=True)
    unit = models.CharField(max_length=25, null=True, blank=True)
    hours_metre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    drivers = models.CharField(max_length=50, null=True, blank=True)
    charging_time = models.TimeField()
    volume = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    storage  = models.CharField(max_length=150, null=True, blank=True)
    operator = models.CharField(max_length=150, null=True, blank=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "mining_fuel_consumption"

        constraints = [
            models.UniqueConstraint(
                fields=["iup", "date", "shift", "unit"],
                name="unique_fuel_unit_by_iup"
            )
        ]

        indexes = [
            models.Index(fields=["iup", "date"]),
            models.Index(fields=["unit"]),
        ]

class FuelConsumptionView(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date           = models.DateField()
    shift          = models.CharField(max_length=10, default=None, null=True, blank=True)
    unit           = models.CharField(max_length=25, default=None, null=True, blank=True)
    code           = models.CharField(max_length=50, default=None, null=True, blank=True)
    hours_metre    = models.CharField(max_length=25, default=None, null=True, blank=True)
    drivers        = models.CharField(max_length=50, default=None, null=True, blank=True)
    charging_time  = models.TimeField()
    volume         = models.FloatField(default=None, null=True, blank=True)
    category       = models.CharField(max_length=50, default=None, null=True, blank=True)
    storage        = models.CharField(max_length=150, default=None, null=True, blank=True)
    operator       = models.CharField(max_length=150, default=None, null=True, blank=True)
    user_id        = models.IntegerField(default=None, null=True, blank=True)
    username       = models.CharField(max_length=50,default=None, null=True, blank=True)
    iup_id         = models.IntegerField(default=None, null=True, blank=True)
    iup_code       = models.CharField(max_length=25,default=None, null=True, blank=True)
    iup_name       = models.CharField(max_length=50,default=None, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
 

    class Meta:
        managed   = False
        db_table  = 'view_mining_fuel_consumption'

