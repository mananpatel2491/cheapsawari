"""Allowlist persistence — who may sign in (Slice 6).

Mirrors the `store/` package: a small repository seam with a SQLite default and a
Firestore cloud implementation, selected by the same `WATCH_STORE` setting so the
allowlist lives next to the watches it gates.
"""
from .base import AllowedUserRepository
from .factory import get_user_repository

__all__ = ["AllowedUserRepository", "get_user_repository"]
