from django.http import FileResponse
from rest_framework.views import APIView, Response
from analytics.models import ExportJob


class ExportJobDownloadView(APIView):
    def get(self, request, pk):
        job = ExportJob.objects.get(pk=pk)

        if not job.file:
            return Response({"detail": "File not ready"}, status=404)

        return FileResponse(job.file.open("rb"), as_attachment=True)