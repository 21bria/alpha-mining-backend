from django.db.models import Prefetch, Count, Q
from rest_framework import filters
from rest_framework import filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.permissions import IsAuthenticatedOrReadOnly

from master.api.pagination import StandardResultsSetPagination
from master.api.base import MasterBaseViewSet
from master.models import SampleType, SampleMethod

from .serializers import (
    SampleTypeListSerializer,
    SampleTypeDetailSerializer,
    SampleTypeWriteSerializer,
    SampleMethodSerializer, SampleMethodWriteSerializer
)
from .filters import MathodFilter

class SampleTypeViewSet(MasterBaseViewSet):
    queryset = SampleType.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.OrderingFilter]

    ordering_fields = [
        'id',
        'type_sample',
        'status',
        'is_production',
        'is_geology',
        'is_selling',
        'is_monitoring',
        "batch_pattern",
        'created_at',
        'updated_at',
    ]

    ordering = ['type_sample']
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SampleTypeDetailSerializer

        if self.action in ['create', 'update', 'partial_update']:
            return SampleTypeWriteSerializer

        return SampleTypeListSerializer

    def get_queryset(self):
        queryset = (
            SampleType.objects
            .select_related('user')
            .annotate(total_methods=Count('samplemethod', distinct=True))
            .order_by('type_sample')
        )

        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                Prefetch(
                    'samplemethod_set',
                    queryset=SampleMethod.objects
                    .select_related('user', 'sample_type')
                    .order_by('sample_method')
                )
            )

        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        is_production = self.request.query_params.get('is_production')
        is_geology = self.request.query_params.get('is_geology')
        is_selling = self.request.query_params.get('is_selling')
        is_monitoring = self.request.query_params.get('is_monitoring')

        if status not in [None, '']:
            queryset = queryset.filter(status=status)

        if is_production not in [None, '']:
            queryset = queryset.filter(
                is_production=is_production.lower() == "true"
            )

        if is_geology not in [None, '']:
            queryset = queryset.filter(
                is_geology=is_geology.lower() == "true"
            )

        if is_selling not in [None, '']:
            queryset = queryset.filter(
                is_selling=is_selling.lower() == "true"
            )

        if is_monitoring not in [None, '']:
            queryset = queryset.filter(
                is_monitoring=is_monitoring.lower() == "true"
            )

        if search:
            search = search.strip()

            queryset = queryset.filter(
                Q(type_sample__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset
    
class SampleMethodViewSet(MasterBaseViewSet):
    queryset = SampleMethod.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    filterset_class = MathodFilter
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SampleMethodWriteSerializer
        return SampleMethodSerializer

    def get_queryset(self):
        queryset = (
            SampleMethod.objects
            .select_related('sample_type', 'user')
            .order_by('sample_method')
        )

        search = self.request.query_params.get('search')

        if search:
            queryset = queryset.filter(
                Q(sample_method__icontains=search) |
                Q(description__icontains=search) |
                Q(sample_type__type_sample__icontains=search)
            )

        return queryset