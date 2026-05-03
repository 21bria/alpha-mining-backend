from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Waybills(BaseTenantModel):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tgl_deliver   = models.DateField(default=None, null=True, blank=True)
    delivery_time = models.TimeField(default=None, null=True, blank=True)
    waybill_number= models.CharField(max_length=25, default=None, null=True, blank=True)
    qty           = models.IntegerField(default=None, null=True, blank=True)
    sample_id     = models.CharField(max_length=25, default=None, null=True, blank=True)
    mral_order    = models.CharField(max_length=5, default=None, null=True, blank=True)
    roa_order     = models.CharField(max_length=5, default=None, null=True, blank=True)
    remarks       = models.CharField(max_length=255, default=None, null=True, blank=True)
    delivery      = models.DateTimeField(default=None, null=True, blank=True)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)


    class Meta:
        db_table  = 'geology_waybills'
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "sample_id"],
                name="uniq_waybill_iup_sample_id"
            )
        ]
        indexes = [
            models.Index(fields=["iup", "waybill_number"]),
            models.Index(fields=["iup", "sample_id"]),
            models.Index(fields=['sample_id'])
        ]

    @classmethod
    def is_duplicate_data(cls, sample_id):
        return cls.objects.filter(sample_id=sample_id).exists()