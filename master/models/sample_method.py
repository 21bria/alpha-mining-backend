from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

class SampleType(models.Model):
    type_sample = models.CharField(max_length=25, unique=True)
    description = models.CharField(max_length=250, default=None, null=True, blank=True)
    status      = models.IntegerField(default=None, null=True, blank=True)
    category    = models.CharField(max_length=50, default=None, null=True, blank=True)
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.type_sample

    class Meta:
        db_table = 'master_sample_type'
    
    indexes = [
        models.Index(fields=['type_sample']),
        models.Index(fields=['category'])
    ]


class SampleMethod(models.Model):
    sample_type = models.ForeignKey(
        SampleType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="id_type"
    )
    sample_method = models.CharField(max_length=25)
    description = models.CharField(max_length=250, default=None, null=True, blank=True)
    status = models.IntegerField(default=None, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.sample_type:
            return f"{self.sample_type.type_sample} - {self.sample_method}"
        return self.sample_method

    class Meta:
        db_table = "master_sample_methods"
        constraints = [
            models.UniqueConstraint(
                fields=["sample_type", "sample_method"],
                name="uq_sample_method_per_type",
            )
        ]
        indexes = [
            models.Index(fields=["sample_type"]),
            models.Index(fields=["sample_method"]),
        ]