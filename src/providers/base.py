"""The FareProvider contract — the seam every data source must implement."""
from __future__ import annotations

import abc
from datetime import date as _date

from ..models import Offer


class ProviderError(RuntimeError):
    """Raised when a provider cannot fulfil a request (auth, network, upstream error).

    Distinct from "no offers found" — that case returns None, not an exception.
    """


class FareProvider(abc.ABC):
    """Abstract fare data source.

    Implementations translate a route+date query into a normalized :class:`Offer`.
    They must NOT leak provider-specific response shapes upward.
    """

    #: Stable identifier stamped onto every Offer this provider returns.
    name: str = "base"

    @abc.abstractmethod
    def get_cheapest_offer(
        self, origin: str, destination: str, departure_date: _date, cabin: str = "ECONOMY"
    ) -> Offer | None:
        """Return the cheapest available offer, or None if no offers exist.

        Args:
            origin: Origin IATA code (3 letters, already validated/upper-cased by the caller).
            destination: Destination IATA code.
            departure_date: Departure date.
            cabin: Requested cabin class.

        Returns:
            The cheapest :class:`Offer`, or ``None`` when the upstream has no inventory.

        Raises:
            ProviderError: On auth/network/upstream failures (i.e. we could not get an answer).
        """
        raise NotImplementedError
