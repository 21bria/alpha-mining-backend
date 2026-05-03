import uuid
from django.db import models

class listWaybills(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tgl_deliver   = models.DateField(default=None, null=True, blank=True)
    delivery_time = models.TimeField(default=None, null=True, blank=True)
    waybill_number = models.CharField(max_length=25, default=None, null=True, blank=True)
    qty           = models.IntegerField(default=None, null=True, blank=True)
    sample_id     = models.CharField(max_length=25, default=None, null=True, blank=True)
    sample_status = models.CharField(max_length=15, default=None, null=True, blank=True)
    mral_order    = models.CharField(max_length=5, default=None, null=True, blank=True)
    roa_order     = models.CharField(max_length=5, default=None, null=True, blank=True)
    remarks       = models.CharField(max_length=255, default=None, null=True, blank=True)
    iup_id        = models.IntegerField(default=None, null=True, blank=True)
    iup_code      = models.CharField(max_length=50, default=None, null=True, blank=True)
    iup_name      = models.CharField(max_length=100, default=None, null=True, blank=True)
    user_id       = models.IntegerField(default=None, null=True, blank=True)
    username      = models.CharField(max_length=50, default=None, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view_geology_waybills'


class listTemporary(models.Model):
    sample_id      = models.CharField(max_length=25, default=None, null=True, blank=True)
    type_sample    = models.CharField(max_length=25, default=None, null=True, blank=True)
    sample_method  = models.CharField(max_length=25, default=None, null=True, blank=True)
    nama_material  = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_area  = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_point = models.CharField(max_length=50, default=None, null=True, blank=True)
    batch_code     = models.CharField(max_length=10, default=None, null=True, blank=True)
    no_save        = models.CharField(max_length=15, default=None, null=True, blank=True)
    status_input   = models.CharField(max_length=15, default=None, null=True, blank=True)
    id_user        = models.IntegerField(default=None, null=True, blank=True)

    class Meta:
        managed   = False
        db_table  = 'view_waybills_temporary'
   

