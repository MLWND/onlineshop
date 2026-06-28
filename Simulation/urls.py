from django.urls import path
from . import views

app_name = "simulation"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("brands/", views.brands, name="brands"),
    path("customers/", views.customers, name="customers"),
    path("events/", views.events, name="events"),
    path("reports/", views.reports, name="reports"),
    path("advance/", views.advance_day_view, name="advance_day"),
    path("init/", views.init_data_view, name="init_data"),
]
