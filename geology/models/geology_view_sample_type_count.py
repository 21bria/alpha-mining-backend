from django.db import models

class SampleTypeCount(models.Model):
    tgl_sample      = models.DateField(default=None, null=True, blank=True)
    sample_number   = models.CharField(max_length=25, default=None, null=True, blank=True)
    type_sample     = models.CharField(max_length=25, default=None, null=True, blank=True)
    sample_method   = models.CharField(max_length=25, default=None, null=True, blank=True)
    delivery        = models.DateTimeField(default=None, null=True, blank=True)
    waybill_number  = models.CharField(max_length=25, default=None, null=True, blank=True)
    mral_order      = models.CharField(max_length=5, default=None, null=True, blank=True)
    roa_order       = models.CharField(max_length=5, default=None, null=True, blank=True)
    date_production = models.DateTimeField(default=None, null=True, blank=True)
    release_mral    = models.DateTimeField(default=None, null=True, blank=True)
    release_roa     = models.DateTimeField(default=None, null=True, blank=True)
    iup_id          = models.IntegerField(default=None, null=True, blank=True)
    iup_code        = models.CharField(max_length=50, default=None, null=True, blank=True)
    iup_name        = models.CharField(max_length=100, default=None, null=True, blank=True)
    

    class Meta:
        managed   = False
        db_table  = 'view_sample_type_count'
       

