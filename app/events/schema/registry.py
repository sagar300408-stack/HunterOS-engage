"""
HunterOS Engage — Event Schema Registry
app/events/schema/registry.py

Manages schema versioning and payload upgrade adapters for all event types.

Design contract
───────────────
• There is exactly ONE canonical Python class per event type at any point
  in time.  That class represents the LATEST schema version.
• Historical payloads stored in the Event Store carry the schema_version
  they were published with.  They are NEVER mutated in the database.
• At dispatch time, if stored_version < latest_version, the registry applies
  an ordered chain of adapter functions to the raw payload dict before the
  event object is constructed.
• Adapters are pure functions: (dict) → dict.  They must not raise on valid
  payloads and must return a new or mutated dict.
• The BFS chain-resolver finds the shortest valid path between any two
  versions so non-contiguous jumps are supported (v1 → v3 directly, or
  v1 → v2 → v3 through two adapters).

Registering an adapter
──────────────────────
    from app.events.schema import schema_registry

    @schema_registry.adapter("RawWebhookEvent", from_version=1, to_version=2)
    def upgrade_raw_webhook_v1_to_v2(payload: dict) -> dict:
        payload.setdefault("source_channel", "meta_webhook")
        return payload

Startup validation
──────────────────
Call schema_registry.validate() once during application startup.  It checks
for: MISSING_UPGRADE_PATH, MULTIPLE_LATEST, DUPLICATE_ADAPTER (the last is
caught eagerly at registration time).
"""

from __future__ import annotations

import copy
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Validation primitives ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class SchemaValidationError:
    """A single validation finding from SchemaRegistry.validate()."""
    code: str       # DUPLICATE_ADAPTER | MISSING_UPGRADE_PATH | MULTIPLE_LATEST
    message: str
    event_name: str

    def to_dict(self) -> dict:
        return {
            "code":       self.code,
            "message":    self.message,
            "event_name": self.event_name,
        }


class SchemaValidationFailed(Exception):
    """
    Raised by SchemaRegistry.validate() or register_adapter() on validation
    failure.  errors contains the complete list of all problems found.
    """
    def __init__(self, errors: List[SchemaValidationError]) -> None:
        self.errors = errors
        combined = "; ".join(e.message for e in errors)
        super().__init__(f"Schema registry validation failed: {combined}")


# ── Registry ──────────────────────────────────────────────────────────────────

class SchemaRegistry:
    """
    Singleton registry of event schema versions and upgrade adapter chains.

    Lifecycle
    ─────────
    1. Application startup: register_version() is called for every known
       event class (extracted from their schema_version field default).
    2. Application startup: adapter modules are imported, registering adapter
       functions via register_adapter() or the @adapter() decorator.
    3. Application startup: validate() is called; raises SchemaValidationFailed
       if any gaps, ambiguities, or duplicates are found.
    4. Dispatch time: upgrade_payload() is called for each event whose stored
       payload version is older than the latest — zero cost if already current.
    """

    def __init__(self) -> None:
        # event_name → set of known version integers
        self._versions: Dict[str, Set[int]] = defaultdict(set)
        # event_name → {(from_v, to_v): adapter_fn}
        self._adapters: Dict[str, Dict[Tuple[int, int], Callable[[dict], dict]]] = defaultdict(dict)
        # BFS result cache: (event_name, from_v, to_v) → ordered list of fns
        self._chain_cache: Dict[Tuple[str, int, int], List[Callable]] = {}

    # ── Registration API ──────────────────────────────────────────────────────

    def register_version(self, event_name: str, version: int) -> None:
        """
        Declare that a schema version is a known, valid version for an event.

        Called at startup for every event class discovered in the consumer
        registry, using the class's schema_version field default value.
        """
        self._versions[event_name].add(version)

    def register_adapter(
        self,
        event_name: str,
        from_version: int,
        to_version: int,
        fn: Callable[[dict], dict],
    ) -> None:
        """
        Register a payload transformation function from one schema version to
        another for the named event type.

        Adapter functions are pure: they receive a copy of the payload dict
        and must return the transformed dict.  They must not raise on a valid
        input payload.

        Raises:
            SchemaValidationFailed(DUPLICATE_ADAPTER) if a function is already
            registered for the same (event_name, from_version, to_version).
        """
        key = (from_version, to_version)

        if key in self._adapters[event_name]:
            raise SchemaValidationFailed([SchemaValidationError(
                code="DUPLICATE_ADAPTER",
                message=(
                    f"An adapter for '{event_name}' v{from_version}→v{to_version} "
                    f"is already registered as '{self._adapters[event_name][key].__name__}'. "
                    f"Each version transition may have exactly one adapter."
                ),
                event_name=event_name,
            )])

        self._adapters[event_name][key] = fn

        # Implicit version registration from adapter endpoints
        self._versions[event_name].add(from_version)
        self._versions[event_name].add(to_version)

        # Invalidate cached chains for this event (new adapter may shorten paths)
        self._chain_cache = {
            k: v for k, v in self._chain_cache.items()
            if k[0] != event_name
        }

        logger.debug(
            "schema_adapter_registered",
            event_name=event_name,
            from_version=from_version,
            to_version=to_version,
            adapter=fn.__name__,
        )

    def adapter(
        self,
        event_name: str,
        from_version: int,
        to_version: int,
    ) -> Callable:
        """
        Decorator that registers a schema upgrade adapter function.

        Example:
            @schema_registry.adapter("MessageReceived", from_version=1, to_version=2)
            def upgrade_message_received_v1_to_v2(payload: dict) -> dict:
                payload.setdefault("channel", "whatsapp")
                return payload
        """
        def decorator(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
            self.register_adapter(event_name, from_version, to_version, fn)
            return fn
        return decorator

    # ── Version resolution ────────────────────────────────────────────────────

    def get_latest_version(self, event_name: str) -> int:
        """
        Returns the highest registered schema version for the given event type.
        Falls back to 1 (the universal base default) if no version is recorded.
        """
        versions = self._versions.get(event_name)
        return max(versions) if versions else 1

    def needs_upgrade(self, event_name: str, stored_version: int) -> bool:
        """True if the stored payload is at an older schema version than latest."""
        return stored_version < self.get_latest_version(event_name)

    # ── BFS chain resolver ────────────────────────────────────────────────────

    def resolve_chain(
        self,
        event_name: str,
        from_version: int,
        to_version: int,
    ) -> List[Callable[[dict], dict]]:
        """
        Build the ordered list of adapter functions that upgrades a payload
        from from_version to to_version using BFS over the adapter graph.

        BFS guarantees the shortest (fewest adapter steps) path is found.
        Results are cached; repeated calls for the same transition are O(1).

        Args:
            event_name:   Event class name.
            from_version: Version the payload is currently at.
            to_version:   Target version (usually the latest).

        Returns:
            Ordered list of adapter callables.  Empty list if from == to.

        Raises:
            ValueError if no upgrade path exists between the two versions.
        """
        if from_version == to_version:
            return []

        cache_key = (event_name, from_version, to_version)
        if cache_key in self._chain_cache:
            return self._chain_cache[cache_key]

        adapters = self._adapters.get(event_name, {})
        if not adapters:
            raise ValueError(
                f"No adapters registered for event '{event_name}'. "
                f"Cannot upgrade payload from v{from_version} to v{to_version}."
            )

        # BFS: state = (current_version, accumulated_chain)
        queue:   deque[Tuple[int, List[Callable]]] = deque([(from_version, [])])
        visited: Set[int] = {from_version}

        while queue:
            current_v, chain = queue.popleft()
            for (f, t), fn in adapters.items():
                if f != current_v or t in visited:
                    continue
                new_chain = chain + [fn]
                if t == to_version:
                    self._chain_cache[cache_key] = new_chain
                    return new_chain
                visited.add(t)
                queue.append((t, new_chain))

        raise ValueError(
            f"No complete upgrade path found for event '{event_name}' "
            f"from v{from_version} to v{to_version}. "
            f"Registered adapters: {sorted(adapters.keys())}"
        )

    # ── Payload upgrade ───────────────────────────────────────────────────────

    def upgrade_payload(
        self,
        event_name: str,
        payload: dict,
        stored_version: int,
    ) -> dict:
        """
        Upgrade a stored payload dict to the latest schema version.

        The input payload is deep-copied before transformation so the original
        EventRecord.payload dict (and the database record) are NEVER mutated.
        The upgrade is purely in-memory and applied only during the current
        dispatch cycle.  This preserves the complete audit trail in the store.

        Args:
            event_name:     Event class name (used to look up adapters).
            payload:        The raw dict from EventRecord.payload (may be
                            the JSONB dict returned by SQLAlchemy; not mutated).
            stored_version: The schema_version value stored in the payload.
                            If absent in the dict, callers should default to 1.

        Returns:
            New dict with all adapter transformations applied and
            schema_version set to the latest version.

        Raises:
            ValueError if no upgrade path exists between versions.
        """
        latest = self.get_latest_version(event_name)

        if stored_version >= latest:
            # Nothing to do — payload is already at the latest version
            return payload

        chain = self.resolve_chain(event_name, stored_version, latest)

        logger.info(
            "schema_upgrade_started",
            event_name=event_name,
            stored_version=stored_version,
            target_version=latest,
            adapter_count=len(chain),
            adapters=[fn.__name__ for fn in chain],
        )

        # Deep-copy guarantees the original dict is untouched
        upgraded = copy.deepcopy(payload)

        for step_idx, adapter_fn in enumerate(chain):
            try:
                upgraded = adapter_fn(upgraded)
            except Exception as exc:
                logger.error(
                    "schema_upgrade_adapter_failed",
                    event_name=event_name,
                    step=step_idx,
                    adapter=adapter_fn.__name__,
                    error=str(exc),
                    exc_info=True,
                )
                raise

        # Stamp the upgraded version so the reconstituted event reflects reality
        upgraded["schema_version"] = latest

        logger.info(
            "schema_upgrade_completed",
            event_name=event_name,
            from_version=stored_version,
            to_version=latest,
            adapter_count=len(chain),
        )

        return upgraded

    # ── Startup validation ────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Validate the entire schema registry.  Call once at application startup
        AFTER all adapter modules have been imported and all event classes have
        been scanned.

        Checks performed
        ────────────────
        DUPLICATE_ADAPTER     — detected eagerly at register_adapter() time
                                (not re-checked here; raises immediately on
                                registration).
        MULTIPLE_LATEST       — the adapter graph contains dead-end branch
                                versions: versions that are the target of at
                                least one adapter but have no outgoing adapter
                                and are not the declared latest.  These branches
                                make it impossible to upgrade data that reaches
                                the dead-end version.  Fires before path checks
                                because the graph structure is malformed.
        MISSING_UPGRADE_PATH  — a registered version older than the latest has
                                no valid adapter path to reach it.  Also fires
                                when multiple versions are registered but no
                                adapters exist at all.

        Raises:
            SchemaValidationFailed — with ALL errors collected, not just first.
        """
        errors: List[SchemaValidationError] = []

        total_adapters = sum(len(a) for a in self._adapters.values())
        logger.info(
            "schema_registry_startup_validation_starting",
            registered_event_types=len(self._versions),
            total_adapters=total_adapters,
        )

        for event_name, versions in self._versions.items():
            adapters = self._adapters.get(event_name, {})
            latest   = max(versions)

            # Single-version events with no adapters are trivially valid
            if len(versions) == 1 and not adapters:
                continue

            if adapters:
                # ── MULTIPLE_LATEST check ─────────────────────────────────
                # A dead-end branch is a version that is the destination of
                # at least one adapter but has no outgoing adapter AND is not
                # the declared latest.  Such branches trap upgrade paths that
                # diverged from the main chain and never converged back.
                all_from  = {f for f, _ in adapters}
                all_to    = {t for _, t in adapters}
                # Versions with no outgoing adapter = potential "terminals"
                sinks     = all_to - all_from
                # Dead-ends are terminals that are NOT the declared latest
                dead_ends = sinks - {latest}

                if dead_ends:
                    errors.append(SchemaValidationError(
                        code="MULTIPLE_LATEST",
                        message=(
                            f"Event '{event_name}' has dead-end branch version(s) "
                            f"{sorted(dead_ends)}: they are adapter targets with no "
                            f"outgoing adapter and are not the declared latest v{latest}. "
                            f"Add adapters to connect them to v{latest} or remove the "
                            f"orphaned adapter registrations."
                        ),
                        event_name=event_name,
                    ))
                    # Graph is structurally malformed; skip path checks
                    continue

            # ── MISSING_UPGRADE_PATH check ────────────────────────────────
            # Every registered version older than latest must have a
            # reachable BFS path to latest so any historical event can be
            # dispatched without errors.  This also catches the case where
            # multiple versions are registered but no adapters exist.
            for v in sorted(versions):
                if v == latest:
                    continue
                try:
                    self.resolve_chain(event_name, v, latest)
                except ValueError as exc:
                    errors.append(SchemaValidationError(
                        code="MISSING_UPGRADE_PATH",
                        message=(
                            f"No upgrade path exists for event '{event_name}' from "
                            f"v{v} to the declared latest v{latest}. Historical events "
                            f"at v{v} cannot be dispatched. Detail: {exc}"
                        ),
                        event_name=event_name,
                    ))

        if errors:
            for err in errors:
                logger.error("schema_registry_validation_error", **err.to_dict())
            raise SchemaValidationFailed(errors)

        logger.info(
            "schema_registry_startup_validation_completed",
            registered_event_types=len(self._versions),
            total_adapters=total_adapters,
            status="OK",
        )


    # ── Introspection ─────────────────────────────────────────────────────────

    def describe(self) -> dict:
        """
        Full structured description of the registry — useful for startup logs
        and admin dashboards.
        """
        return {
            "event_types": {
                event_name: {
                    "known_versions": sorted(versions),
                    "latest_version": self.get_latest_version(event_name),
                    "adapters": [
                        {
                            "from_version": f,
                            "to_version":   t,
                            "fn":           self._adapters[event_name][(f, t)].__name__,
                        }
                        for (f, t) in sorted(self._adapters.get(event_name, {}))
                    ],
                }
                for event_name, versions in self._versions.items()
            }
        }
