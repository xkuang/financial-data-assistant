from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FinancialInstitutionViewSet, QuarterlyStatsViewSet

router = DefaultRouter()
router.register(r'institutions', FinancialInstitutionViewSet)
router.register(r'quarterly-stats', QuarterlyStatsViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 