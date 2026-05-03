from django.db import models
from django.db.models import Q
from core.models import BaseTenantModel
import uuid
from django.contrib.auth import get_user_model
User = get_user_model()

class AssayRoa(BaseTenantModel):
    code_source_field = "sample_id"

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    release_date = models.DateField(default=None, null=True, blank=True)
    release_time = models.TimeField(default=None, null=True, blank=True)
    release_roa  = models.DateTimeField(default=None, null=True, blank=True)
    job_number   = models.CharField(max_length=25, default=None, null=True, blank=True)
    sample_id    = models.CharField(max_length=20, default=None, null=True, blank=True)
    ni           = models.FloatField(default=None, null=True, blank=True)
    co           = models.FloatField(default=None, null=True, blank=True)
    al2o3        = models.FloatField(default=None, null=True, blank=True)
    cao          = models.FloatField(default=None, null=True, blank=True)
    cr2o3        = models.FloatField(default=None, null=True, blank=True)
    fe2o3        = models.FloatField(default=None, null=True, blank=True)
    fe           = models.FloatField(default=None, null=True, blank=True)
    k2o          = models.FloatField(default=None, null=True, blank=True)
    mgo          = models.FloatField(default=None, null=True, blank=True)
    mno          = models.FloatField(default=None, null=True, blank=True)
    na2o         = models.FloatField(default=None, null=True, blank=True)
    p2o5         = models.FloatField(default=None, null=True, blank=True)
    p            = models.FloatField(default=None, null=True, blank=True)
    sio2         = models.FloatField(default=None, null=True, blank=True)
    tio2         = models.FloatField(default=None, null=True, blank=True)
    s            = models.FloatField(default=None, null=True, blank=True)
    cu           = models.FloatField(default=None, null=True, blank=True)
    zn           = models.FloatField(default=None, null=True, blank=True)
    ci           = models.FloatField(default=None, null=True, blank=True)
    so3          = models.FloatField(default=None, null=True, blank=True)
    loi          = models.FloatField(default=None, null=True, blank=True)
    total        = models.CharField(max_length=25, default=None, null=True, blank=True)
    wt_wet       = models.FloatField(default=None, null=True, blank=True)
    wt_dry       = models.FloatField(default=None, null=True, blank=True)
    mc           = models.FloatField(default=None, null=True, blank=True)
    p75um        = models.FloatField(default=None, null=True, blank=True)
    _5mm         = models.FloatField(default=None, null=True, blank=True)
    problem      = models.CharField(max_length=255, default=None, null=True, blank=True)
    no_input     = models.BigIntegerField(default=None, null=True, blank=True)
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "lab_assay_roa"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "sample_id"],
                condition=Q(is_deleted=False),
                name="unique_assay_roa_by_iup_active"
            )
        ]
        indexes = [
            models.Index(fields=["release_roa"]),
            models.Index(fields=["sample_id"]),
        ]

   
