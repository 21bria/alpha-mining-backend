from django.db import models
from django.contrib.auth import get_user_model
from master.models import SourceMinesDome
User = get_user_model()

class domeStatusClose(models.Model):
    dome          = models.ForeignKey(SourceMinesDome,on_delete=models.CASCADE,related_name="close_dome")
    tonnage_dome  = models.FloatField(default=None,null=True,blank=True)
    status_dome   = models.CharField(max_length=15,default=None,null=True,blank=True)
    description   = models.TextField(default=None,null=True,blank=True)
    cek_duplicated= models.CharField(max_length=255,default=None,null=True,blank=True)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  ='geology_dome_close'


class domeStatusFinish(models.Model):
    dome           = models.ForeignKey(SourceMinesDome,on_delete=models.CASCADE,related_name="finish_dome")
    tonnage_dome   = models.FloatField(default=None,null=True,blank=True)
    status_dome    = models.CharField(max_length=15,default=None,null=True,blank=True)
    description    = models.TextField(default=None,null=True,blank=True)
    cek_duplicated = models.CharField(max_length=255,default=None,null=True,blank=True)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  ='geology_dome_finish'
