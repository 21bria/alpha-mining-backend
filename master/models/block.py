from django.db import models
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class Block(BaseTenantModel):
    code_source_field = "name"
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250, null=True, blank=True)
    status = models.IntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = "master_blocks"
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "name"],
                name="unique_block_per_iup"
            )
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["name"]),
        ]