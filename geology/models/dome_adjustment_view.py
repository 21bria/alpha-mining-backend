from django.db import models

class domeAdjustmentView(models.Model):
    id             = models.BigIntegerField(primary_key=True,default=None)
    dome           = models.CharField(max_length=255,default=None,null=True,blank=True)
    current_total  = models.FloatField(default=0,null=True,blank=True)
    target_total   = models.FloatField(default=0,null=True,blank=True)
    scale_factor   = models.FloatField(default=0,null=True,blank=True)
    description    = models.TextField(default=None,null=True,blank=True)
    cek_duplicated = models.CharField(max_length=255,default=None,null=True,blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_dome_adjustment'


