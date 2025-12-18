from django.contrib import admin

from .models import (
    RawFirm,
    CandidateFirm,
    CallVerification,
    VerifiedMSPFirm,
)


@admin.register(RawFirm)
class RawFirmAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'source', 'imported_at', 'is_processed')
    search_fields = ('company_name', 'source', 'source_id')
    readonly_fields = ('raw_payload', 'imported_at')


@admin.register(CandidateFirm)
class CandidateFirmAdmin(admin.ModelAdmin):
    list_display = (
        'raw_firm',
        'score',
        'status',
        'is_us',
        'suspected_msp',
        'suspected_pe',
    )
    list_filter = ('status', 'is_us', 'suspected_msp')
    search_fields = ('raw_firm__company_name',)


@admin.register(CallVerification)
class CallVerificationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'caller', 'result', 'called_at')
    list_filter = ('result', 'contact_method')


@admin.register(VerifiedMSPFirm)
class VerifiedMSPFirmAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'verified_by', 'verified_at', 'confidence')
