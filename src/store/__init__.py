"""Persistence: the swappable store seam for watches and price snapshots.

Mirrors the providers/ pattern. Everything depends only on `WatchRepository`,
so the SQLite store (default, local) can be swapped for Firestore at Slice 3
without touching the API layer.
"""
from .base import WatchNotFoundError, WatchRepository
from .factory import get_repository

__all__ = ["WatchRepository", "WatchNotFoundError", "get_repository"]
