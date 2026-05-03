from django.db import models
from django.contrib.auth import get_user_model
import uuid
User = get_user_model()


class ImportJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    module = models.CharField(max_length=80)  # contoh: "hr.position"
    file  = models.FileField(upload_to="imports/%Y/%m/%d/")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    status  = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    message = models.TextField(blank=True, null=True)

    total_rows   = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    failed_rows  = models.IntegerField(default=0)
    progress     = models.IntegerField(default=0)  # 0..100

    created_at  = models.DateTimeField(auto_now_add=True)
    started_at  = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "import_job"
        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.module} ({self.status})"


class ImportJobRow(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job         = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="rows")
    row_number  = models.IntegerField()
    status      = models.CharField(max_length=20, choices=[("success","Success"),("failed","Failed")], default="failed")
    payload     = models.JSONField(default=dict, blank=True)
    error       = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "import_job_row"
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["job", "row_number"]),
        ]
