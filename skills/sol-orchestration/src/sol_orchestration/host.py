"""The one seam every host request passes through.

Two properties are load-bearing, and both are easy to lose by accident.

**A single injection point.** Without it the spawn path can only be exercised live,
and the rule that no automated gate spends model quota becomes aspirational. With it,
every later unit tests against a recording double that can assert on the *shape* of
the traffic — that availability was resolved one entry at a time, that a spawn
carried an explicit selector — not merely on return values.

**A lazy runtime import.** The runtime ships with Prime Agent and is not published on
PyPI, and the skill contract forbids declaring it as a dependency. A module-level
``import rlm`` would therefore make this package unimportable everywhere except a
kernel, including the standalone test run that proves it works. Every import here
sits inside a call, and the failure is reported as an unavailable host rather than an
ImportError escaping from module load.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The runtime rejects a search limit above its own cap of twenty, so this package
#: keeps its own copy and refuses locally: a live error is worth turning into a test.
MODEL_SEARCH_LIMIT = 20

#: The bundled runtime module. Imported lazily inside calls, never at module level.
RUNTIME_MODULE = "rlm"


class HostUnavailable(RuntimeError):
    """The Prime Agent host bridge is not reachable from this process."""


def checked_limit(limit: int) -> int:
    """Return ``limit`` if the host would accept it, else raise before the request.

    Raises:
        ValueError: The limit is outside the range the runtime accepts.
    """
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError(f"model search limit must be an int, got {type(limit).__name__}")
    if limit < 1 or limit > MODEL_SEARCH_LIMIT:
        raise ValueError(f"model search limit must be an integer from 1 to {MODEL_SEARCH_LIMIT}, got {limit}")
    return limit


@dataclass(frozen=True)
class ModelMatch:
    """One authenticated model, as the host's search reports it."""

    provider: str
    id: str
    name: str
    selector: str


@dataclass(frozen=True)
class Subagent:
    """One entry in the parent session's child registry.

    ``active_session_id`` is the retention signal and the only one that matters for
    corrections: the host populates it solely for daemon-backed children, and the
    bundled agent-message skill addresses a child only when it is present.
    """

    child_id: str
    active_session_id: str | None
    session_id: str | None
    session_name: str
    session_dir: Path
    status: str


class Host:
    """The host requests this package is allowed to make.

    Subclasses answer them from the live runtime, from a recording double, or by
    reporting the bridge as unavailable. Nothing outside this module talks to the
    runtime directly.
    """

    async def request(self, request_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Issue a typed host request and return the host's reply."""
        raise NotImplementedError

    async def find_models(self, query: str = "", limit: int = MODEL_SEARCH_LIMIT) -> tuple[ModelMatch, ...]:
        """Search the authenticated model catalog, bounded by the host's own cap."""
        raise NotImplementedError

    async def list_subagents(self) -> tuple[Subagent, ...]:
        """List the direct children the parent session currently retains."""
        raise NotImplementedError


class RuntimeHost(Host):
    """Answers from the bundled runtime, imported lazily on every call."""

    def _runtime(self) -> Any:
        try:
            return importlib.import_module(RUNTIME_MODULE)
        except Exception as error:  # ImportError in a kernel-less process, anything else in a broken one
            raise HostUnavailable(
                f"the Prime Agent runtime ({RUNTIME_MODULE}) is unavailable: {error}"
            ) from error

    async def request(self, request_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._runtime().host_request(request_type, payload)

    async def find_models(self, query: str = "", limit: int = MODEL_SEARCH_LIMIT) -> tuple[ModelMatch, ...]:
        models = await self._runtime().find_models(query, checked_limit(limit))
        return tuple(
            ModelMatch(provider=model.provider, id=model.id, name=model.name, selector=model.selector)
            for model in models
        )

    async def list_subagents(self) -> tuple[Subagent, ...]:
        entries = await self._runtime().list_subagents()
        return tuple(
            Subagent(
                child_id=entry.rlm_child_id,
                active_session_id=entry.active_session_id,
                session_id=entry.session_id,
                session_name=entry.session_name,
                session_dir=Path(entry.session_dir),
                status=entry.status,
            )
            for entry in entries
        )


class UnavailableHost(Host):
    """Reports the bridge as unreachable, carrying the reason it was not reachable."""

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def _fail(self) -> HostUnavailable:
        return HostUnavailable(f"no Prime Agent host bridge in this process: {self.reason}")

    async def request(self, request_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        raise self._fail()

    async def find_models(self, query: str = "", limit: int = MODEL_SEARCH_LIMIT) -> tuple[ModelMatch, ...]:
        raise self._fail()

    async def list_subagents(self) -> tuple[Subagent, ...]:
        raise self._fail()


_installed: Host | None = None


def current() -> Host:
    """Return the host in force — the injected one, or the live runtime."""
    if _installed is not None:
        return _installed
    return RuntimeHost()


def install(host: Host) -> None:
    """Replace the host in force. The single injection point in the package."""
    global _installed
    _installed = host


def reset() -> None:
    """Drop any injected host and go back to the live runtime."""
    global _installed
    _installed = None


class using:
    """Install a host for the duration of a block, then restore the previous one."""

    def __init__(self, host: Host) -> None:
        self._host = host
        self._previous: Host | None = None

    def __enter__(self) -> Host:
        global _installed
        self._previous = _installed
        _installed = self._host
        return self._host

    def __exit__(self, *exc_info: object) -> None:
        global _installed
        _installed = self._previous
