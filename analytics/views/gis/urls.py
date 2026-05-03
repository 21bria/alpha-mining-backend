from django.urls import path

from .geo_json_mine_iup import api_iup_with_sources

urlpatterns = [
    path("mine-iup/<int:iup_id>/",api_iup_with_sources, name="iup-with-sources"),
]