from django.shortcuts import render
from django.db.models import F, Q, Window, OuterRef, Subquery, Count, Sum
from django.db.models.functions import FirstValue
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import FinancialInstitution, QuarterlyStats
from .serializers import (
    FinancialInstitutionSerializer,
    FinancialInstitutionListSerializer,
    QuarterlyStatsSerializer,
    AssetTierMetricsSerializer,
    DepositDeclineSerializer
)
from rest_framework.permissions import AllowAny
from django.db import connections
from django.db.utils import OperationalError
from django.core.cache import cache
import psutil
import logging
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Create your views here.

class FinancialInstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing financial institutions
    """
    queryset = FinancialInstitution.objects.all()
    serializer_class = FinancialInstitutionSerializer
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FinancialInstitutionListSerializer
        return FinancialInstitutionSerializer

    def get_queryset(self):
        queryset = FinancialInstitution.objects.all()

        # Get the latest stats for each institution
        latest_stats = QuarterlyStats.objects.filter(
            institution=OuterRef('pk')
        ).order_by('-year', '-quarter')

        # Add latest assets and deposits
        queryset = queryset.annotate(
            latest_assets=Subquery(
                latest_stats.values('total_assets')[:1]
            ),
            latest_deposits=Subquery(
                latest_stats.values('total_deposits')[:1]
            )
        )

        # Calculate deposit change percentage
        previous_quarter_stats = QuarterlyStats.objects.filter(
            institution=OuterRef('pk')
        ).order_by('-year', '-quarter')[1:2]

        queryset = queryset.annotate(
            previous_deposits=Subquery(
                previous_quarter_stats.values('total_deposits')[:1]
            )
        ).annotate(
            deposit_change=100 * (F('latest_deposits') - F('previous_deposits')) / F('previous_deposits')
        )

        return queryset

    @action(detail=False, methods=['get'])
    def by_asset_tier(self, request):
        """
        Get metrics grouped by asset tier
        """
        metrics = (
            self.get_queryset()
            .values('asset_tier')
            .annotate(
                institution_count=Count('id'),
                total_assets=Sum('quarterly_stats__total_assets'),
                total_deposits=Sum('quarterly_stats__total_deposits')
            )
            .order_by('asset_tier')
        )
        
        serializer = AssetTierMetricsSerializer(metrics, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def deposit_decline(self, request):
        """
        Get institutions with >5% deposit decline in the last quarter
        """
        current_date = timezone.now().date()
        last_quarter = current_date - timedelta(days=90)
        
        declining_institutions = (
            QuarterlyStats.objects
            .filter(
                quarter_end_date__gte=last_quarter,
                deposit_change_pct__lt=-5
            )
            .select_related('institution')
            .order_by('deposit_change_pct')
        )
        
        serializer = DepositDeclineSerializer(declining_institutions, many=True)
        return Response(serializer.data)

class QuarterlyStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing quarterly statistics
    """
    queryset = QuarterlyStats.objects.all()
    serializer_class = QuarterlyStatsSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by institution if provided
        institution_id = self.request.query_params.get('institution', None)
        if institution_id is not None:
            queryset = queryset.filter(institution_id=institution_id)
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(quarter_end_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(quarter_end_date__lte=end_date)
        
        return queryset

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to monitor system status
    Checks:
    - Database connection
    - Cache connection
    - System resources (CPU, Memory)
    - Application status
    """
    health_status = {
        'status': 'healthy',
        'database': True,
        'cache': True,
        'system': {
            'cpu_usage': None,
            'memory_usage': None,
        }
    }
    
    # Check database connection
    try:
        connections['default'].cursor()
    except OperationalError:
        health_status['database'] = False
        health_status['status'] = 'unhealthy'
        logger.error("Database connection failed during health check")
    
    # Check cache connection
    try:
        cache.set('health_check', 'ok', 1)
        cache.get('health_check')
    except Exception as e:
        health_status['cache'] = False
        health_status['status'] = 'unhealthy'
        logger.error(f"Cache connection failed during health check: {str(e)}")
    
    # Check system resources
    try:
        health_status['system']['cpu_usage'] = psutil.cpu_percent(interval=1)
        health_status['system']['memory_usage'] = psutil.virtual_memory().percent
        
        # Set unhealthy if resources are critically high
        if (health_status['system']['cpu_usage'] > 90 or 
            health_status['system']['memory_usage'] > 90):
            health_status['status'] = 'warning'
            logger.warning("System resources critically high during health check")
    except Exception as e:
        logger.error(f"Error checking system resources: {str(e)}")
        health_status['system'] = None
        health_status['status'] = 'warning'
    
    # Log health check results
    if health_status['status'] != 'healthy':
        logger.warning(f"Health check returned non-healthy status: {health_status}")
    
    return Response(health_status)
