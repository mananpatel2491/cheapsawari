"""Fare providers: the swappable data-source seam for cheapsawari.

Slice 1's core deliverable. Everything downstream depends only on `FareProvider`
and `Offer`, never on a concrete provider, so swapping Amadeus for another source
later is a one-file change.
"""
from .base import FareProvider, ProviderError
from .factory import get_provider

__all__ = ["FareProvider", "ProviderError", "get_provider"]
