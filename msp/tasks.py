from celery import shared_task

from .models import CandidateFirm, RawFirm
from .utils import evaluate_raw_row


@shared_task
def evaluate_and_promote(raw_id, threshold=50.0):
    try:
        raw = RawFirm.objects.get(pk=raw_id)
    except RawFirm.DoesNotExist:
        return False

    score, matched = evaluate_raw_row(raw)

    if score >= threshold:
        CandidateFirm.objects.get_or_create(
            raw_firm=raw,
            defaults={
                'score': score,
                'matched_rules': matched,
                'is_us': 'us' in matched,
                'suspected_msp': 'msp_keyword' in matched,
                'suspected_pe': 'pe_keyword' in matched,
            },
        )

    return True


@shared_task
def batch_promote_raw_ids(raw_ids, threshold=50.0):
    for rid in raw_ids:
        evaluate_and_promote.delay(rid, threshold)