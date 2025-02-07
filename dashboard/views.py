"""
Author: Xiaoting Kuang
Dashboard views for displaying financial data analytics and visualizations.
"""

from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db.models import Count, Sum, F, ExpressionWrapper, FloatField
from django.db.models.functions import TruncQuarter
from prospects.models import FinancialInstitution, QuarterlyStats
from decimal import Decimal
import json
from .services import DashboardMetricsService
from .middleware import rate_limit_decorator
from django.core.cache import cache
import pandas as pd

# Create your views here.

class DashboardView(TemplateView):
    template_name = 'dashboard/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = DashboardMetricsService()
        
        # Get total institutions count
        institution_metrics = service.get_institution_metrics()
        type_metrics = institution_metrics.get('type_metrics', [])
        total_institutions = sum(metric['count'] for metric in type_metrics)
        
        # Get latest total assets and deposits
        asset_metrics = service.get_asset_tier_metrics()
        total_assets = asset_metrics.get('total_assets', 0)
        total_deposits = asset_metrics.get('total_deposits', 0)
        
        # Convert to billions for display
        total_assets_b = float(total_assets) / 1_000_000_000
        total_deposits_b = float(total_deposits) / 1_000_000_000
        
        context.update({
            'total_institutions': total_institutions,
            'total_assets': total_assets,
            'total_deposits': total_deposits,
            'total_assets_b': total_assets_b,
            'total_deposits_b': total_deposits_b,
        })
        
        return context

@rate_limit_decorator(requests=100, interval=60)
def institution_metrics(request):
    """API endpoint for institution metrics"""
    try:
        metrics = DashboardMetricsService.get_institution_metrics()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@rate_limit_decorator(requests=100, interval=60)
def asset_tier_metrics(request):
    """API endpoint for asset tier metrics"""
    try:
        metrics = DashboardMetricsService.get_asset_tier_metrics()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@rate_limit_decorator(requests=100, interval=60)
def state_metrics(request):
    """API endpoint for state-level metrics"""
    try:
        metrics = DashboardMetricsService.get_state_metrics()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@rate_limit_decorator(requests=100, interval=60)
def deposit_trends(request):
    """API endpoint for deposit trend analysis"""
    try:
        metrics = DashboardMetricsService.get_deposit_trends()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@rate_limit_decorator(requests=100, interval=60)
def time_series_metrics(request):
    """API endpoint for quarterly growth trends"""
    try:
        metrics = DashboardMetricsService.get_time_series_metrics()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def stats_dashboard(request):
    # Read the statistics file
    try:
        tier_stats = pd.read_csv('dashboard/static/visualizations/tier_statistics.csv')
        tier_stats_html = tier_stats.to_html(classes='table table-striped', index=True)
    except FileNotFoundError:
        tier_stats_html = "<p>Statistics not yet generated</p>"
    
    context = {
        'tier_stats': tier_stats_html
    }
    return render(request, 'stats_dashboard.html', context)
