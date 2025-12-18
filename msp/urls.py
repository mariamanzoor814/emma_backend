# File: backend/msp/urls.py
from rest_framework.routers import DefaultRouter
from .views import CandidateFirmViewSet, CallVerificationViewSet, VerifiedMSPFirmViewSet

router = DefaultRouter()
router.register(r'candidates', CandidateFirmViewSet, basename='candidate')
router.register(r'calls', CallVerificationViewSet, basename='call')
router.register(r'verified', VerifiedMSPFirmViewSet, basename='verified')

urlpatterns = router.urls
