from django.db import models
from core.models import BaseTenantModel
from master.models import SellingSurveyor
from django.contrib.auth import get_user_model

User = get_user_model()
class SellingOfficial(BaseTenantModel):
    surveyor       = models.ForeignKey(SellingSurveyor, on_delete=models.SET_NULL, null=True, blank=True)
    type_selling   = models.CharField(max_length=50, default=None, null=True, blank=True)
    tonnage        = models.FloatField(default=None, null=True, blank=True)
    id_factory     = models.IntegerField(default=None, null=True, blank=True)
    so_number      = models.CharField(max_length=150,default=None, null=True, blank=True)
    product_code   = models.CharField(max_length=150,default=None, null=True, blank=True)
    barge_code     = models.CharField(max_length=150,default=None, null=True, blank=True)
    ni             = models.FloatField(default=None, null=True, blank=True)
    co	           = models.FloatField(default=None, null=True, blank=True)
    al2o3	       = models.FloatField(default=None, null=True, blank=True)
    cao	           = models.FloatField(default=None, null=True, blank=True)
    cr2o3	       = models.FloatField(default=None, null=True, blank=True)
    fe	           = models.FloatField(default=None, null=True, blank=True)
    mgo	           = models.FloatField(default=None, null=True, blank=True)
    sio2	       = models.FloatField(default=None, null=True, blank=True)
    mno	           = models.FloatField(default=None, null=True, blank=True)
    mc	           = models.FloatField(default=None, null=True, blank=True)
    # sm	             = models.FloatField(default=None, null=True, blank=True)
    start_date     = models.DateField(default=None, null=True, blank=True)
    end_date       = models.DateField(default=None, null=True, blank=True)
    description    = models.CharField(max_length=250, default=None, null=True, blank=True)
    re_assay       = models.IntegerField(default=0, null=True, blank=True)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table   = 'selling_official'

    indexes = [
        models.Index(fields=['iup']),
        models.Index(fields=['type_selling']),
        models.Index(fields=['product_code']),
        models.Index(fields=['barge_code'])
    ]
