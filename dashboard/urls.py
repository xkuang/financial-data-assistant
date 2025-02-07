from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='index'),
    path('api/metrics/institutions/', views.institution_metrics, name='institution_metrics'),
    path('api/metrics/asset-tiers/', views.asset_tier_metrics, name='asset_tier_metrics'),
    path('api/metrics/time-series/', views.time_series_metrics, name='time_series_metrics'),
    path('api/metrics/states/', views.state_metrics, name='state_metrics'),
    path('api/metrics/deposit-trends/', views.deposit_trends, name='deposit_trends'),
    path('stats/', views.stats_dashboard, name='stats_dashboard'),
] 