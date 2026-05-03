from django.db import models
from core.models import BaseTenantModel
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()
class FuelStockDaily(BaseTenantModel):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date     = models.DateField()
    incoming = models.FloatField(default=0)
    description = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  = 'mining_stock_fuel'
        indexes   = [
            models.Index(fields=['iup','date']),
        ]
        