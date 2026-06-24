"""Firestore-backed AllowedUserRepository — the cloud allowlist (Slice 6).

Layout: `allowed_users/{email}` — the email *is* the document id (lower-cased), so
membership checks are a single doc get and adds are naturally idempotent.
"""
from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import firestore

from ..models import AllowedUser
from .base import AllowedUserRepository

_USERS = "allowed_users"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


class FirestoreAllowedUserRepository(AllowedUserRepository):
    def __init__(self, project: str | None = None) -> None:
        self._db = firestore.Client(project=project) if project else firestore.Client()

    def _to_user(self, doc) -> AllowedUser:
        d = doc.to_dict()
        return AllowedUser(
            email=doc.id,
            added_by=d["added_by"],
            added_at=_as_utc(d["added_at"]),
        )

    def list_users(self) -> list[AllowedUser]:
        users = [self._to_user(d) for d in self._db.collection(_USERS).stream()]
        users.sort(key=lambda u: u.added_at, reverse=True)
        return users

    def is_allowed(self, email: str) -> bool:
        return self._db.collection(_USERS).document(email.lower()).get().exists

    def add_user(self, email: str, added_by: str) -> AllowedUser:
        user = AllowedUser(email=email.lower(), added_by=added_by.lower(), added_at=_now())
        self._db.collection(_USERS).document(user.email).set(
            {"added_by": user.added_by, "added_at": user.added_at}
        )
        return user

    def remove_user(self, email: str) -> bool:
        ref = self._db.collection(_USERS).document(email.lower())
        if not ref.get().exists:
            return False
        ref.delete()
        return True
