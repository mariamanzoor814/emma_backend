# backend/accounts/importers.py
import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import (
    AccessLevel, UserProfile,
    LocalChapter, ChapterMembership, MemberTier
)

User = get_user_model()

@transaction.atomic
def import_accounts_from_excel(path: str):
    """
    Expected Excel columns (you can change mapping later):
      email, password(optional), access_level,
      chapter_code(optional), member_tier(optional),
      phone, country, city, address, profession, organization,
      background, education, interests, iq_score, eq_score, gq_score, net_worth,
      plus any extra columns -> UserProfile.extra
    """
    df = pd.read_excel(path)

    for _, row in df.iterrows():
        email = str(row.get("email", "")).strip().lower()
        if not email:
            continue

        access_level = row.get("access_level", AccessLevel.VISITOR)
        if access_level not in dict(AccessLevel.choices):
            access_level = AccessLevel.VISITOR

        # username defaults to email
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"username": email, "access_level": access_level},
        )
        if created:
            # set password if provided; else random unusable
            pw = row.get("password")
            if isinstance(pw, str) and pw.strip():
                user.set_password(pw.strip())
            else:
                user.set_unusable_password()
            user.save()
        else:
            # update access level / email if changed
            user.email = email
            user.access_level = access_level
            user.save(update_fields=["email", "access_level"])

        # profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.access_level = access_level

        # map known fields safely
        for field in [
            "phone","country","city","address","profession","organization",
            "background","education","interests","iq_score","eq_score","gq_score","net_worth"
        ]:
            if field in df.columns and pd.notna(row.get(field)):
                setattr(profile, field, row.get(field))

        # dump unknown columns into extra JSON
        known = set([
            "email","password","access_level",
            "chapter_code","member_tier",
            "phone","country","city","address","profession","organization",
            "background","education","interests","iq_score","eq_score","gq_score","net_worth"
        ])
        extra = {}
        for col in df.columns:
            if col not in known and pd.notna(row.get(col)):
                extra[col] = row.get(col)
        profile.extra = {**(profile.extra or {}), **extra}
        profile.save()

        # chapter + membership
        chapter_code = row.get("chapter_code")
        if isinstance(chapter_code, str) and chapter_code.strip():
            code = chapter_code.strip()
            chapter, _ = LocalChapter.objects.get_or_create(
                code=code,
                defaults={"name": code},
            )
        else:
            chapter = None

        if access_level == AccessLevel.MEMBER:
            tier = row.get("member_tier", MemberTier.TIER_1)
            if tier not in dict(MemberTier.choices):
                tier = MemberTier.TIER_1

            membership, _ = ChapterMembership.objects.get_or_create(user=user)
            membership.chapter = chapter
            membership.member_tier = tier
            membership.save()
