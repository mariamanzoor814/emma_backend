# File: backend/msp/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from .models import CandidateFirm, CallVerification, VerifiedMSPFirm
from .serializers import CandidateFirmSerializer, CallVerificationSerializer, VerifiedMSPFirmSerializer
from accounts.permissions import HasMinAccessLevel

MemberOrAbove = HasMinAccessLevel.with_level('member')
AdminOnly = HasMinAccessLevel.with_level('admin')

class CallVerificationViewSet(viewsets.ModelViewSet):
    queryset = CallVerification.objects.all().select_related('candidate', 'caller')
    serializer_class = CallVerificationSerializer
    permission_classes = [MemberOrAbove()]

class VerifiedMSPFirmViewSet(viewsets.ModelViewSet):
    queryset = VerifiedMSPFirm.objects.all().select_related('candidate', 'verified_by')
    serializer_class = VerifiedMSPFirmSerializer
    permission_classes = [AdminOnly()]

class CandidateFirmViewSet(viewsets.ModelViewSet):
    queryset = CandidateFirm.objects.all().select_related('raw_firm').order_by('-score')
    serializer_class = CandidateFirmSerializer
    permission_classes = [MemberOrAbove()]

    # caller calls this to atomically claim the next candidate
    @action(detail=False, methods=['post'], url_path='claim-next')
    def claim_next(self, request):
        user = request.user
        # filter: only pending candidates, not locked recently or assigned to someone else
        now = timezone.now()
        ten_minutes_ago = now - timezone.timedelta(minutes=10)
        qs = CandidateFirm.objects.filter(
            status=CandidateFirm.STATUS_PENDING
        ).filter(
            Q(locked_at__isnull=True) | Q(locked_at__lt=ten_minutes_ago) | Q(locked_by=user)
        ).order_by('-score')

        with transaction.atomic():
            candidate = qs.select_for_update(skip_locked=True).first()
            if not candidate:
                return Response({'detail': 'No candidates available'}, status=status.HTTP_204_NO_CONTENT)
            candidate.locked_by = user
            candidate.locked_at = timezone.now()
            candidate.assigned_to = user
            candidate.save(update_fields=['locked_by', 'locked_at', 'assigned_to', 'updated_at'])
            return Response(CandidateFirmSerializer(candidate, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[MemberOrAbove()], url_path='log-call')
    def log_call(self, request, pk=None):
        candidate = self.get_object()
        serializer = CallVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(candidate=candidate, caller=request.user)
        # update candidate last_called_at (signal in model handles)
        return Response({'detail': 'Call logged'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[AdminOnly()], url_path='verify')
    def verify_candidate(self, request, pk=None):
        candidate = self.get_object()
        if candidate.status == CandidateFirm.STATUS_VERIFIED:
            return Response({'detail': 'Already verified'}, status=status.HTTP_400_BAD_REQUEST)
        candidate.status = CandidateFirm.STATUS_VERIFIED
        candidate.save(update_fields=['status', 'updated_at'])
        verified = VerifiedMSPFirm.objects.create(candidate=candidate, verified_by=request.user)
        return Response(VerifiedMSPFirmSerializer(verified).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[AdminOnly()], url_path='export-verified')
    def export_verified(self, request):
        # simple CSV download
        from django.http import HttpResponse
        import csv

        qs = CandidateFirm.objects.filter(status=CandidateFirm.STATUS_VERIFIED).select_related('raw_firm')
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename=verified_msp_firms.csv'
        writer = csv.writer(resp)
        writer.writerow(['company_name', 'website', 'email', 'phone', 'score', 'verified_at', 'verified_by'])
        for c in qs:
            try:
                verified = c.verified  # one-to-one VerifiedMSPFirm
                vb = verified.verified_by.email if verified.verified_by else ''
                vat = verified.verified_at.isoformat()
            except VerifiedMSPFirm.DoesNotExist:
                vb = ''
                vat = ''
            writer.writerow([c.raw_firm.company_name, c.raw_firm.website, c.raw_firm.email, c.raw_firm.phone, c.score, vat, vb])
        return resp

