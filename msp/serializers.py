from rest_framework import serializers

from .models import (
    RawFirm,
    CandidateFirm,
    CallVerification,
    VerifiedMSPFirm,
)


class RawFirmSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawFirm
        fields = '__all__'
        read_only_fields = ('imported_at', 'is_processed')


class CandidateFirmSerializer(serializers.ModelSerializer):
    raw_firm = RawFirmSerializer(read_only=True)

    class Meta:
        model = CandidateFirm
        fields = '__all__'
        read_only_fields = ('raw_firm', 'created_at', 'updated_at')


class CallVerificationSerializer(serializers.ModelSerializer):
    caller = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = CallVerification
        fields = ('id', 'candidate', 'caller', 'contact_method', 'result', 'notes', 'called_at')
        read_only_fields = ('called_at', 'caller')


class VerifiedMSPFirmSerializer(serializers.ModelSerializer):
    candidate = CandidateFirmSerializer(read_only=True)

    class Meta:
        model = VerifiedMSPFirm
        fields = '__all__'
        read_only_fields = ('verified_at',)
