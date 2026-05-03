from django.db import models
from .mine_iup import MineIUP
from django.contrib.auth import get_user_model

User = get_user_model()

class MineUnitsExportView(models.Model):
    id = models.IntegerField(primary_key=True)
    unit_vendor = models.CharField(max_length=60, null=True, blank=True)
    unit_code = models.CharField(max_length=25, null=True, blank=True)
    unit_model = models.CharField(max_length=50, null=True, blank=True)
    unit_class = models.CharField(max_length=50, null=True, blank=True)
    brand = models.CharField(max_length=150, null=True, blank=True)
    id_category = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=50, null=True, blank=True)
    id_vendor = models.IntegerField(null=True, blank=True)
    supports = models.CharField(max_length=50, null=True, blank=True)
    status = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    commisioning_date = models.DateField(null=True, blank=True)
    on_hire = models.DateField(null=True, blank=True)
    off_hire = models.DateField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    username = models.CharField(max_length=150, null=True, blank=True)
    iup_id = models.IntegerField(null=True, blank=True)
    iup_code = models.CharField(max_length=25, null=True, blank=True)
    iup_name = models.CharField(max_length=100, null=True, blank=True)
    assignment_start_date = models.DateField(null=True, blank=True)
    assignment_end_date = models.DateField(null=True, blank=True)
    assignment_active = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "view_master_units"