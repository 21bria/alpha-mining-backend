from rest_framework import serializers
from imports.models import ImportJob, ImportJobRow

class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = [
            "id",
            "module",
            "status",
            "message",
            "total_rows",
            "success_rows",
            "failed_rows",
            "progress",
            "created_at",
            "started_at",
            "finished_at",
            "created_by",
        ]
        read_only_fields = ["created_by"]

    def create(self, validated_data):
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            validated_data["created_by"] = request.user

        return super().create(validated_data)
    
class ImportJobRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJobRow
        fields = ["id","row_number","status","payload","error"]
