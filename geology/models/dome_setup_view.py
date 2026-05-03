from django.db import models

class domeStatusCloseView(models.Model):
    # id             = models.BigIntegerField(default=None,null=True,blank=True)
    id_dome        = models.BigIntegerField(default=None,null=True,blank=True)
    sampling_point = models.CharField(max_length=50,default=None,null=True,blank=True)
    sampling_area  = models.CharField(max_length=50,default=None,null=True,blank=True)
    tonnage_dome   = models.FloatField(default=None,null=True,blank=True)
    status_dome    = models.CharField(max_length=15,default=None,null=True,blank=True)
    description    = models.TextField(default=None,null=True,blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_dome_close'


class domeStatusFinishView(models.Model):
    # id             = models.BigIntegerField(default=None,null=True,blank=True)
    id_dome        = models.BigIntegerField(default=None,null=True,blank=True)
    sampling_point = models.CharField(max_length=50,default=None,null=True,blank=True)
    sampling_area  = models.CharField(max_length=50,default=None,null=True,blank=True)
    tonnage_dome   = models.FloatField(default=None,null=True,blank=True)
    status_dome    = models.CharField(max_length=15,default=None,null=True,blank=True)
    description    = models.TextField(default=None,null=True,blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_dome_finish'
