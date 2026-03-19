"""Tests for quarantine framework."""

from engines.connectors.base import ColumnSchema, ExtractBatch, TableSchema
from lakehouse.quarantine import (
    ContractRule,
    split_batch,
    validate_batch,
)


def _make_batch(records):
    return ExtractBatch(
        records=records,
        schema=TableSchema(
            name="test",
            columns=[
                ColumnSchema(name="id", data_type="long"),
                ColumnSchema(name="name", data_type="string"),
                ColumnSchema(name="age", data_type="int"),
                ColumnSchema(name="status", data_type="string"),
            ],
        ),
        source_table="test",
    )


def test_all_clean():
    batch = _make_batch(
        [{"id": 1, "name": "Alice", "age": 30, "status": "active"}]
    )
    rules = [
        ContractRule(
            name="age-range",
            column="age",
            rule_type="range",
            params={"min": 0, "max": 150},
        )
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    assert result.quarantine_count == 0


def test_not_null_violation():
    batch = _make_batch(
        [
            {"id": 1, "name": "Alice", "age": 30, "status": "active"},
            {"id": 2, "name": None, "age": 25, "status": "active"},
        ]
    )
    rules = [
        ContractRule(
            name="name-required",
            column="name",
            rule_type="not_null",
        )
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    assert result.quarantine_count == 1
    assert result.failures[0].column == "name"


def test_range_violation():
    batch = _make_batch(
        [
            {"id": 1, "name": "Alice", "age": 30, "status": "active"},
            {"id": 2, "name": "Bob", "age": -5, "status": "active"},
            {"id": 3, "name": "Eve", "age": 200, "status": "active"},
        ]
    )
    rules = [
        ContractRule(
            name="age-range",
            column="age",
            rule_type="range",
            params={"min": 0, "max": 150},
        )
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    assert result.quarantine_count == 2


def test_allowed_values():
    batch = _make_batch(
        [
            {"id": 1, "name": "A", "age": 30, "status": "active"},
            {"id": 2, "name": "B", "age": 25, "status": "deleted"},
        ]
    )
    rules = [
        ContractRule(
            name="valid-status",
            column="status",
            rule_type="allowed_values",
            params={"values": ["active", "inactive", "pending"]},
        )
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    assert result.quarantine_count == 1
    assert "deleted" in result.failures[0].reason


def test_type_check_violation():
    batch = _make_batch(
        [
            {"id": 1, "name": "A", "age": "30", "status": "active"},
            {"id": 2, "name": "B", "age": "not_a_number", "status": "active"},
        ]
    )
    rules = [
        ContractRule(
            name="age-is-int",
            column="age",
            rule_type="type_check",
            params={"expected_type": "int"},
        )
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    assert result.quarantine_count == 1


def test_split_batch():
    batch = _make_batch(
        [
            {"id": 1, "name": "A", "age": 30, "status": "active"},
            {"id": 2, "name": None, "age": 25, "status": "active"},
            {"id": 3, "name": "C", "age": 35, "status": "active"},
        ]
    )
    rules = [
        ContractRule(
            name="name-required",
            column="name",
            rule_type="not_null",
        )
    ]
    result = validate_batch(batch, rules)
    clean, quarantine = split_batch(batch, result)
    assert len(clean.records) == 2
    assert len(quarantine.records) == 1
    assert "quarantine" in quarantine.source_table


def test_multiple_rules():
    batch = _make_batch(
        [
            {"id": 1, "name": "A", "age": 30, "status": "active"},
            {"id": 2, "name": None, "age": -5, "status": "deleted"},
        ]
    )
    rules = [
        ContractRule(
            name="name-req", column="name", rule_type="not_null"
        ),
        ContractRule(
            name="age-range",
            column="age",
            rule_type="range",
            params={"min": 0, "max": 150},
        ),
        ContractRule(
            name="status-ok",
            column="status",
            rule_type="allowed_values",
            params={"values": ["active", "inactive"]},
        ),
    ]
    result = validate_batch(batch, rules)
    assert result.clean_count == 1
    # Row 2 fails all 3 rules
    assert result.quarantine_count == 3
