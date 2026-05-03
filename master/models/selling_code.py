from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class SellingCode(BaseTenantModel):
    code          = models.CharField(max_length=50)
    description   = models.CharField(max_length=250, default=None, null=True, blank=True)
    type          = models.CharField(max_length=10, default=None, null=True, blank=True)
    active        = models.IntegerField(default=None, null=True, blank=True)
    truck_factors = models.FloatField(default=None, null=True, blank=True)
    sublot_close  = models.CharField(max_length=10, default=None, null=True, blank=True)
    group_close   = models.IntegerField(default=None, null=True, blank=True)
    ritase_max    = models.IntegerField(default=None, null=True, blank=True)
    tonnage       = models.FloatField(default=None, null=True, blank=True)
    ni            = models.FloatField(default=None, null=True, blank=True)
    fe            = models.FloatField(default=None, null=True, blank=True)
    al2o3         = models.FloatField(default=None, null=True, blank=True)
    co            = models.FloatField(default=None, null=True, blank=True)
    mgo           = models.FloatField(default=None, null=True, blank=True)
    sio2          = models.FloatField(default=None, null=True, blank=True)
    cao           = models.FloatField(default=None, null=True, blank=True)
    mno           = models.FloatField(default=None, null=True, blank=True)
    cr2o3         = models.FloatField(default=None, null=True, blank=True)
    sm            = models.FloatField(default=None, null=True, blank=True)
    mc            = models.FloatField(default=None, null=True, blank=True)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table  = 'master_selling_code'
        indexes = [
            models.Index(fields=['iup','code','type']),
        ]




