from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from imports.models import ImportJob, ImportJobRow
from .serializers import ImportJobSerializer, ImportJobRowSerializer
from .pagination import StandardResultsSetPagination

class ImportJobListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ImportJobSerializer

    def get_queryset(self):
        qs = ImportJob.objects.all().order_by("-created_at")

        module = self.request.query_params.get("module")
        if module:
            qs = qs.filter(module=module)

        # if not self.request.user.is_superuser:
        #     qs = qs.filter(created_by=self.request.user)

        return qs


class ImportJobDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ImportJobSerializer

    def get_queryset(self):
        qs = ImportJob.objects.all()
        # if not self.request.user.is_superuser:
        #     qs = qs.filter(created_by=self.request.user)
        return qs



class ImportJobRowListView(generics.ListAPIView):
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]
    serializer_class = ImportJobRowSerializer
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        job_id = self.kwargs["pk"]  # ganti dari job_id ke pk

        qs = ImportJobRow.objects.filter(job_id=job_id).order_by("row_number")

        # if not self.request.user.is_superuser:
        #   qs = qs.filter(job__created_by=self.request.user)

        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)

        return qs