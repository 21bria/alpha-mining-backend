from django.contrib.auth.models import Permission
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from core.permissions import IsSystemAdmin

class PermissionTreeView(APIView):
    """
    Return permission tree grouped by app -> model -> permissions
    """
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):

        # hanya app yang ingin ditampilkan di UI
        ALLOWED_APPS = {
            "accounts",
            "core",
            "geology",
            "imports",
            "master",
            "mining",
            "selling",
            "analytics",
        }

        perms = Permission.objects.select_related(
            "content_type"
        ).filter(
            content_type__app_label__in=ALLOWED_APPS
        ).order_by(
            "content_type__app_label",
            "content_type__model",
            "codename"
        )

        tree = {}

        for p in perms:
            app = p.content_type.app_label
            model = p.content_type.model

            tree.setdefault(app, {})
            tree[app].setdefault(model, [])

            tree[app][model].append({
                "id": p.id,
                "code": f"{app}.{p.codename}",
                "name": p.name,
                "codename": p.codename,
            })

        result = []

        for app, models in tree.items():
            result.append({
                "app": app,
                "models": [
                    {
                        "model": model,
                        "perms": perms
                    }
                    for model, perms in models.items()
                ]
            })

        return Response(result)