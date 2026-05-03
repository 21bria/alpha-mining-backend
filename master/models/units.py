from django.db import models
from .mine_iup import MineIUP
from django.contrib.auth import get_user_model

User = get_user_model()
class MineUnits(models.Model):
    unit_vendor  = models.CharField(max_length=60, unique=True)
    # unit_vendor   = models.CharField(max_length=60, null=True, blank=True)
    unit_code     = models.CharField(max_length=25)
    unit_model    = models.CharField(max_length=50, default=None, null=True, blank=True)
    unit_class    = models.CharField(max_length=50, default=None, null=True, blank=True)
    brand         = models.CharField(max_length=150, default=None, null=True, blank=True)
    id_category   = models.IntegerField(default=None, null=True, blank=True)
    id_vendor     = models.IntegerField(default=None, null=True, blank=True)
    supports      = models.CharField(max_length=50, default=None, null=True, blank=True)
    status        = models.IntegerField(default=None, null=True, blank=True)
    description   = models.CharField(max_length=255, default=None, null=True, blank=True)
    commisioning_date = models.DateField(default=None, null=True, blank=True)
    on_hire     = models.DateField(default=None, null=True, blank=True)
    off_hire    = models.DateField(default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.unit_vendor

    class Meta:
        db_table = "master_units"

        # constraints = [
        #     models.UniqueConstraint(
        #         fields=["unit_code", "id_vendor"],
        #         name="uq_unit_code_vendor"
        #     )
        # ]

        indexes = [
            models.Index(fields=["unit_vendor"]),
            models.Index(fields=["unit_code"]),
            models.Index(fields=["id_vendor"]),
        ]
        
class UnitAssignment(models.Model):
    unit = models.ForeignKey(MineUnits, on_delete=models.PROTECT, related_name="assignments")
    iup  = models.ForeignKey(MineIUP, on_delete=models.PROTECT, related_name="unit_assignments")

    start_date = models.DateField()
    end_date   = models.DateField(null=True, blank=True)  # null = masih aktif
    active     = models.BooleanField(default=True)

    class Meta:
        db_table = "master_unit_assignments"
        constraints = [
            models.UniqueConstraint(fields=["unit"], condition=models.Q(active=True), name="uq_one_active_assignment_per_unit")
        ]
        indexes = [
            models.Index(fields=["iup"]),
            models.Index(fields=["unit"]),
        ]

class unitsCategories(models.Model):
    category    = models.CharField(max_length=50, default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'master_units_categories'
        indexes = [
            models.Index(fields=['category']),
            ]

class unitsView(models.Model):
    unit_code   = models.CharField(max_length=25, default=None, null=True, blank=True)
    unit_model  = models.CharField(max_length=50, default=None, null=True, blank=True)
    unit_class  = models.CharField(max_length=50, default=None, null=True, blank=True)
    brand       = models.CharField(max_length=150, default=None, null=True, blank=True)
    supports    = models.CharField(max_length=25, default=None, null=True, blank=True)
    category    = models.CharField(max_length=50, default=None, null=True, blank=True)
    vendor_name = models.CharField(max_length=25, default=None, null=True, blank=True)
    
    status      = models.IntegerField(default=None, null=True, blank=True)
    
    class Meta:
        managed     = False
        db_table    = 'view_master_units'

