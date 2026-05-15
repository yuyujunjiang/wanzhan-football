from __future__ import annotations

import importlib

from .mock_provider import MockResultsProvider
from .provider import ResultsProvider


_singleton: ResultsProvider | None = None
_cached_provider_key: str | None = None


def get_results_provider() -> ResultsProvider:
    """Return the configured results provider, rebuilding if settings change (e.g. tests reload settings)."""
    global _singleton, _cached_provider_key
    settings = importlib.import_module("app.settings").settings
    provider = (settings.results_provider or "mock").lower()
    if _singleton is not None and _cached_provider_key == provider:
        return _singleton

    _singleton = None
    _cached_provider_key = provider
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
    raise ValueError(f"Unknown results provider: {provider!r}")

