import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AIChatSession(models.Model):

    id = models.UUIDField( primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="ai_chat_sessions" )
    title = models.CharField( max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_chat_sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title or str(self.id)


class AIReport(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    id = models.UUIDField( primary_key=True,default=uuid.uuid4,editable=False)

    session = models.ForeignKey(AIChatSession,on_delete=models.CASCADE,related_name="reports",null=True,blank=True )

    task_id = models.CharField(max_length=255,unique=True)

    report_type = models.CharField(max_length=100)

    intent = models.CharField(max_length=100,blank=True,null=True)

    params = models.JSONField(default=dict,blank=True)

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default="PENDING")

    result = models.TextField(blank=True,null=True)

    error = models.TextField(blank=True,null=True)

    created_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="ai_reports")

    created_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(null=True,blank=True)

    class Meta:
        db_table = "ai_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.report_type} - {self.status}"


class AIChatMessage(models.Model):

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    session = models.ForeignKey(
        AIChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    report = models.ForeignKey(
        AIReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    message = models.TextField()

    intent = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "ai_chat_messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role} - {self.created_at}"