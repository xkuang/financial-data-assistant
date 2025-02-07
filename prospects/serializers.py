from rest_framework import serializers
from .models import FinancialInstitution, QuarterlyStats

class QuarterlyStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for quarterly financial statistics
    """
    class Meta:
        model = QuarterlyStats
        fields = [
            'id',
            'quarter_end_date',
            'total_assets',
            'total_deposits',
            'deposit_change_pct',
            'created_at',
            'updated_at'
        ]

class FinancialInstitutionSerializer(serializers.ModelSerializer):
    """
    Serializer for financial institutions
    """
    latest_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialInstitution
        fields = [
            'id',
            'institution_type',
            'charter_number',
            'web_domain',
            'city',
            'state',
            'asset_tier',
            'latest_stats',
            'created_at',
            'updated_at'
        ]
    
    def get_latest_stats(self, obj):
        latest_stats = obj.quarterly_stats.first()
        if latest_stats:
            return QuarterlyStatsSerializer(latest_stats).data
        return None

class AssetTierMetricsSerializer(serializers.Serializer):
    """
    Serializer for asset tier analysis
    """
    asset_tier = serializers.CharField()
    institution_count = serializers.IntegerField()
    total_assets = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_deposits = serializers.DecimalField(max_digits=14, decimal_places=2)

class DepositDeclineSerializer(serializers.Serializer):
    """
    Serializer for institutions with deposit decline
    """
    institution = FinancialInstitutionSerializer()
    quarter_end_date = serializers.DateField()
    deposit_change_pct = serializers.DecimalField(max_digits=7, decimal_places=2)
    previous_deposits = serializers.DecimalField(max_digits=14, decimal_places=2)
    current_deposits = serializers.DecimalField(max_digits=14, decimal_places=2)

class FinancialInstitutionListSerializer(serializers.ModelSerializer):
    latest_assets = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    latest_deposits = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    deposit_change = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = FinancialInstitution
        fields = [
            'id', 'type', 'name', 'city', 'state', 'latest_assets',
            'latest_deposits', 'deposit_change'
        ] 