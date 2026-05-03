from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class SellingBarging(BaseTenantModel):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_barge_in       = models.DateField(default=None, null=True, blank=True)
    date_barge_out      = models.DateField(default=None, null=True, blank=True)
    barge_code          = models.IntegerField(default=None, null=True, blank=True)
    barging_load_loc    = models.CharField(max_length=50, default=None, null=True, blank=True)
    barging_unload_loc  = models.CharField(max_length=50, default=None, null=True, blank=True)
    date_hauling        = models.DateField(default=None, null=True, blank=True)
    time_hauling        = models.TimeField(default=None, null=True, blank=True)
    shift               = models.CharField(max_length=10, default=None, null=True, blank=True)
    id_material         = models.IntegerField(default=None, null=True, blank=True)
    id_stockpile        = models.IntegerField(default=None, null=True, blank=True)
    id_pile             = models.IntegerField(default=None, null=True, blank=True)
    unit_code	        = models.CharField(max_length=50,default=None, null=True, blank=True)
    tonnage             = models.FloatField(default=0, null=True, blank=True)
    ritase_group        = models.IntegerField(default=1, null=True, blank=True)
    ton_barge_load      = models.FloatField(default=0, null=True, blank=True)
    ton_barge_unload    = models.FloatField(default=0, null=True, blank=True)
    fill_adjust         = models.FloatField(default=0, null=True, blank=True)
    batch               = models.CharField(max_length=25, default=None, null=True, blank=True)
    id_factory          = models.IntegerField(default=None, null=True, blank=True)
    type_selling        = models.CharField(max_length=50, default=None, null=True, blank=True)
    code_inc            = models.CharField(max_length=25, default=None, null=True, blank=True)
    code_sub            = models.CharField(max_length=150, default=None, null=True, blank=True)
    code_batch_in       = models.CharField(max_length=150, default=None, null=True, blank=True)
    code_batch_ex       = models.CharField(max_length=150, default=None, null=True, blank=True)
    code_batch_pulp     = models.CharField(max_length=150, default=None, null=True, blank=True)
    surv_order          = models.CharField(max_length=100, default=None, null=True, blank=True)
    code_monitoring     = models.CharField(max_length=100, default=None, null=True, blank=True)
    code_lot            = models.CharField(max_length=150, default=None, null=True, blank=True)
    date_barging        = models.DateField(default=None, null=True, blank=True)
    sale_adjust         = models.CharField(max_length=5,default=None, null=True, blank=True)
    sale_dome           = models.CharField(max_length=10,default=None, null=True, blank=True)
    direct              = models.CharField(max_length=10,default=None, null=True, blank=True)
    status_barging      = models.CharField(max_length=50,default='Draft', null=True, blank=True)
    no_input            = models.CharField(max_length=50, default=None, null=True, blank=True)
    description         = models.CharField(max_length=255, default=None, null=True, blank=True)
    user                = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table   = 'selling_barging'

    indexes = [
            models.Index(fields=['iup','date_hauling']),
            models.Index(fields=['code_monitoring']),
            models.Index(fields=['code_batch']),
            models.Index(fields=['code_batch_pulp']),
            models.Index(fields=['sale_adjust']),
            models.Index(fields=['code_lot']),
            models.Index(fields=['status_barging'])
    ]


