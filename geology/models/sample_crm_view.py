import uuid
from django.db import models

class sampleCrmRoaView(models.Model):
    id = models.BigIntegerField(primary_key=True)
    oreas_name = models.CharField(max_length=25, default=None, null=True, blank=True)

    ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    al2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)

    sample_number = models.CharField(max_length=25, default=None, null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50, default=None, null=True, blank=True)
    sample_id = models.CharField(max_length=20, default=None, null=True, blank=True)
    release_date = models.DateField(default=None, null=True, blank=True)

    roa_ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    roa_al2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)

    diff_ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_al2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)

    iup_id = models.BigIntegerField(default=None, null=True, blank=True)
    iup_code = models.CharField(max_length=50, default=None, null=True, blank=True)
    iup_name = models.CharField(max_length=100, default=None, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view_sample_crm_diff_roa'

class sampleCrmMralView(models.Model):
    id = models.BigIntegerField(primary_key=True)
    oreas_name = models.CharField(max_length=25, default=None, null=True, blank=True)

    ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)

    sample_number = models.CharField(max_length=25, default=None, null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50, default=None, null=True, blank=True)
    sample_id = models.CharField(max_length=20, default=None, null=True, blank=True)
    release_date = models.DateField(default=None, null=True, blank=True)

    mral_ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mral_co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mral_fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mral_fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mral_mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    mral_sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)


    diff_ni = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_co = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_fe2o3 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_fe = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_mgo = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
    diff_sio2 = models.DecimalField(max_digits=18, decimal_places=4, default=None, null=True, blank=True)
 
    iup_id = models.BigIntegerField(default=None, null=True, blank=True)
    iup_code = models.CharField(max_length=50, default=None, null=True, blank=True)
    iup_name = models.CharField(max_length=100, default=None, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view_sample_crm_diff_mral'