import uuid
from django.db import models

class sampleDuplikatRoa(models.Model):
    id = models.BigIntegerField(primary_key=True)
    sample_number = models.CharField(max_length=25, null=True, blank=True)
    sample_method = models.CharField(max_length=25, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50, null=True, blank=True)
    material = models.CharField(max_length=50, null=True, blank=True)

    ni = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    sample_original = models.CharField(max_length=15, null=True, blank=True)

    ni_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    ni_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    ni_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ni_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ni_error = models.TextField(null=True, blank=True)

    co_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_error = models.TextField(null=True, blank=True)

    fe_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_error = models.TextField(null=True, blank=True)

    mgo_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_error = models.TextField(null=True, blank=True)

    sio2_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_error = models.TextField(null=True, blank=True)

    iup_id = models.BigIntegerField(null=True, blank=True)
    iup_code = models.CharField(max_length=50, null=True, blank=True)
    iup_name = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view_sample_duplicated_roa'

class sampleDuplikatMral(models.Model):
    id = models.BigIntegerField(primary_key=True)
    sample_number = models.CharField(max_length=25, null=True, blank=True)
    sample_method = models.CharField(max_length=25, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50, null=True, blank=True)
    material = models.CharField(max_length=50, null=True, blank=True)

    ni = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2 = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    sample_original = models.CharField(max_length=15, null=True, blank=True)

    ni_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_ori = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    ni_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)

    ni_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ni_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    ni_error = models.TextField(null=True, blank=True)

    co_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    co_error = models.TextField(null=True, blank=True)

    fe_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    fe_error = models.TextField(null=True, blank=True)

    mgo_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    mgo_error = models.TextField(null=True, blank=True)

    sio2_rel_diff = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_rel_abs = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    sio2_error = models.TextField(null=True, blank=True)

    iup_id = models.BigIntegerField(null=True, blank=True)
    iup_code = models.CharField(max_length=50, null=True, blank=True)
    iup_name = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'view_sample_duplicated_mral'