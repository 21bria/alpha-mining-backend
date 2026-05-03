from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
class MineCategory(models.Model):
    category = models.CharField( max_length=25)
    remarks = models.CharField(max_length=250,blank=True,null=True )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(blank=True,null=True)
    updated_at = models.DateTimeField( blank=True, null=True )

    class Meta:
        db_table     = "mining_category"
        verbose_name = "Mining Category"
        verbose_name_plural = "Mining Categories"

    def __str__(self):
        return self.category
