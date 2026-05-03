from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class StockFactories(models.Model):
    factory_stock  = models.CharField(max_length=150, unique=True)
    capacity       = models.FloatField(null=True,blank=True)
    description    = models.CharField(max_length=255, default=None, null=True, blank=True)
    status         = models.IntegerField(default=None, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now_add=True)
    user           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.factory_stock 

    class Meta:
        db_table  = 'master_stock_factories'
        indexes   = [
            models.Index(fields=['factory_stock']),
        ]
