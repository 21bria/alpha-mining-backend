from django.db import models
import uuid

class SamplesDomeView(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_sample    = models.DateField(default=None, null=True, blank=True)
    shift          = models.CharField(max_length=10, default=None, null=True, blank=True)
    type_sample    = models.CharField(max_length=25, default=None, null=True, blank=True)
    is_production  = models.BooleanField(default=True)
    is_geology     = models.BooleanField(default=True)
    sample_method  = models.CharField(max_length=50, default=None, null=True, blank=True)
    material       = models.CharField(max_length=50, default=None, null=True, blank=True)
    sampling_point = models.CharField(max_length=100, default=None, null=True, blank=True)
    batch          = models.CharField(max_length=15, default=None, null=True, blank=True)
    increments     = models.IntegerField(default=None, null=True, blank=True)
    sample_weight  = models.FloatField(default=None, null=True, blank=True)
    sample_id      = models.CharField(max_length=25, default=None, null=True, blank=True)
    sampling_desc  = models.CharField(max_length=50, default=None, null=True, blank=True)
    ni             = models.FloatField(default=None, null=True, blank=True)
    co             = models.FloatField(default=None, null=True, blank=True)
    al2o3          = models.FloatField(default=None, null=True, blank=True)
    cao            = models.FloatField(default=None, null=True, blank=True)
    cr2o3          = models.FloatField(default=None, null=True, blank=True)
    fe2o3          = models.FloatField(default=None, null=True, blank=True)
    fe             = models.FloatField(default=None, null=True, blank=True)
    mgo            = models.FloatField(default=None, null=True, blank=True)
    sio2           = models.FloatField(default=None, null=True, blank=True)
    mc             = models.FloatField(default=None, null=True, blank=True)
    sm             = models.FloatField(default=None, null=True, blank=True)
    user_id        = models.IntegerField(default=None, null=True, blank=True)
    username       = models.CharField(max_length=50,default=None, null=True, blank=True)
    iup_id         = models.IntegerField(default=None, null=True, blank=True)
    iup_code       = models.CharField(max_length=25,default=None, null=True, blank=True)
    iup_name       = models.CharField(max_length=50,default=None, null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed   = False
        db_table  = 'view_geology_samples_dome'
