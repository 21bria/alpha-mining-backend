from django.db import models
from django.contrib.auth import get_user_model
from master.models import SellingCode

User = get_user_model()
class SellingBargingAdjustment(models.Model):
    code_lot        = models.ForeignKey(SellingCode,on_delete=models.CASCADE,related_name="adjustments")
    date_arrival    = models.DateField(default=None,null=True,blank=True)
    date_departure  = models.DateField(default=None,null=True,blank=True)
    jetty_departure = models.CharField(max_length=25,default=None,null=True,blank=True)
    ritase_ori      = models.IntegerField(default=None,null=True,blank=True)
    tonnage_ori     = models.FloatField(default=None,null=True,blank=True)
    tonnage_adjust  = models.FloatField(default=None,null=True,blank=True)
    status          = models.CharField(max_length=15,default=None,null=True,blank=True)
    description     = models.TextField(null=True, blank=True)
    user            = models.ForeignKey( User, on_delete=models.SET_NULL,null=True,blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "selling_barging_adjustment"
        indexes = [
            models.Index(fields=["created_at"]),
        ]
