from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class Vendors(models.Model):
    vendor_name = models.CharField(max_length=50, unique=True)
    code        = models.CharField(max_length=15, default=None, null=True, blank=True)
    status      = models.IntegerField(default=None, null=True, blank=True)
    description = models.CharField(max_length=255, default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    class Meta:
        db_table  = 'master_vendors'
        indexes   = [
            models.Index(fields=['vendor_name']),
            models.Index(fields=['code'])
        ]


