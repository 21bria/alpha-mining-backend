from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class SellingSurveyor(models.Model):
    code_surveyor = models.CharField(max_length=50, default=None, null=True, blank=True)
    name_surveyor = models.CharField(max_length=150, default=None, null=True, blank=True)
    description   = models.CharField(max_length=150, default=None, null=True, blank=True)
    status        = models.IntegerField(default=None, null=True, blank=True)
    start_date    = models.DateField(default=None, null=True, blank=True)
    end_date      = models.DateField(default=None, null=True, blank=True)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table   = 'master_surveyor'

        indexes = [
            models.Index(fields=['code_surveyor']), 
            models.Index(fields=['name_surveyor'])
        ]
