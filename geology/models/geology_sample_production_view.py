from django.db import models
import uuid

class SamplesView(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_sample    = models.DateField(default=None, null=True, blank=True)
    week           = models.IntegerField(default=None, null=True, blank=True)
    month          = models.IntegerField(default=None, null=True, blank=True)
    year           = models.IntegerField(default=None, null=True, blank=True)
    shift          = models.CharField(max_length=10, default=None, null=True, blank=True)
    type_sample    = models.CharField(max_length=25, default=None, null=True, blank=True)
    is_production = models.BooleanField(default=True)
    is_geology    = models.BooleanField(default=True)
    is_selling     = models.BooleanField(default=False)
    is_monitoring  = models.BooleanField(default=False)
    sample_method  = models.CharField(max_length=50, default=None, null=True, blank=True)
    material       = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_area  = models.CharField(max_length=200, default=None, null=True, blank=True)
    sampling_point = models.CharField(max_length=100, default=None, null=True, blank=True)
    area_sampling  = models.CharField(max_length=50, default=None, null=True, blank=True)
    factory_stock  = models.CharField(max_length=150, default=None, null=True, blank=True)
    point_sampling = models.CharField(max_length=50, default=None, null=True, blank=True)
    selling_code   = models.CharField(max_length=50, default=None, null=True, blank=True)
    batch          = models.CharField(max_length=15, default=None, null=True, blank=True)
    increments     = models.IntegerField(default=None, null=True, blank=True)
    size           = models.CharField(max_length=15, default=None, null=True, blank=True)
    sample_weight  = models.FloatField(default=None, null=True, blank=True)
    sample_id      = models.CharField(max_length=25, default=None, null=True, blank=True)
    remark         = models.CharField(max_length=255, default=None, null=True, blank=True)
    primer_raw     = models.FloatField(default=None, null=True, blank=True)
    duplicate_raw  = models.FloatField(default=None, null=True, blank=True)
    sampling_desc  = models.CharField(max_length=50, default=None, null=True, blank=True)
    code_batch     = models.CharField(max_length=150, default=None, null=True, blank=True)
    no_sample      = models.CharField(max_length=15, default=None, null=True, blank=True)
    user_id        = models.IntegerField(default=None, null=True, blank=True)
    username       = models.CharField(max_length=50,default=None, null=True, blank=True)
    iup_id         = models.IntegerField(default=None, null=True, blank=True)
    iup_code       = models.CharField(max_length=25,default=None, null=True, blank=True)
    iup_name       = models.CharField(max_length=50,default=None, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_samples'


class samplesNoOrders(models.Model):
    tgl_sample     = models.DateField(default=None, null=True, blank=True)
    minggu         = models.IntegerField(default=None, null=True, blank=True)
    bulan          = models.IntegerField(default=None, null=True, blank=True)
    tahun          = models.IntegerField(default=None, null=True, blank=True)
    shift          = models.CharField(max_length=10, default=None, null=True, blank=True)
    type_sample    = models.CharField(max_length=25, default=None, null=True, blank=True)
    sample_method  = models.CharField(max_length=50, default=None, null=True, blank=True)
    nama_material  = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_area  = models.CharField(max_length=200, default=None, null=True, blank=True)
    sampling_point = models.CharField(max_length=100, default=None, null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50, default=None, null=True, blank=True)
    batch_code     = models.CharField(max_length=15, default=None, null=True, blank=True)
    increments     = models.IntegerField(default=None, null=True, blank=True)
    size           = models.CharField(max_length=15, default=None, null=True, blank=True)
    sample_weight  = models.FloatField(default=None, null=True, blank=True)
    sample_number  = models.CharField(max_length=25, default=None, null=True, blank=True)
    remark         = models.CharField(max_length=255, default=None, null=True, blank=True)
    primer_raw     = models.FloatField(default=None, null=True, blank=True)
    duplicate_raw  = models.FloatField(default=None, null=True, blank=True)
    to_its         = models.TimeField(default=None, null=True, blank=True)
    waybill_number = models.CharField(max_length=25, default=None, null=True, blank=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_samples_not_orders'

class samplesNaPds(models.Model):
    tgl_sample     = models.DateField(default=None, null=True, blank=True)
    minggu         = models.IntegerField(default=None, null=True, blank=True)
    bulan          = models.IntegerField(default=None, null=True, blank=True)
    tahun          = models.IntegerField(default=None, null=True, blank=True)
    shift          = models.CharField(max_length=10, default=None, null=True, blank=True)
    type_sample    = models.CharField(max_length=25, default=None, null=True, blank=True)
    units          = models.CharField(max_length=25, default=None, null=True, blank=True)
    nama_material  = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_area  = models.CharField(max_length=200, default=None, null=True, blank=True)
    sampling_point = models.CharField(max_length=100, default=None, null=True, blank=True)
    batch_code     = models.CharField(max_length=15, default=None, null=True, blank=True)
    increments     = models.IntegerField(default=None, null=True, blank=True)
    size           = models.CharField(max_length=15, default=None, null=True, blank=True)
    sample_weight  = models.FloatField(default=None, null=True, blank=True)
    sample_number  = models.CharField(max_length=25, default=None, null=True, blank=True)
    remark         = models.CharField(max_length=255, default=None, null=True, blank=True)
    primer_raw     = models.FloatField(default=None, null=True, blank=True)
    duplicate_raw  = models.FloatField(default=None, null=True, blank=True)
    to_its         = models.TimeField(default=None, null=True, blank=True)
    kode_batch     = models.CharField(max_length=15, default=None, null=True, blank=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_sample_pds_na'      