from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class planProductions(BaseTenantModel):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_plan  = models.DateField(default=None, null=True, blank=True)
    category   = models.CharField(max_length=25, default=None, null=True, blank=True)
    sources    = models.CharField(max_length=50, default=None, null=True, blank=True)
    vendors    = models.CharField(max_length=15, default=None, null=True, blank=True)
    topsoil    = models.FloatField(default=0, null=True, blank=True)
    ob         = models.FloatField(default=0, null=True, blank=True)
    lglo       = models.FloatField(default=0, null=True, blank=True)
    mglo       = models.FloatField(default=0, null=True, blank=True)
    hglo       = models.FloatField(default=0, null=True, blank=True)
    waste      = models.FloatField(default=0, null=True, blank=True)
    mws        = models.FloatField(default=0, null=True, blank=True)
    lgso       = models.FloatField(default=0, null=True, blank=True)
    uglo       = models.FloatField(default=0, null=True, blank=True)
    mgso       = models.FloatField(default=0, null=True, blank=True)
    hgso       = models.FloatField(default=0, null=True, blank=True)
    lim        = models.FloatField(default=0, null=True, blank=True)
    sap        = models.FloatField(default=0, null=True, blank=True)
    quarry     = models.FloatField(default=0, null=True, blank=True)
    ballast    = models.FloatField(default=0, null=True, blank=True)
    biomass    = models.FloatField(default=0, null=True, blank=True)
    ref_plan   = models.CharField(max_length=150, default=None, null=True, blank=True)
    task_id    = models.CharField(max_length=255, default=None, null=True, blank=True)
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  = 'mining_plan_productions'

    
    indexes = [
        models.Index(fields=['iup']),
        models.Index(fields=['date_plan']),
        models.Index(fields=['ref_plan']),
    ]

