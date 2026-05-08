from __future__ import annotations

from app.settings import settings

from .mock_provider import MockResultsProvider
from .provider import ResultsProvider


_singleton: ResultsProvider | None = None


def get_results_provider() -> ResultsProvider:
    global _singleton
    if _singleton is not None:
        return _singleton
    provider = (settings.results_provider or "mock").lower()
    if provider == "mock":
        _singleton = MockResultsProvider()
        return _singleton
    if provider == "sporttery":
        from .cached_sporttery import CachedSportteryResultsProvider

        _singleton = CachedSportteryResultsProvider()
        return _singleton
    if provider == "football_data_org":
        if not settings.football_data_org_token:
            # Graceful fallback for local dev: keep app usable without secrets.
            _singleton = MockResultsProvider()
            return _singleton
        from .football_data_org import FootballDataOrgProvider

        _singleton = FootballDataOrgProvider(token=settings.football_data_org_token)
        return _singleton
    raise ValueError(f"Unknown results provider: {settings.results_provider!r}")

