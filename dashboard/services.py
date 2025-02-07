"""
Author: Xiaoting Kuang
Dashboard services for handling business logic and data processing.
"""

from django.core.cache import cache
from django.db.models import Count, Sum, F, ExpressionWrapper, FloatField, Max, Avg
from django.db.models.functions import TruncQuarter
from prospects.models import FinancialInstitution, QuarterlyStats
from decimal import Decimal
from typing import Dict, Any, List
import logging
import statistics

logger = logging.getLogger(__name__)

class DashboardMetricsService:
    """Service class for dashboard metrics with caching"""
    
    CACHE_TIMEOUT = 3600  # 1 hour cache timeout
    
    @classmethod
    def get_institution_metrics(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get institution metrics with caching"""
        cache_key = 'dashboard_institution_metrics'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            try:
                # Get metrics by institution type
                type_metrics = list(FinancialInstitution.objects.values('institution_type')\
                    .annotate(
                        count=Count('id')
                    )\
                    .order_by('-count'))
                
                # Rename the type field
                for metric in type_metrics:
                    metric['type'] = metric.pop('institution_type')
                
                # Get top 10 states by institution count
                state_metrics = list(FinancialInstitution.objects.values('state')\
                    .annotate(count=Count('id'))\
                    .order_by('-count')[:10])
                
                metrics = {
                    'type_metrics': type_metrics,
                    'state_metrics': state_metrics
                }
                
                cache.set(cache_key, metrics, cls.CACHE_TIMEOUT)
                logger.info("Institution metrics cached successfully")
            except Exception as e:
                logger.error(f"Error calculating institution metrics: {str(e)}")
                raise
        
        return metrics
    
    @classmethod
    def get_asset_tier_metrics(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get asset tier metrics with caching"""
        cache_key = 'dashboard_asset_tier_metrics'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            try:
                # Get latest stats for each institution
                latest_stats = QuarterlyStats.objects.values(
                    'institution_id'
                ).annotate(
                    latest_assets=Max('total_assets'),
                    latest_deposits=Max('total_deposits')
                )
                
                tier_counts = {
                    '<$100M': {'count': 0, 'total_assets': 0, 'total_deposits': 0},
                    '$100M-$500M': {'count': 0, 'total_assets': 0, 'total_deposits': 0},
                    '$500M-$1B': {'count': 0, 'total_assets': 0, 'total_deposits': 0},
                    '$1B-$10B': {'count': 0, 'total_assets': 0, 'total_deposits': 0},
                    '>$10B': {'count': 0, 'total_assets': 0, 'total_deposits': 0}
                }
                
                for stat in latest_stats:
                    assets = float(stat['latest_assets'])
                    deposits = float(stat['latest_deposits'])
                    
                    if assets < 100_000_000:  # < 100M
                        tier = '<$100M'
                    elif assets < 500_000_000:  # < 500M
                        tier = '$100M-$500M'
                    elif assets < 1_000_000_000:  # < 1B
                        tier = '$500M-$1B'
                    elif assets < 10_000_000_000:  # < 10B
                        tier = '$1B-$10B'
                    else:  # >= 10B
                        tier = '>$10B'
                    
                    tier_counts[tier]['count'] += 1
                    tier_counts[tier]['total_assets'] += assets
                    tier_counts[tier]['total_deposits'] += deposits
                
                tier_metrics = []
                total_assets = sum(t['total_assets'] for t in tier_counts.values())
                total_deposits = sum(t['total_deposits'] for t in tier_counts.values())
                
                for tier, data in tier_counts.items():
                    tier_metrics.append({
                        'tier': tier,
                        'count': data['count'],
                        'total_assets': data['total_assets'],
                        'total_deposits': data['total_deposits'],
                        'asset_share': (data['total_assets'] / total_assets * 100) if total_assets > 0 else 0,
                        'deposit_share': (data['total_deposits'] / total_deposits * 100) if total_deposits > 0 else 0,
                        'deposit_to_asset_ratio': (data['total_deposits'] / data['total_assets'] * 100) if data['total_assets'] > 0 else 0
                    })
                
                metrics = {
                    'tier_metrics': tier_metrics,
                    'total_assets': total_assets,
                    'total_deposits': total_deposits
                }
                
                cache.set(cache_key, metrics, cls.CACHE_TIMEOUT)
                logger.info("Asset tier metrics cached successfully")
            except Exception as e:
                logger.error(f"Error calculating asset tier metrics: {str(e)}")
                raise
        
        return metrics
    
    @classmethod
    def get_time_series_metrics(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get time series metrics with caching"""
        cache_key = 'dashboard_time_series_metrics'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            try:
                quarterly_metrics = list(QuarterlyStats.objects.values('year', 'quarter').annotate(
                    total_assets=Sum('total_assets'),
                    total_deposits=Sum('total_deposits')
                ).order_by('year', 'quarter'))
                
                quarterly_trends = []
                
                for i in range(1, len(quarterly_metrics)):
                    prev = quarterly_metrics[i-1]
                    curr = quarterly_metrics[i]
                    
                    asset_growth = ((curr['total_assets'] - prev['total_assets']) / prev['total_assets'] * 100
                                  if prev['total_assets'] else 0)
                    deposit_growth = ((curr['total_deposits'] - prev['total_deposits']) / prev['total_deposits'] * 100
                                    if prev['total_deposits'] else 0)
                    
                    quarterly_trends.append({
                        'year': curr['year'],
                        'quarter': f"Q{curr['quarter']} {curr['year']}",
                        'asset_growth': round(asset_growth, 2),
                        'deposit_growth': round(deposit_growth, 2)
                    })
                
                metrics = {'quarterly_trends': quarterly_trends}
                cache.set(cache_key, metrics, cls.CACHE_TIMEOUT)
                logger.info("Time series metrics cached successfully")
            except Exception as e:
                logger.error(f"Error calculating time series metrics: {str(e)}")
                raise
        
        return metrics
    
    @classmethod
    def get_state_metrics(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get state-level metrics with caching"""
        cache_key = 'dashboard_state_metrics'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            try:
                # Get latest stats for each state
                state_stats = QuarterlyStats.objects.values(
                    'institution__state'
                ).annotate(
                    institution_count=Count('institution_id', distinct=True),
                    total_assets=Sum('total_assets'),
                    total_deposits=Sum('total_deposits'),
                    avg_deposit_change=Avg('deposit_change_pct')
                ).order_by('-total_assets')
                
                state_metrics = []
                total_assets = sum(float(s['total_assets'] or 0) for s in state_stats)
                
                for stat in state_stats:
                    if not stat['institution__state']:
                        continue
                        
                    assets = float(stat['total_assets'] or 0)
                    deposits = float(stat['total_deposits'] or 0)
                    
                    state_metrics.append({
                        'state': stat['institution__state'],
                        'institution_count': stat['institution_count'],
                        'total_assets': assets,
                        'total_deposits': deposits,
                        'asset_share': (assets / total_assets * 100) if total_assets > 0 else 0,
                        'avg_deposit_change': float(stat['avg_deposit_change'] or 0),
                        'deposit_to_asset_ratio': (deposits / assets * 100) if assets > 0 else 0
                    })
                
                metrics = {
                    'state_metrics': state_metrics[:10],  # Top 10 states
                    'total_states': len(state_metrics)
                }
                
                cache.set(cache_key, metrics, cls.CACHE_TIMEOUT)
                logger.info("State metrics cached successfully")
            except Exception as e:
                logger.error(f"Error calculating state metrics: {str(e)}")
                raise
        
        return metrics
    
    @classmethod
    def get_deposit_trends(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get deposit trend analysis"""
        cache_key = 'dashboard_deposit_trends'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            try:
                # Get institutions with significant deposit changes
                significant_changes = QuarterlyStats.objects.filter(
                    deposit_change_pct__isnull=False
                ).select_related('institution').order_by('deposit_change_pct')
                
                # Calculate distribution of deposit changes
                changes = [float(stat.deposit_change_pct) for stat in significant_changes if stat.deposit_change_pct is not None]
                
                if changes:
                    metrics = {
                        'top_declines': [{
                            'institution': stat.institution.charter_number,
                            'state': stat.institution.state,
                            'change_pct': float(stat.deposit_change_pct),
                            'current_deposits': float(stat.total_deposits)
                        } for stat in significant_changes[:5]],
                        'top_growth': [{
                            'institution': stat.institution.charter_number,
                            'state': stat.institution.state,
                            'change_pct': float(stat.deposit_change_pct),
                            'current_deposits': float(stat.total_deposits)
                        } for stat in significant_changes.reverse()[:5]],
                        'stats': {
                            'median_change': statistics.median(changes),
                            'mean_change': statistics.mean(changes),
                            'std_dev': statistics.stdev(changes) if len(changes) > 1 else 0,
                            'total_analyzed': len(changes)
                        }
                    }
                else:
                    metrics = {
                        'top_declines': [],
                        'top_growth': [],
                        'stats': {
                            'median_change': 0,
                            'mean_change': 0,
                            'std_dev': 0,
                            'total_analyzed': 0
                        }
                    }
                
                cache.set(cache_key, metrics, cls.CACHE_TIMEOUT)
                logger.info("Deposit trends cached successfully")
            except Exception as e:
                logger.error(f"Error calculating deposit trends: {str(e)}")
                raise
        
        return metrics
    
    @classmethod
    def invalidate_all_caches(cls) -> None:
        """Invalidate all dashboard metric caches"""
        cache_keys = [
            'dashboard_institution_metrics',
            'dashboard_asset_tier_metrics',
            'dashboard_time_series_metrics'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        logger.info("All dashboard metric caches invalidated") 