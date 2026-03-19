"""Tests for schema evolution detection and handling."""

from engines.connectors.base import ColumnSchema, TableSchema
from lakehouse.evolution import (
    ChangeSafety,
    ChangeType,
    apply_safe_changes,
    diff_schemas,
)


def _schema(name, cols):
    return TableSchema(
        name=name,
        columns=[
            ColumnSchema(name=n, data_type=t, nullable=nl)
            for n, t, nl in cols
        ],
    )


def test_no_changes():
    old = _schema("t", [("id", "long", False), ("name", "string", True)])
    new = _schema("t", [("id", "long", False), ("name", "string", True)])
    plan = diff_schemas(old, new)
    assert len(plan.changes) == 0
    assert plan.is_safe


def test_add_column_is_safe():
    old = _schema("t", [("id", "long", False)])
    new = _schema(
        "t", [("id", "long", False), ("email", "string", True)]
    )
    plan = diff_schemas(old, new)
    assert len(plan.changes) == 1
    assert plan.changes[0].change_type == ChangeType.ADD_COLUMN
    assert plan.changes[0].safety == ChangeSafety.SAFE
    assert plan.is_safe


def test_drop_column_is_breaking():
    old = _schema(
        "t", [("id", "long", False), ("email", "string", True)]
    )
    new = _schema("t", [("id", "long", False)])
    plan = diff_schemas(old, new)
    assert len(plan.changes) == 1
    assert plan.changes[0].change_type == ChangeType.DROP_COLUMN
    assert plan.changes[0].safety == ChangeSafety.BREAKING
    assert not plan.is_safe


def test_widen_type_is_safe():
    old = _schema("t", [("amount", "int", True)])
    new = _schema("t", [("amount", "long", True)])
    plan = diff_schemas(old, new)
    assert len(plan.changes) == 1
    assert plan.changes[0].change_type == ChangeType.WIDEN_TYPE
    assert plan.changes[0].safety == ChangeSafety.SAFE
    assert plan.is_safe


def test_narrow_type_is_breaking():
    old = _schema("t", [("amount", "double", True)])
    new = _schema("t", [("amount", "int", True)])
    plan = diff_schemas(old, new)
    assert len(plan.changes) == 1
    assert plan.changes[0].change_type == ChangeType.NARROW_TYPE
    assert plan.changes[0].safety == ChangeSafety.BREAKING


def test_mixed_safe_and_breaking():
    old = _schema(
        "t",
        [
            ("id", "long", False),
            ("old_col", "string", True),
            ("amount", "int", True),
        ],
    )
    new = _schema(
        "t",
        [
            ("id", "long", False),
            ("amount", "long", True),
            ("new_col", "string", True),
        ],
    )
    plan = diff_schemas(old, new)
    assert not plan.is_safe
    assert len(plan.safe_changes) == 2  # add + widen
    assert len(plan.breaking_changes) == 1  # drop


def test_apply_safe_changes():
    old = _schema("t", [("id", "long", False)])
    new = _schema(
        "t",
        [
            ("id", "long", False),
            ("email", "string", True),
            ("age", "int", True),
        ],
    )
    plan = diff_schemas(old, new)
    evolved = apply_safe_changes(old, plan)
    col_names = [c.name for c in evolved.columns]
    assert "email" in col_names
    assert "age" in col_names
    assert len(evolved.columns) == 3
