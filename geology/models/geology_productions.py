from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class OreProductions(BaseTenantModel):
    id                  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tgl_production      = models.DateField(default=None, null=True, blank=True)
    shift               = models.CharField(max_length=10, default=None, null=True, blank=True)
    id_prospect_area    = models.IntegerField(default=None, null=True, blank=True)
    id_block            = models.BigIntegerField(default=None, null=True, blank=True)
    from_rl             = models.CharField(max_length=15, default=None, null=True, blank=True)
    to_rl               = models.CharField(max_length=15, default=None, null=True, blank=True)
    id_material         = models.IntegerField(default=None, null=True, blank=True)
    grade_expect        = models.FloatField(default=None, null=True, blank=True)
    grade_control       = models.CharField(max_length=50, default=None, null=True, blank=True)
    unit_truck          = models.CharField(max_length=15, default=None, null=True, blank=True)
    id_stockpile        = models.IntegerField(default=None, null=True, blank=True)
    id_pile             = models.IntegerField(default=None, null=True, blank=True)
    batch_code          = models.CharField(max_length=15, default=None, null=True, blank=True)
    increment           = models.IntegerField(default=None, null=True, blank=True)
    batch_status        = models.CharField(max_length=25, default=None, null=True, blank=True)
    ritase              = models.IntegerField(default=None, null=True, blank=True)
    # tonnage             = models.FloatField(default=None, null=True, blank=True)
    tonnage             = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True, default=0)
    pile_status         = models.CharField(max_length=25, default=None, null=True, blank=True)
    kode_batch          = models.CharField(max_length=150, default=None, null=True, blank=True)
    pile_original       = models.IntegerField(default=None, null=True, blank=True)
    stockpile_ori       = models.IntegerField(default=None, null=True, blank=True)
    truck_factor        = models.CharField(max_length=15, default=None, null=True, blank=True)
    ore_class           = models.CharField(max_length=15, default=None, null=True, blank=True)
    batch_status_set    = models.CharField(max_length=15, default=None, null=True, blank=True)
    dome_compositing    = models.CharField(max_length=100, default=None, null=True, blank=True)
    stock_compositing   = models.CharField(max_length=15, default=None, null=True, blank=True)
    status_dome         = models.CharField(max_length=25, default=None, null=True, blank=True)
    sale_adjust         = models.CharField(max_length=5, default=None, null=True, blank=True)
    remarks             = models.TextField(default=None, null=True, blank=True)
    category            = models.CharField(max_length=10, default=None, null=True, blank=True)
    direct              = models.CharField(max_length=15, default='No', null=True, blank=True)
    no_production       = models.CharField(max_length=15,default=None, null=True, blank=True)
    user                = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

   
    class Meta:
        db_table = "geology_ore_productions"
        indexes = [
            models.Index(fields=["iup", "tgl_production"]),
            models.Index(fields=["kode_batch"]),
            models.Index(fields=["ore_class"]),
        ]

