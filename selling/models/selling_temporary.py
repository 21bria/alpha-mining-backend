from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class SellingBargingTemporary(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code_lot = models.IntegerField(default=None, null=True, blank=True)
    barge_code = models.IntegerField(default=None, null=True, blank=True)
    date_hauling = models.DateField(default=None, null=True, blank=True)
    time_hauling = models.TimeField(default=None, null=True, blank=True)
    shift = models.CharField(max_length=10, default=None, null=True, blank=True)
    id_material = models.IntegerField(default=None, null=True, blank=True)
    id_stockpile = models.IntegerField(default=None, null=True, blank=True)
    id_pile = models.IntegerField(default=None, null=True, blank=True)
    unit_code = models.CharField(max_length=50, default=None, null=True, blank=True)
    tonnage = models.FloatField(default=0, null=True, blank=True)
    type_selling = models.CharField(max_length=50, default=None, null=True, blank=True)
    code_inc = models.CharField(max_length=25, default=None, null=True, blank=True)
    code_sub = models.CharField(max_length=25, default=None, null=True, blank=True)
    code_sub_auto = models.CharField(max_length=25, default=None, null=True, blank=True)
    id_user = models.IntegerField(default=None, null=True, blank=True)
    sale_adjust = models.CharField(max_length=5, default=None, null=True, blank=True)
    no_urut = models.IntegerField(default=0, null=True, blank=True)
    status = models.IntegerField(default=0, null=True, blank=True)
    description = models.CharField(max_length=255, default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "sellings_barging_temporary"
        indexes = [
            models.Index(fields=["code_inc"]),
            models.Index(fields=["sale_adjust"]),
            models.Index(fields=["code_lot"]),
            models.Index(fields=["code_sub"]),
            models.Index(fields=["unit_code"]),
            models.Index(fields=["type_selling"]),
        ]