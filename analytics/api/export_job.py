from rest_framework import serializers
from analytics.models import ExportJob


class ExportJobSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "module",
            "status",
            "progress",
            "error",
            "file",
            "file_url",
            "created_at",
            "finished_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        return None