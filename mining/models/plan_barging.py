from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class planBarging(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    date_plan = models.DateField(null=True, blank=True)

    category = models.CharField(max_length=25, null=True, blank=True)

    vendor_code = models.CharField(max_length=50, null=True, blank=True)

    lim = models.FloatField(default=0, null=True, blank=True)
    sap = models.FloatField(default=0, null=True, blank=True)

    task_id = models.CharField(max_length=255, null=True, blank=True)

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        db_table = "mining_plan_barging"
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["date_plan"]),
            models.Index(fields=["vendor_code"]),
            models.Index(fields=["category"]),
        ]