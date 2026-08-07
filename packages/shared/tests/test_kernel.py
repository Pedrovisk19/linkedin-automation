"""Testes do kernel: TypedId, Entity, AggregateRoot, Timestamps."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.kernel import (
    AggregateRoot,
    Entity,
    TenantId,
    UserId,
    utcnow,
)


def test_typed_id_new_generates_distinct_uuids() -> None:
    a, b = TenantId.new(), TenantId.new()
    assert a != b
    assert str(a) != str(b)


def test_typed_id_accepts_str_and_uuid() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    tid = TenantId(raw)
    assert str(tid) == raw
    assert tid == TenantId(raw)


def test_typed_id_distinct_types_never_equal() -> None:
    uid_str = "12345678-1234-5678-1234-567812345678"
    assert TenantId(uid_str) != UserId(uid_str)


def test_typed_id_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        TenantId("not-a-uuid")


def test_typed_id_ordering() -> None:
    a = TenantId("00000000-0000-0000-0000-000000000001")
    b = TenantId("00000000-0000-0000-0000-000000000002")
    assert a < b
    assert not (b < a)


def test_typed_id_hash_stable() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    assert hash(TenantId(raw)) == hash(TenantId(raw))


def test_entity_equality_by_id() -> None:
    @dataclass(eq=False)
    class Foo(Entity):
        pass

    tid = TenantId.new()
    assert Foo(id=tid) == Foo(id=tid)
    assert Foo(id=TenantId.new()) != Foo(id=TenantId.new())


def test_aggregate_root_records_and_pulls_events() -> None:
    @dataclass(frozen=True)
    class FooCreated(DomainEvent):
        pass

    @dataclass(eq=False)
    class Foo(AggregateRoot):
        pass

    agg = Foo(id=UserId.new())
    ev = FooCreated()
    agg.record_event(ev)

    pulled = agg.pull_events()
    assert pulled == [ev]
    assert agg.pending_events == ()
    assert agg.pull_events() == []


def test_timestamps_touch_cannot_retrocede() -> None:
    from developer_brain_ai_shared.kernel import Timestamps

    now = utcnow()
    ts = Timestamps(created_at=now, updated_at=now)
    with pytest.raises(ValueError):
        ts.touch(at=now.replace(second=now.second - 1))