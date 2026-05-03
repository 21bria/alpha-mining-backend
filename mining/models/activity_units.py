from django.db import models
import uuid
from core.models import BaseTenantModel
from master.models import MineUnits,MiningActivityCategories,MiningActivity,MiningActivityLocation
from django.contrib.auth import get_user_model

User = get_user_model()
class HmUnit(BaseTenantModel):
    SHIFT_CHOICES = [
        ('Day', 'Day'),
        ('Night', 'Night'),
    ]
    id  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(
        MineUnits,
        on_delete=models.PROTECT,
        related_name='hm_units'
    )
    date = models.DateField()
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    hm_start = models.DecimalField(max_digits=15, decimal_places=2)
    hm_end   = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(
        max_length=20,
        default='DRAFT',
        choices=[
            ('DRAFT', 'Draft'),
            ('SUBMITTED', 'Submitted'),
            ('APPROVED', 'Approved'),
        ]
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'mining_hm_unit'
        unique_together = ('iup','unit', 'date', 'shift')
        indexes = [
            models.Index(fields=['iup']), 
            models.Index(fields=['unit']), 
            models.Index(fields=['date']),
            models.Index(fields=['shift']), 
        ]

    def __str__(self):
        return f'{self.unit.unit_code} | {self.date} | {self.shift}'
   

class HmUnitDetail(BaseTenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hm_unit = models.ForeignKey(
        HmUnit,
        on_delete=models.CASCADE,
        related_name='details'
    )
    start_time = models.TimeField()
    end_time   = models.TimeField()
    duration_min = models.PositiveIntegerField()
    status   = models.ForeignKey(MiningActivityCategories, on_delete=models.PROTECT)
    activity = models.ForeignKey(MiningActivity, on_delete=models.PROTECT)
    location = models.ForeignKey(MiningActivityLocation, on_delete=models.PROTECT)
    category = models.CharField(
        max_length=20,
        blank=True, 
        null=True,
        choices=[
            ('Mining', 'Mining'),
            ('Project', 'Project')
        ]
    )
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'mining_hm_unit_detail'
        indexes = [
            models.Index(fields=['iup']),
            models.Index(fields=['hm_unit']),
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['category'])
        ]

    