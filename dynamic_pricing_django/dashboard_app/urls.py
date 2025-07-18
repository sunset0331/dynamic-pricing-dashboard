# dashboard_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('product/<str:product_id>/', views.product_detail_view, name='product_detail'),
    path('api/update_product/', views.api_update_product, name='api_update_product'),
    path('api/run_ml_predictions/', views.api_run_ml_predictions, name='api_run_ml_predictions'),
    path('api/add_historical_record/', views.api_add_historical_record, name='api_add_historical_record'),
    path('api/chart/<str:product_id>/<str:chart_type>/', views.api_get_chart, name='api_get_chart'), # New URL
]
