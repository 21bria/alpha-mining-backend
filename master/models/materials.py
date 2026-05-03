from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class Material(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=250, default=None, null=True, blank=True)
    categories = models.CharField(max_length=25, default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'master_materials'
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["categories"]),
        ]
       