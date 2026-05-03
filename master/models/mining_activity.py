from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()

class MiningActivityCategories(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    category = models.CharField(
        max_length=20,
        choices=[
            ('Working', 'Working'),
            ('STANDBY', 'Standby'),
            ('BREAKDOWN', 'Breakdown'),
            # ('MAINTENANCE', 'Maintenance'),
            # ('SUPPORT', 'Support'),
            # ('OFF', 'Off / Non Shift'),
        ]
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'master_activity_categories'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            ]

class MiningActivity(models.Model):
    status = models.ForeignKey(
        MiningActivityCategories,
        on_delete=models.PROTECT,
        related_name='activities'
    )
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    class Meta:
        db_table  = 'master_activity'
        

class MiningActivityLocation(BaseTenantModel):
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)   
    description = models.CharField(max_length=250,null=True, blank=True)   
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table  = 'master_activity_locations'
        
