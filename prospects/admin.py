from django.contrib import admin
from .models import FinancialInstitution, QuarterlyStats

@admin.register(FinancialInstitution)
class FinancialInstitutionAdmin(admin.ModelAdmin):
    list_display = ['charter_number', 'institution_type', 'city', 'state', 'asset_tier']
    list_filter = ['institution_type', 'state', 'asset_tier']
    search_fields = ['charter_number', 'city', 'state']
    ordering = ['charter_number']

@admin.register(QuarterlyStats)
class QuarterlyStatsAdmin(admin.ModelAdmin):
    list_display = ['institution', 'quarter_end_date', 'total_assets', 'total_deposits', 'deposit_change_pct']
    list_filter = ['quarter_end_date', 'institution__institution_type']
    search_fields = ['institution__charter_number']
    ordering = ['-quarter_end_date']
