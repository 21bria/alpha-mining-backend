from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class MineGeologies(BaseTenantModel):
    code        = models.CharField(max_length=15)
    name        = models.CharField(max_length=100,default=None, null=True, blank=True)
    status      = models.IntegerField(default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
  
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        db_table  = 'master_geology'
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "code"],
                name="unique_gc_per_iup"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["name"]),
            models.Index(fields=["code"]),
        ]

