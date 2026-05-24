from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class AIReport(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    task_id = models.CharField(max_length=255, unique=True)
    report_type = models.CharField(max_length=100, default="production_review")
    params = models.JSONField(default=dict)
    result = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, default="pending")
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)