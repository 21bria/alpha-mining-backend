from django.db import models
from django.db.models import Q
from core.models import BaseTenantModel
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

class AssayMral(BaseTenantModel):
    code_source_field = "sample_id"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release_date = models.DateField(default=None, null=True, blank=True)
    release_time = models.TimeField(default=None, null=True, blank=True)
    release_mral = models.DateTimeField(null=True, blank=True)
    job_number   = models.CharField(max_length=25, null=True, blank=True)
    sample_id    = models.CharField(max_length=15, null=True, blank=True)

    ni    = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    co    = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    fe2o3 = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    fe    = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    mgo   = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    sio2  = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)

    no_input = models.BigIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "lab_assay_mral"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "sample_id"],
                condition=Q(is_deleted=False),
                name="unique_assay_mral_by_iup_active"
            )
        ]
        indexes = [
            models.Index(fields=["iup","sample_id"]),
            models.Index(fields=["release_mral"]),
            models.Index(fields=["sample_id"]),
        ]

   
