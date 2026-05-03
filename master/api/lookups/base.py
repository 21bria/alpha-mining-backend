from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from master.api.pagination import StandardResultsSetPagination


class BaseLookupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Generic lookup endpoint with pagination.

    Query params:
      - q: optional search string
      - value_key: which field to use for "value" (default: default_value_key)
      - label_key: which field to use for "label" (default: default_label_key)

    Subclasses must set:
      - queryset (or override get_queryset)
      - search_fields (optional)
      - allowed_value_keys, allowed_label_keys
      - default_value_key, default_label_key
    """

    pagination_class = StandardResultsSetPagination

    # override di subclass
    search_fields = []  # e.g. ["code__icontains", "description__icontains"]
    allowed_value_keys = {"id"}
    allowed_label_keys = {"id"}
    default_value_key = "id"
    default_label_key = "id"

    def apply_search(self, qs, q: str):
        if not q or not self.search_fields:
            return qs
        from django.db.models import Q

        cond = Q()
        for f in self.search_fields:
            cond |= Q(**{f: q})
        return qs.filter(cond)

    def list(self, request, *args, **kwargs):
        value_key = request.query_params.get("value_key", self.default_value_key)
        label_key = request.query_params.get("label_key", self.default_label_key)
        q = request.query_params.get("q") or request.query_params.get("search")

        if value_key not in self.allowed_value_keys:
            raise ValidationError({"value_key": f"Invalid. Allowed: {sorted(self.allowed_value_keys)}"})

        if label_key not in self.allowed_label_keys:
            raise ValidationError({"label_key": f"Invalid. Allowed: {sorted(self.allowed_label_keys)}"})

        qs = self.apply_search(self.get_queryset(), q)
        page = self.paginate_queryset(qs)

        results = [{"value": getattr(obj, value_key), "label": getattr(obj, label_key)} for obj in page]
        return self.get_paginated_response(results)