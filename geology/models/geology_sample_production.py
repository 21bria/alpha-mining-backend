from django.db import models
import uuid
from core.models import BaseTenantModel
from django.contrib.auth import get_user_model

User = get_user_model()
class SampleProductions(BaseTenantModel):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tgl_sample      = models.DateField(default=None, null=True, blank=True)
    shift           = models.CharField(max_length=10, default=None, null=True, blank=True)
    id_type_sample  = models.IntegerField(default=None, null=True, blank=True)
    id_method       = models.IntegerField(default=None, null=True, blank=True)
    id_material     = models.IntegerField(default=None, null=True, blank=True)
    sampling_area   = models.BigIntegerField(default=None, null=True, blank=True)
    sampling_point  = models.BigIntegerField(default=None, null=True, blank=True)
    from_rl         = models.CharField(max_length=15,default=None, null=True, blank=True)
    to_rl           = models.CharField(max_length=15,default=None, null=True, blank=True)
    batch_code      = models.CharField(max_length=15,default=None, null=True, blank=True)
    increments      = models.IntegerField(default=None, null=True, blank=True)
    fraction        = models.CharField(max_length=15,default=None, null=True, blank=True)
    size            = models.CharField(max_length=15,default=None, null=True, blank=True)
    sample_weight   = models.FloatField(default=None, null=True, blank=True)
    sample_number   = models.CharField(max_length=25,default=None, null=True, blank=True)
    remark          = models.CharField(max_length=255,default=None, null=True, blank=True)
    primer_raw      = models.FloatField(default=None, null=True, blank=True)
    duplicate_raw   = models.FloatField(default=None, null=True, blank=True)
    to_its          = models.TimeField(default=None, null=True, blank=True)
    unit_truck      = models.CharField(max_length=15,default=None, null=True, blank=True)
    kode_batch      = models.CharField(max_length=150,default=None, null=True, blank=True)
    selling_pulp    = models.CharField(max_length=150,default=None, null=True, blank=True)
    sale_monitoring = models.CharField(max_length=150,default=None, null=True, blank=True)
    sampling_deskripsi = models.CharField(max_length=50,default=None, null=True, blank=True)
    type            = models.CharField(max_length=25,default=None, null=True, blank=True)
    usage_status    = models.CharField(max_length=5,default=None, null=True, blank=True)
    pile_original   = models.BigIntegerField(default=None, null=True, blank=True)
    no_sample       = models.CharField(max_length=15,default=None, null=True, blank=True)
    sample_dup      = models.CharField(max_length=15,default=None, null=True, blank=True)
    discharge_area  = models.BigIntegerField(default=None, null=True, blank=True)
    product_code    = models.BigIntegerField(default=None, null=True, blank=True)
    gc_expect       = models.CharField(max_length=10,default=None, null=True, blank=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
 
    class Meta:
        db_table  = 'geology_samples_productions'
        constraints = [
            models.UniqueConstraint(
                fields=["iup", "sample_number"],
                name="uniq_sample_iup_sample_number"
            )
        ]

        indexes = [
            models.Index(fields=["iup", "sample_number"]),
            models.Index(fields=['sample_number']),   # Index for sample_number
            models.Index(fields=['selling_pulp']),
            models.Index(fields=['sale_monitoring']),
            models.Index(fields=['kode_batch']),
            models.Index(fields=['sampling_deskripsi']),
            models.Index(fields=['sample_dup']),
            models.Index(fields=['gc_expect'])
        ]
        
    def save(self, *args, **kwargs):
        original = self.sampling_deskripsi

        # Default None
        self.sample_dup = None

        if original and isinstance(original, str):
            desc = original.strip()

            # Jika DUP_, isi sample_dup versi bersih
            if desc.startswith("DUP_"):
                self.sample_dup = desc[4:]  # hilangkan DUP_

        super().save(*args, **kwargs)

    @classmethod
    def get_samples(cls, sample_from, sample_to):
        return cls.objects.filter(sample_number__gte=sample_from, sample_number__lte=sample_to)
