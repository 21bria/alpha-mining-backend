from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class WaybillsTemporary(BaseTenantModel):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample_id      = models.CharField(max_length=25, default=None, null=True, blank=True)
    id_type_sample = models.BigIntegerField(default=None, null=True, blank=True)
    id_method      = models.BigIntegerField(default=None, null=True, blank=True)
    id_material    = models.IntegerField(default=None, null=True, blank=True)
    sampling_area  = models.BigIntegerField(default=None, null=True, blank=True)
    sampling_point = models.BigIntegerField(default=None, null=True, blank=True)
    batch_code     = models.CharField(max_length=10, default=None, null=True, blank=True)
    no_save        = models.CharField(max_length=15, default=None, null=True, blank=True)
    status_input   = models.CharField(max_length=15, default=None, null=True, blank=True)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


    class Meta:
        db_table  = 'geology_waybill_temps'

        indexes = [
            models.Index(fields=["iup", "sample_id"]),
            models.Index(fields=['sample_id'])
        ]