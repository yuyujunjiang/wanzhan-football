from __future__ import annotations

from app.settings import settings

from .mock_provider import MockResultsProvider
from .provider import ResultsProvider


def get_results_provider() -> ResultsProvider:
    provider = (settings.results_provider or "mock").lower()
    if provider == "mock":
        return MockResultsProvider()
    if provider == "sporttery":
        from .sporttery import SportteryResultsProvider

        return SportteryResultsProvider()
    if provider == "football_data_org":
        if not settings.football_data_org_token:
            # Graceful fallback for local dev: keep app usable without secrets.
            return MockResultsProvider()
        from .football_data_org import FootballDataOrgProvider

        return FootballDataOrgProvider(token=settings.football_data_org_token)
    raise ValueError(f"Unknown results provider: {settings.results_provider!r}")

