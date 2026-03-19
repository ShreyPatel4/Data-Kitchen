"""Quarantine framework — routes bad rows to side tables.

When a row fails data contract validation:
1. The row is written to a quarantine table with error metadata
2. The pipeline continues processing clean rows
3. Quarantined rows can be reviewed and reprocessed
"""

import logging
from dataclasses import dataclass, field

from engines.connectors.base import ExtractBatch

logger = logging.getLogger(__name__)


@dataclass
class ContractRule:
    """A single data quality rule from a DataContract."""

    name: str
    column: str
    rule_type: str  # not_null, type_check, range, allowed_values, regex
    params: dict = field(default_factory=dict)


@dataclass
class ValidationFailure:
    """A single validation failure for one row."""

    row_index: int
    row_data: dict
    rule_name: str
    column: str
    reason: str
    contract_id: str | None = None


@dataclass
class ValidationResult:
    """Result of validating a batch against contracts."""

    clean_records: list[dict]
    failures: list[ValidationFailure]
    total_rows: int = 0
    clean_count: int = 0
    quarantine_count: int = 0


def validate_batch(
    batch: ExtractBatch,
    rules: list[ContractRule],
) -> ValidationResult:
    """Validate a batch of records against contract rules.

    Returns clean records and quarantined failures.
    """
    clean = []
    failures = []

    for i, record in enumerate(batch.records):
        row_failures = _validate_row(record, rules, i)
        if row_failures:
            failures.extend(row_failures)
        else:
            clean.append(record)

    return ValidationResult(
        clean_records=clean,
        failures=failures,
        total_rows=len(batch.records),
        clean_count=len(clean),
        quarantine_count=len(failures),
    )


def _validate_row(
    record: dict,
    rules: list[ContractRule],
    row_index: int,
) -> list[ValidationFailure]:
    """Validate a single row against all rules."""
    failures = []

    for rule in rules:
        value = record.get(rule.column)
        failure = _check_rule(record, rule, value, row_index)
        if failure:
            failures.append(failure)

    return failures


def _check_rule(
    record: dict,
    rule: ContractRule,
    value,
    row_index: int,
) -> ValidationFailure | None:
    """Check a single rule against a value."""

    if rule.rule_type == "not_null":
        if value is None or value == "":
            return ValidationFailure(
                row_index=row_index,
                row_data=record,
                rule_name=rule.name,
                column=rule.column,
                reason=f"Column '{rule.column}' is null/empty",
            )

    elif rule.rule_type == "range":
        if value is not None:
            try:
                num_val = float(value)
                min_val = rule.params.get("min")
                max_val = rule.params.get("max")
                if min_val is not None and num_val < float(
                    min_val
                ):
                    return ValidationFailure(
                        row_index=row_index,
                        row_data=record,
                        rule_name=rule.name,
                        column=rule.column,
                        reason=(
                            f"Value {num_val} below min {min_val}"
                        ),
                    )
                if max_val is not None and num_val > float(
                    max_val
                ):
                    return ValidationFailure(
                        row_index=row_index,
                        row_data=record,
                        rule_name=rule.name,
                        column=rule.column,
                        reason=(
                            f"Value {num_val} above max {max_val}"
                        ),
                    )
            except (ValueError, TypeError):
                return ValidationFailure(
                    row_index=row_index,
                    row_data=record,
                    rule_name=rule.name,
                    column=rule.column,
                    reason=(
                        f"Cannot convert '{value}' to number "
                        f"for range check"
                    ),
                )

    elif rule.rule_type == "allowed_values":
        allowed = rule.params.get("values", [])
        if value not in allowed:
            return ValidationFailure(
                row_index=row_index,
                row_data=record,
                rule_name=rule.name,
                column=rule.column,
                reason=(
                    f"Value '{value}' not in allowed values: "
                    f"{allowed}"
                ),
            )

    elif rule.rule_type == "type_check":
        expected = rule.params.get("expected_type", "string")
        if not _type_check(value, expected):
            return ValidationFailure(
                row_index=row_index,
                row_data=record,
                rule_name=rule.name,
                column=rule.column,
                reason=(
                    f"Value '{value}' is not of type "
                    f"'{expected}'"
                ),
            )

    return None


def _type_check(value, expected_type: str) -> bool:
    """Check if a value matches the expected type."""
    if value is None:
        return True  # Nullability is handled by not_null rule

    try:
        if expected_type in ("int", "long"):
            int(value)
        elif expected_type in ("float", "double"):
            float(value)
        elif expected_type == "boolean":
            if str(value).lower() not in (
                "true",
                "false",
                "0",
                "1",
            ):
                return False
        return True
    except (ValueError, TypeError):
        return False


def split_batch(
    batch: ExtractBatch,
    result: ValidationResult,
) -> tuple[ExtractBatch, ExtractBatch]:
    """Split a batch into clean and quarantine batches."""
    clean_batch = ExtractBatch(
        records=result.clean_records,
        schema=batch.schema,
        source_table=batch.source_table,
        batch_id=f"{batch.batch_id}_clean",
        extracted_at=batch.extracted_at,
        is_last=batch.is_last,
    )
    quarantine_batch = ExtractBatch(
        records=[f.row_data for f in result.failures],
        schema=batch.schema,
        source_table=f"{batch.source_table}_quarantine",
        batch_id=f"{batch.batch_id}_quarantine",
        extracted_at=batch.extracted_at,
        is_last=batch.is_last,
    )
    return clean_batch, quarantine_batch
