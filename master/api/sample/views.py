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
    ordering_fields = ['id', 'type_sample', 'category', 'status', 'created_at', 'updated_at']
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
                    queryset=SampleMethod.objects.select_related('user', 'sample_type').order_by('sample_method')
                )
            )

        category = self.request.query_params.get('category')
        status = self.request.query_params.get('status')
        search = self.request.query_params.get('search')

        if category:
            queryset = queryset.filter(category__iexact=category.strip())

        if status not in [None, '']:
            queryset = queryset.filter(status=status)

        if search:
            search = search.strip()
            queryset = queryset.filter(
                Q(type_sample__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
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