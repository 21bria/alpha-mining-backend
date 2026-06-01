from django.urls import path
from .inventory_raw import (
    get_data_inventory_all,
    get_data_inventory_lim,
    get_data_inventory_sap
    )

from .stockpiles import get_inventory_stockpile

urlpatterns = [
    path('list/', get_data_inventory_all),
    path('lim/', get_data_inventory_lim),
    path('sap/', get_data_inventory_sap),
    path('stockpiles/', get_inventory_stockpile),
]