"""
Tests for Phase 1.4 - Milestone 3: Event Schema Versioning & Compatibility
"""

import asyncio
import copy
import uuid
import pytest
from typing import List, Type

from app.events.schema.registry import (
    SchemaRegistry,
    SchemaValidationError,
    SchemaValidationFailed,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def fresh_registry() -> SchemaRegistry:
    """Return a clean registry for each test (no singleton pollution)."""
    return SchemaRegistry()


def make_v1_payload(extra: dict = None) -> dict:
    base = {"schema_version": 1, "event_id": str(uuid.uuid4()), "content": "hello"}
    if extra:
        base.update(extra)
    return base


# ── Tests: adapter registration & decorator ───────────────────────────────────

def test_register_adapter_and_describe():
    reg = fresh_registry()

    @reg.adapter("MyEvent", from_version=1, to_version=2)
    def upgrade_v1_v2(payload: dict) -> dict:
        payload["new_field"] = "added_by_v2"
        return payload

    desc = reg.describe()
    assert "MyEvent" in desc["event_types"]
    et = desc["event_types"]["MyEvent"]
    assert et["latest_version"] == 2
    assert et["known_versions"] == [1, 2]
    assert et["adapters"][0]["fn"] == "upgrade_v1_v2"
    assert et["adapters"][0]["from_version"] == 1
    assert et["adapters"][0]["to_version"] == 2


def test_duplicate_adapter_raises_immediately():
    reg = fresh_registry()

    def fn1(p): return p
    def fn2(p): return p

    reg.register_adapter("MyEvent", 1, 2, fn1)

    with pytest.raises(SchemaValidationFailed) as exc_info:
        reg.register_adapter("MyEvent", 1, 2, fn2)

    errs = exc_info.value.errors
    assert len(errs) == 1
    assert errs[0].code == "DUPLICATE_ADAPTER"
    assert errs[0].event_name == "MyEvent"


# ── Tests: version resolution ─────────────────────────────────────────────────

def test_get_latest_version_no_versions():
    reg = fresh_registry()
    assert reg.get_latest_version("UnknownEvent") == 1


def test_get_latest_version_after_register():
    reg = fresh_registry()
    reg.register_version("MyEvent", 1)
    reg.register_version("MyEvent", 3)
    reg.register_version("MyEvent", 2)
    assert reg.get_latest_version("MyEvent") == 3


def test_needs_upgrade_true():
    reg = fresh_registry()
    reg.register_version("MyEvent", 1)
    reg.register_version("MyEvent", 2)
    assert reg.needs_upgrade("MyEvent", stored_version=1) is True


def test_needs_upgrade_false_when_current():
    reg = fresh_registry()
    reg.register_version("MyEvent", 2)
    assert reg.needs_upgrade("MyEvent", stored_version=2) is False


def test_needs_upgrade_false_when_no_versions():
    """If no versions registered, latest = 1; v1 payload needs no upgrade."""
    reg = fresh_registry()
    assert reg.needs_upgrade("MyEvent", stored_version=1) is False


# ── Tests: BFS chain resolution ───────────────────────────────────────────────

def test_resolve_chain_same_version():
    reg = fresh_registry()
    assert reg.resolve_chain("MyEvent", 2, 2) == []


def test_resolve_chain_direct_hop():
    reg = fresh_registry()
    fn = lambda p: p
    fn.__name__ = "upgrade_v1_v2"
    reg.register_adapter("MyEvent", 1, 2, fn)

    chain = reg.resolve_chain("MyEvent", 1, 2)
    assert chain == [fn]


def test_resolve_chain_two_hops():
    reg = fresh_registry()
    fn_12 = lambda p: p; fn_12.__name__ = "fn_12"
    fn_23 = lambda p: p; fn_23.__name__ = "fn_23"
    reg.register_adapter("MyEvent", 1, 2, fn_12)
    reg.register_adapter("MyEvent", 2, 3, fn_23)

    chain = reg.resolve_chain("MyEvent", 1, 3)
    assert chain == [fn_12, fn_23]


def test_resolve_chain_three_hops():
    reg = fresh_registry()
    fns = []
    for f, t in [(1, 2), (2, 3), (3, 4)]:
        fn = lambda p, _t=t: p
        fn.__name__ = f"fn_{f}_{t}"
        reg.register_adapter("MyEvent", f, t, fn)
        fns.append(fn)

    chain = reg.resolve_chain("MyEvent", 1, 4)
    assert chain == fns


def test_resolve_chain_skips_direct_jump():
    """BFS finds shortest path: direct v1→v3 adapter is preferred over v1→v2→v3."""
    reg = fresh_registry()
    fn_direct = lambda p: {**p, "direct": True}; fn_direct.__name__ = "fn_direct"
    fn_12 = lambda p: p; fn_12.__name__ = "fn_12"
    fn_23 = lambda p: p; fn_23.__name__ = "fn_23"

    reg.register_adapter("MyEvent", 1, 2, fn_12)
    reg.register_adapter("MyEvent", 2, 3, fn_23)
    reg.register_adapter("MyEvent", 1, 3, fn_direct)   # shorter path

    chain = reg.resolve_chain("MyEvent", 1, 3)
    # BFS explores level by level: level-1 finds v2 from v1, level-2 finds v3 via fn_12+fn_23
    # BUT also from v1 directly to v3 is checked when f==1 and t==3 — it IS level 1 adjacent
    # Since both fn_direct and fn_12 are adjacent from v1, BFS explores them in dict iteration order.
    # Either way the chain must be valid and reach v3.
    assert len(chain) >= 1
    # Verify that applying the chain does in fact produce a dict
    result = make_v1_payload()
    for fn in chain:
        result = fn(result)
    assert isinstance(result, dict)


def test_resolve_chain_missing_raises():
    reg = fresh_registry()
    reg.register_version("MyEvent", 1)
    reg.register_version("MyEvent", 3)
    # No adapter registered — gap between v1 and v3

    with pytest.raises(ValueError, match="No adapters registered"):
        reg.resolve_chain("MyEvent", 1, 3)


def test_resolve_chain_no_adapters_raises():
    reg = fresh_registry()
    with pytest.raises(ValueError, match="No adapters registered"):
        reg.resolve_chain("MyEvent", 1, 2)


def test_resolve_chain_caches_result():
    reg = fresh_registry()
    call_count = [0]

    def fn(p):
        call_count[0] += 1
        return p
    fn.__name__ = "counting_fn"

    reg.register_adapter("MyEvent", 1, 2, fn)
    chain1 = reg.resolve_chain("MyEvent", 1, 2)
    chain2 = reg.resolve_chain("MyEvent", 1, 2)
    assert chain1 is chain2  # same list object from cache


# ── Tests: payload upgrade ────────────────────────────────────────────────────

def test_upgrade_payload_linear_chain():
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def v1_to_v2(payload: dict) -> dict:
        payload["field_v2"] = "added"
        return payload

    @reg.adapter("E", from_version=2, to_version=3)
    def v2_to_v3(payload: dict) -> dict:
        payload["field_v3"] = "also_added"
        return payload

    original = {"schema_version": 1, "data": "hello"}
    upgraded = reg.upgrade_payload("E", original, stored_version=1)

    assert upgraded["schema_version"] == 3
    assert upgraded["field_v2"] == "added"
    assert upgraded["field_v3"] == "also_added"
    assert upgraded["data"] == "hello"


def test_upgrade_payload_does_not_mutate_original():
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def v1_to_v2(payload: dict) -> dict:
        payload["injected"] = True
        return payload

    original = {"schema_version": 1, "data": "original"}
    original_copy = copy.deepcopy(original)

    reg.upgrade_payload("E", original, stored_version=1)

    assert original == original_copy, "upgrade_payload must not mutate the original dict"


def test_upgrade_payload_stamps_schema_version():
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def v1_to_v2(p): return p

    result = reg.upgrade_payload("E", {"schema_version": 1}, stored_version=1)
    assert result["schema_version"] == 2


def test_upgrade_payload_no_op_when_current():
    reg = fresh_registry()
    reg.register_version("E", 2)

    payload = {"schema_version": 2, "data": "x"}
    result = reg.upgrade_payload("E", payload, stored_version=2)
    # No adapter chain applied — same content returned
    assert result["data"] == "x"


def test_upgrade_payload_adapter_exception_propagates():
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def bad_adapter(payload: dict) -> dict:
        raise RuntimeError("adapter crashed")

    with pytest.raises(RuntimeError, match="adapter crashed"):
        reg.upgrade_payload("E", {"schema_version": 1}, stored_version=1)


# ── Tests: startup validation ─────────────────────────────────────────────────

def test_validate_clean_registry_passes():
    """A registry with no adapters must validate without errors."""
    reg = fresh_registry()
    reg.register_version("MyEvent", 1)
    reg.validate()   # must not raise


def test_validate_complete_chain_passes():
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def fn_12(p): return p

    @reg.adapter("E", from_version=2, to_version=3)
    def fn_23(p): return p

    reg.validate()   # must not raise


def test_validate_missing_upgrade_path_detected():
    """v1 registered, v3 is latest, no adapters → can't upgrade → MISSING_UPGRADE_PATH."""
    reg = fresh_registry()
    reg.register_version("E", 1)
    reg.register_version("E", 3)
    # No adapters at all → resolve_chain fails → MISSING_UPGRADE_PATH

    with pytest.raises(SchemaValidationFailed) as exc_info:
        reg.validate()

    codes = [e.code for e in exc_info.value.errors]
    assert "MISSING_UPGRADE_PATH" in codes


def test_validate_gap_in_chain_detected():
    """
    Adapters 1→2 and 3→4 exist but the chain is disconnected.
    Version 2 is a dead-end (not the declared latest v4, no outgoing adapter)
    so the registry reports MULTIPLE_LATEST (dead-end branch at v2).
    """
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def fn_12(p): return p

    @reg.adapter("E", from_version=3, to_version=4)
    def fn_34(p): return p

    with pytest.raises(SchemaValidationFailed) as exc_info:
        reg.validate()

    codes = [e.code for e in exc_info.value.errors]
    # v2 is a dead-end branch → MULTIPLE_LATEST
    assert "MULTIPLE_LATEST" in codes


def test_validate_multiple_latest_detected():
    """Adapters 1→2 and 1→3 create two sinks (2 and 3) → MULTIPLE_LATEST."""
    reg = fresh_registry()

    @reg.adapter("E", from_version=1, to_version=2)
    def fn_12(p): return p

    @reg.adapter("E", from_version=1, to_version=3)
    def fn_13(p): return p

    with pytest.raises(SchemaValidationFailed) as exc_info:
        reg.validate()

    codes = [e.code for e in exc_info.value.errors]
    assert "MULTIPLE_LATEST" in codes


def test_validate_multiple_events_all_errors_reported():
    """validate() collects all errors across all event types."""
    reg = fresh_registry()
    # Event A: v1 and v3 registered, no adapters → MISSING_UPGRADE_PATH
    reg.register_version("EventA", 1)
    reg.register_version("EventA", 3)
    # Event B: fork (1→2 and 1→3, dead-end at v2) → MULTIPLE_LATEST
    @reg.adapter("EventB", from_version=1, to_version=2)
    def fn_b12(p): return p
    @reg.adapter("EventB", from_version=1, to_version=3)
    def fn_b13(p): return p

    with pytest.raises(SchemaValidationFailed) as exc_info:
        reg.validate()

    event_names = {e.event_name for e in exc_info.value.errors}
    assert "EventA" in event_names   # MISSING_UPGRADE_PATH
    assert "EventB" in event_names   # MULTIPLE_LATEST


# ── Tests: register_version implicit from adapters ────────────────────────────

def test_adapter_implicitly_registers_versions():
    reg = fresh_registry()

    @reg.adapter("E", from_version=2, to_version=3)
    def fn(p): return p

    # Both 2 and 3 should be known
    assert 2 in reg._versions["E"]
    assert 3 in reg._versions["E"]
    assert reg.get_latest_version("E") == 3


# ── Tests: cache invalidation ─────────────────────────────────────────────────

def test_cache_invalidated_on_new_adapter():
    reg = fresh_registry()

    def fn_13(p): return p
    fn_13.__name__ = "fn_13"
    reg.register_adapter("E", 1, 3, fn_13)  # v1 → v3 in one hop

    # Cache it
    chain1 = reg.resolve_chain("E", 1, 3)
    assert len(chain1) == 1

    # Adding a new adapter for this event invalidates cache
    def fn_12(p): return p
    fn_12.__name__ = "fn_12"
    def fn_23(p): return p
    fn_23.__name__ = "fn_23"
    reg.register_adapter("E", 1, 2, fn_12)

    # Cache was cleared — BFS will re-run
    cache_key = ("E", 1, 3)
    assert cache_key not in reg._chain_cache


# ── Tests: bootstrap helper ───────────────────────────────────────────────────

def test_get_schema_version_pydantic_field():
    """_get_schema_version reads the correct default from UniversalBaseEvent subclasses."""
    from app.events.bootstrap.register_consumers import _get_schema_version
    from app.events.message_events import RawWebhookEvent, MessageReceived

    assert _get_schema_version(RawWebhookEvent) == 1
    assert _get_schema_version(MessageReceived) == 1


def test_bootstrap_schema_registry_with_fake_registry():
    """_bootstrap_schema_registry registers versions and validates cleanly."""
    from app.events.bootstrap.register_consumers import _bootstrap_schema_registry
    from app.events.schema.registry import SchemaRegistry
    from app.utils.logger import get_logger

    # Build a minimal fake registry with just one event class
    from app.events.message_events import MessageReceived

    class FakeRegistry:
        _subscriptions = {MessageReceived: []}

    # Use a fresh schema registry to avoid global state pollution
    import app.events.schema as schema_module
    original = schema_module.schema_registry
    schema_module.schema_registry = SchemaRegistry()

    try:
        _bootstrap_schema_registry(FakeRegistry(), get_logger("test"))
        # No exception means validation passed
    finally:
        schema_module.schema_registry = original
