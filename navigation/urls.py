# backend/navigation/urls.py
from django.urls import path

from .views import MenuListView

app_name = "navigation"

urlpatterns = [
    path("menus/", MenuListView.as_view(), name="menu_list"),
]
