"""Schema evolution — detects changes and classifies them as safe or breaking.

Safe (auto-applied): add column, widen type
Breaking (requires review): remove column, rename column, narrow type
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

from engines.connectors.base import ColumnSchema, TableSchema

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    WIDEN_TYPE = "widen_type"
    NARROW_TYPE = "narrow_type"
    CHANGE_NULLABLE = "change_nullable"


class ChangeSafety(str, Enum):
    SAFE = "safe"  # Auto-apply
    BREAKING = "breaking"  # Requires human review


# Type widening rules: from_type → set of types it can safely widen to
WIDEN_RULES = {
    "int": {"long", "double", "string"},
    "long": {"double", "string"},
    "float": {"double", "string"},
    "double": {"string"},
    "boolean": {"string"},
    "date": {"timestamp", "timestamptz", "string"},
    "timestamp": {"timestamptz", "string"},
}


@dataclass
class SchemaChange:
    change_type: ChangeType
    column_name: str
    safety: ChangeSafety
    old_value: str | None = None
    new_value: str | None = None
    description: str = ""


@dataclass
class SchemaEvolutionPlan:
    table_name: str
    changes: list[SchemaChange] = field(default_factory=list)
    is_safe: bool = True

    @property
    def safe_changes(self) -> list[SchemaChange]:
        return [
            c
            for c in self.changes
            if c.safety == ChangeSafety.SAFE
        ]

    @property
    def breaking_changes(self) -> list[SchemaChange]:
        return [
            c
            for c in self.changes
            if c.safety == ChangeSafety.BREAKING
        ]


def diff_schemas(
    old: TableSchema, new: TableSchema
) -> SchemaEvolutionPlan:
    """Compare two schemas and produce an evolution plan."""
    plan = SchemaEvolutionPlan(table_name=new.name)

    old_cols = {c.name: c for c in old.columns}
    new_cols = {c.name: c for c in new.columns}

    # Added columns (safe)
    for name, col in new_cols.items():
        if name not in old_cols:
            plan.changes.append(
                SchemaChange(
                    change_type=ChangeType.ADD_COLUMN,
                    column_name=name,
                    safety=ChangeSafety.SAFE,
                    new_value=col.data_type,
                    description=(
                        f"New column '{name}' ({col.data_type})"
                    ),
                )
            )

    # Dropped columns (breaking)
    for name in old_cols:
        if name not in new_cols:
            plan.changes.append(
                SchemaChange(
                    change_type=ChangeType.DROP_COLUMN,
                    column_name=name,
                    safety=ChangeSafety.BREAKING,
                    old_value=old_cols[name].data_type,
                    description=(
                        f"Column '{name}' removed from source"
                    ),
                )
            )

    # Type changes
    for name in old_cols:
        if name in new_cols:
            old_type = old_cols[name].data_type
            new_type = new_cols[name].data_type
            if old_type != new_type:
                # Check if this is a safe widening
                safe_targets = WIDEN_RULES.get(old_type, set())
                if new_type in safe_targets:
                    plan.changes.append(
                        SchemaChange(
                            change_type=ChangeType.WIDEN_TYPE,
                            column_name=name,
                            safety=ChangeSafety.SAFE,
                            old_value=old_type,
                            new_value=new_type,
                            description=(
                                f"Type widened: "
                                f"{old_type} → {new_type}"
                            ),
                        )
                    )
                else:
                    plan.changes.append(
                        SchemaChange(
                            change_type=ChangeType.NARROW_TYPE,
                            column_name=name,
                            safety=ChangeSafety.BREAKING,
                            old_value=old_type,
                            new_value=new_type,
                            description=(
                                f"Type narrowed: "
                                f"{old_type} → {new_type}"
                            ),
                        )
                    )

            # Nullable changes
            old_null = old_cols[name].nullable
            new_null = new_cols[name].nullable
            if old_null != new_null:
                safety = (
                    ChangeSafety.SAFE
                    if new_null
                    else ChangeSafety.BREAKING
                )
                plan.changes.append(
                    SchemaChange(
                        change_type=ChangeType.CHANGE_NULLABLE,
                        column_name=name,
                        safety=safety,
                        old_value=str(old_null),
                        new_value=str(new_null),
                        description=(
                            f"Nullable changed: "
                            f"{old_null} → {new_null}"
                        ),
                    )
                )

    plan.is_safe = all(
        c.safety == ChangeSafety.SAFE for c in plan.changes
    )
    return plan


def apply_safe_changes(
    schema: TableSchema, plan: SchemaEvolutionPlan
) -> TableSchema:
    """Apply safe changes to a schema, returning the evolved schema."""
    cols = list(schema.columns)

    for change in plan.safe_changes:
        if change.change_type == ChangeType.ADD_COLUMN:
            cols.append(
                ColumnSchema(
                    name=change.column_name,
                    data_type=change.new_value or "string",
                    nullable=True,
                )
            )
        elif change.change_type == ChangeType.WIDEN_TYPE:
            for i, col in enumerate(cols):
                if col.name == change.column_name:
                    cols[i] = ColumnSchema(
                        name=col.name,
                        data_type=change.new_value or col.data_type,
                        nullable=col.nullable,
                        is_pii=col.is_pii,
                        metadata=col.metadata,
                    )
        elif change.change_type == ChangeType.CHANGE_NULLABLE:
            for i, col in enumerate(cols):
                if col.name == change.column_name:
                    cols[i] = ColumnSchema(
                        name=col.name,
                        data_type=col.data_type,
                        nullable=True,
                        is_pii=col.is_pii,
                        metadata=col.metadata,
                    )

    return TableSchema(
        name=schema.name,
        columns=cols,
        primary_key=schema.primary_key,
        row_count_estimate=schema.row_count_estimate,
    )
