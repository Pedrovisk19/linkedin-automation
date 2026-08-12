"""Testes do Kernel extras: metodos no cobertos (clear_events, __hash__, as_uuid, lt)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from developer_brain_ai_shared.events.base import DomainEvent
from developer_brain_ai_shared.kernel import AggregateRoot, Entity, TenantId, UserId
from developer_brain_ai_shared.kernel.timestamp import Timestamps, utcnow


def test_entity_hash_stable_for_type() -> None:
    @dataclass(eq=False)
    class Foo(Entity):
        pass

    tid = UserId.new()
    a, b = Foo(id=tid), Foo(id=tid)
    assert hash(a) == hash(b)
    assert a in {b}


def test_aggregate_clear_events_zera_pendentes() -> None:
    @dataclass(frozen=True)
    class Ev(DomainEvent):
        pass

    @dataclass(eq=False)
    class Agg(AggregateRoot):
        pass

    a = Agg(id=UserId.new())
    a.record_event(Ev())
    a.clear_events()
    assert a.pending_events == ()
    assert a.pull_events() == []


def test_typed_id_lt_returns_notimplemented_for_mismatched_type() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    res = TenantId(raw).__lt__(UserId(raw))
    assert res is NotImplemented


def test_typed_id_as_uuid_roundtrips() -> None:

    raw = "12345678-1234-5678-1234-567812345678"
    assert TenantId(raw).as_uuid() == uuid.UUID(raw)


def test_typed_id_repr_format() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    assert repr(TenantId(raw)) == f"TenantId({raw})"


def test_typed_id_eq_with_other_object_returns_false() -> None:
    raw = "12345678-1234-5678-1234-567812345678"
    assert TenantId(raw) != "not-an-id"
    assert TenantId(raw) != 42


def test_typed_id_constructor_rejects_int() -> None:

    with pytest.raises(TypeError):
        TenantId(123)


def test_timestamps_touch_advances() -> None:
    now = utcnow()
    ts = Timestamps(created_at=now, updated_at=now)
    future = utcnow()
    ts2 = ts.touch(at=future)
    assert ts2.updated_at == future
    assert ts2.created_at == now
