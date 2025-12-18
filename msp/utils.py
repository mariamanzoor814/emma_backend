import re
from typing import List, Tuple


KEYWORD_MSP = [
    'managed service',
    'managed-services',
    'managed services',
    'msp',
]

KEYWORD_PE = [
    'private equity',
    'private-equity',
    'private equity firm',
    'pe firm',
]


def text_contains_keywords(text: str, keywords: List[str]) -> bool:
    if not text:
        return False

    text = text.lower()

    for kw in keywords:
        if kw in text:
            return True

    return False


def evaluate_raw_row(raw_firm) -> Tuple[float, list]:
    """Return (score, matched_rules_list)."""

    text_fields = []
    payload = raw_firm.raw_payload or {}

    for key in ('description', 'business', 'industry', 'investments', 'notes'):
        value = payload.get(key) or payload.get(key.title()) or ''
        if value:
            text_fields.append(str(value))

    joined = '\n'.join(text_fields).lower()

    score = 0.0
    matched = []

    if raw_firm.country and raw_firm.country.lower() in ('united states', 'usa', 'us'):
        score += 20
        matched.append('us')

    if text_contains_keywords(joined, KEYWORD_MSP):
        score += 40
        matched.append('msp_keyword')

    if text_contains_keywords(joined, KEYWORD_PE):
        score += 40
        matched.append('pe_keyword')

    if raw_firm.website and re.search(
        r'\b(pe|private-equity|funds|partners)\b',
        raw_firm.website.lower(),
    ):
        score += 10
        matched.append('website_pe_hint')

    return score, matched
