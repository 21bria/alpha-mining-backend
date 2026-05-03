from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class Weather(BaseTenantModel):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date        = models.DateField()
    shift       = models.CharField(max_length=10)
    category    = models.CharField(max_length=20)
    start_time  = models.TimeField(default=None, null=True, blank=True)
    end_time    = models.TimeField(default=None, null=True, blank=True)
    duration    = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=250, default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  = 'mining_weather'
        indexes = [
            models.Index(
                fields=['iup','date', 'shift', 'category', 'start_time', 'end_time'],
                name='idx_weather_check'
            )
        ]

class RainfallPoint(BaseTenantModel):
    name        = models.CharField(max_length=50)
    description = models.CharField(max_length=255, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  = 'mining_rainfall_point'
        indexes = [
            models.Index(
                fields=['iup','name'],
                name='idx_rainfall_type'
            )
        ]

class Rainfall(BaseTenantModel):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date        = models.DateField()
    point       = models.ForeignKey(RainfallPoint, related_name="point_rainfall",on_delete=models.SET_NULL, null=True,blank=True,)
    milimeter   = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=255, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  = 'mining_rainfall'
        indexes = [
            models.Index(
                fields=['iup','date'],
                name='idx_rainfall'
            )
        ]

