from django.db import models
from django.contrib.auth import get_user_model
from master.models import SourceMinesDome
User = get_user_model()

class DomeAdjustment(models.Model):
    dome = models.ForeignKey(SourceMinesDome,on_delete=models.CASCADE,related_name="adjustments")
    current_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    target_total  = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    scale_factor  = models.DecimalField(max_digits=10, decimal_places=6, default=0)

    description = models.TextField(null=True, blank=True)
    user = models.ForeignKey( User, on_delete=models.SET_NULL,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geology_dome_adjustment"
        indexes = [
            models.Index(fields=["created_at"]),
        ]