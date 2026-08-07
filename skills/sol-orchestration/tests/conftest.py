"""Shared fixtures — chiefly the recording host double every later unit tests against.

The double is the reason no gate in this package spends model quota. It records every
host request the package makes, so a test can assert on the *shape of the traffic*
rather than only on the return value: that availability was resolved with one query
per allowlist entry and never with a single catalog enumeration, that a limit above
the runtime's cap was never sent, and later that a spawn carried an explicit selector.

``find_models`` deliberately reimplements the runtime's own matching and truncation
(``findRlmModelMatches`` in ``dist/core/rlm-runtime.js``: normalise, score exact then
prefix then partial, sort, slice to the limit). A double that returned everything it
was asked for would make the twenty-result cap invisible, which is precisely the
failure the per-entry query exists to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from sol_orchestration import host as host_module

#: Mirrors the runtime's own MAX_RLM_MODEL_SEARCH_LIMIT.
RUNTIME_SEARCH_CAP = 20


def _normalise(value: str) -> str:
    """Mirror the runtime's normalizeModelSearchText."""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


class RecordingHost(host_module.Host):
    """A host double that answers from a seeded catalog and records every request.

    Args:
        catalog: Selectors the authenticated model search should be able to return.
        subagents: Registry entries ``list_subagents`` should report.
        roster: Reply for ``agent_message.list_agents``; ``None`` makes it unreachable,
            which is how a session that is not daemon-backed presents itself.
        observe: Whether ``agent_observe.list`` is reachable.
        failures: Selectors whose availability query should raise, standing in for an
            expired credential.
    """

    def __init__(
        self,
        catalog: tuple[str, ...] = (),
        subagents: tuple[host_module.Subagent, ...] = (),
        roster: dict[str, Any] | None = None,
        observe: bool = True,
        failures: tuple[str, ...] = (),
    ) -> None:
        self.catalog = catalog
        self.subagents_registry = subagents
        self.roster = roster or {
            "current": {"name": "orchestrator", "id": "sess-1", "depth": 0},
            "entries": [],
        }
        self._roster_unreachable = False
        self.observe = observe
        self.failures = failures
        #: Every ``find_models`` call, as ``(query, limit)`` — the enumeration tripwire.
        self.searches: list[tuple[str, int]] = []
        #: Every generic host request, as ``(type, payload)``.
        self.requests: list[tuple[str, dict[str, Any] | None]] = []

    def without_roster(self) -> RecordingHost:
        """Present as a session whose agent-family roster is unavailable."""
        self._roster_unreachable = True
        return self

    async def request(self, request_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.requests.append((request_type, payload))
        if request_type == "agent_message.list_agents":
            if self._roster_unreachable:
                raise RuntimeError("agent family roster is not available in this session")
            return dict(self.roster)
        if request_type == "agent_observe.list":
            if not self.observe:
                raise RuntimeError("agent observation is not available in this session")
            return {"agents": []}
        raise RuntimeError(f'no handler for host request "{request_type}" in this session')

    async def find_models(
        self, query: str = "", limit: int = host_module.MODEL_SEARCH_LIMIT
    ) -> tuple[host_module.ModelMatch, ...]:
        self.searches.append((query, limit))
        if limit > RUNTIME_SEARCH_CAP:
            raise RuntimeError(f"rlm.find_models limit must be an integer from 1 to {RUNTIME_SEARCH_CAP}")
        if query in self.failures:
            raise RuntimeError(f"authentication failed for {query}")
        normalised_query = _normalise(query.strip())
        scored: list[tuple[float, str]] = []
        for selector in self.catalog:
            fields = [_normalise(selector), _normalise(selector.split("/", 1)[-1])]
            score = float("inf") if normalised_query else 0.0
            if normalised_query:
                if normalised_query in fields:
                    score = float(fields.index(normalised_query))
                elif any(field.startswith(normalised_query) for field in fields):
                    score = 3.0
                elif any(normalised_query in field for field in fields):
                    score = 6.0
            if score != float("inf") or not normalised_query:
                scored.append((score, selector))
        scored.sort(key=lambda item: (item[0], item[1]))
        return tuple(
            host_module.ModelMatch(
                provider=selector.split("/", 1)[0],
                id=selector.split("/", 1)[1],
                name=selector.split("/", 1)[1],
                selector=selector,
            )
            for _, selector in scored[:limit]
        )

    async def list_subagents(self) -> tuple[host_module.Subagent, ...]:
        self.requests.append(("rlm.list_subagents", None))
        return self.subagents_registry


@pytest.fixture
def recording_host() -> RecordingHost:
    return RecordingHost()


@pytest.fixture
def agent_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A disposable Prime Agent home with both isolation variables redirected.

    Redirecting the home alone is not isolation: Prime Agent resolves the kernel venv
    from its own variable and otherwise from a path hardcoded off the real user home.
    """
    from sol_orchestration import home

    disposable = tmp_path / "agent-home"
    disposable.mkdir()
    monkeypatch.setenv(home.HOME_ENV_VAR, str(disposable))
    monkeypatch.setenv(home.KERNEL_VENV_ENV_VAR, str(tmp_path / "kernel-venv"))
    return disposable
