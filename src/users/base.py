"""The AllowedUserRepository contract — the allowlist persistence seam.

Note: the configured ADMIN_EMAIL is the bootstrap owner and is *always* allowed; it
is not required to have a row here. This store holds the *additional* users the admin
grants access to.
"""
from __future__ import annotations

import abc

from ..models import AllowedUser


class AllowedUserRepository(abc.ABC):
    """Abstract store for the access allowlist. Implementations are per-request safe."""

    @abc.abstractmethod
    def list_users(self) -> list[AllowedUser]:
        """Return all allowed users, newest first."""

    @abc.abstractmethod
    def is_allowed(self, email: str) -> bool:
        """True if `email` (case-insensitive) is on the allowlist."""

    @abc.abstractmethod
    def add_user(self, email: str, added_by: str) -> AllowedUser:
        """Grant access to `email`. Idempotent: re-adding refreshes added_by/added_at."""

    @abc.abstractmethod
    def remove_user(self, email: str) -> bool:
        """Revoke access. Returns True if the user existed."""
