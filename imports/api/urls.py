from django.urls import path
from .views import ImportJobDetailView, ImportJobRowListView,ImportJobListView

urlpatterns = [
    path("import-jobs/", ImportJobListView.as_view()),
    path("import-jobs/<uuid:pk>/", ImportJobDetailView.as_view()),
    path("import-jobs/<uuid:pk>/rows/", ImportJobRowListView.as_view()),
]
