from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from analytics.models import ExportJob
from .export_job import ExportJobSerializer

class ExportJobDetailView(RetrieveAPIView):
    queryset = ExportJob.objects.all()
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if getattr(user, "is_superuser", False) or getattr(user, "is_system", False):
            return qs

        return qs.filter(created_by=user)