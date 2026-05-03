from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class mineAdditionFactor(BaseTenantModel):
    type_unit       = models.CharField(max_length=100,default=None,null=True,blank=True)
    material        = models.CharField(max_length=25,default=None, null=True, blank=True)
    density_bcm     = models.FloatField(default=None, null=True, blank=True)
    density_lcm     = models.FloatField(default=None, null=True, blank=True)
    bucket_capacity = models.FloatField(default=None, null=True, blank=True)
    validation      = models.CharField(max_length=100, default=None, null=True, blank=True)
    description     = models.CharField(max_length=255, default=None, null=True, blank=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
       return f"{self.type_unit}{self.material}"

    class Meta:
        db_table  = 'mining_addition_factor'



class volumeTruckFactorAdjustment(BaseTenantModel):
    date_start      = models.DateField(default=None,null=True,blank=True)
    date_end        = models.DateField(default=None,null=True,blank=True)
    category        = models.CharField(max_length=25,default=None,null=True,blank=True)
    vendors         = models.CharField(max_length=50,default=None,null=True,blank=True)
    sources         = models.BigIntegerField(default=None,null=True,blank=True)
    loading_point   = models.BigIntegerField(default=None,null=True,blank=True)
    type_truck      = models.CharField(max_length=50,default=None,null=True,blank=True)
    material        = models.CharField(max_length=25,default=None,null=True,blank=True)
    bucket_original = models.IntegerField(default=None,null=True,blank=True)
    bcm_original    = models.FloatField(default=None,null=True,blank=True)
    ton_original    = models.FloatField(default=None,null=True,blank=True)
    bucket_updated  = models.FloatField(default=None,null=True,blank=True)
    bcm_updated     = models.FloatField(default=None,null=True,blank=True)
    ton_updated     = models.FloatField(default=None,null=True,blank=True)
    status          = models.CharField(max_length=50,blank=True,default=None,null=True)
    description     = models.CharField(max_length=255,blank=True,default=None,null=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table  ='mining_volume_factors_adjustment'
        unique_together = ('iup',
        'date_start', 'date_end',
        'category', 'vendors',
        'loading_point', 'type_truck',
        'material', 'bucket_updated'
    )


class mineVolumeAdjustment(models.Model):
    date_start      = models.DateField(default=None,null=True,blank=True)
    date_end        = models.DateField(default=None,null=True,blank=True)
    category        = models.CharField(max_length=25,default=None,null=True,blank=True)
    vendors         = models.CharField(max_length=50,default=None,null=True,blank=True)
    sources_area    = models.CharField(max_length=250,default=None,null=True,blank=True)
    loading_point   = models.CharField(max_length=250,default=None,null=True,blank=True)
    type_truck      = models.CharField(max_length=50,default=None,null=True,blank=True)
    material        = models.CharField(max_length=25,default=None,null=True,blank=True)
    bucket_original = models.FloatField(default=None,null=True,blank=True)
    bcm_original    = models.FloatField(default=None,null=True,blank=True)
    ton_original    = models.FloatField(default=None,null=True,blank=True)
    bucket_updated  = models.FloatField(default=None,null=True,blank=True)
    bcm_updated     = models.FloatField(default=None,null=True,blank=True)
    ton_updated     = models.FloatField(default=None,null=True,blank=True)
    status          = models.CharField(max_length=50,blank=True,default=None,null=True)
    description     = models.CharField(max_length=255,blank=True,default=None,null=True)

    class Meta:
        managed   = False
        db_table  = 'view_mining_volume_adjustment'

