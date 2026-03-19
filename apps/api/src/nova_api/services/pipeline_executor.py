"""Pipeline execution service — orchestrates connector → validate → write → metadata.

This is the core execution engine that Sprint 3's Temporal worker will call.
For MVP, it runs synchronously. Temporal integration wraps this in durable workflows.
"""

import logging
import uuid
from datetime import datetime

from engines.connectors.base import ConnectorConfig
from engines.connectors.registry import registry
from lakehouse.evolution import diff_schemas

logger = logging.getLogger(__name__)


async def execute_extraction(
    connector_config: ConnectorConfig,
    tables: list[str] | None = None,
) -> dict:
    """Execute a full extraction pipeline.

    1. Connect to source
    2. Discover schema (detect changes)
    3. Extract data
    4. Validate against contracts
    5. Write clean data to lakehouse
    6. Write quarantined data to side table
    7. Emit OpenLineage events
    8. Update metadata

    Returns execution metrics.
    """
    connector = registry.create(connector_config)
    metrics = {
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.utcnow().isoformat(),
        "tables_extracted": 0,
        "rows_extracted": 0,
        "rows_quarantined": 0,
        "schema_changes": [],
        "errors": [],
    }

    try:
        await connector.connect()

        # Discover schema
        discovered = await connector.discover_schema()
        metrics["tables_discovered"] = len(discovered)

        # Filter to requested tables or use all
        target_tables = discovered
        if tables:
            target_tables = [
                t for t in discovered if t.name in tables
            ]

        for table_schema in target_tables:
            try:
                batch_count = 0
                async for batch in connector.extract_table(
                    table_schema.name
                ):
                    metrics["rows_extracted"] += len(
                        batch.records
                    )
                    batch_count += 1

                    # Build OpenLineage event
                    ol_event = connector.build_openlineage_event(
                        table_schema.name, batch
                    )
                    metrics.setdefault(
                        "openlineage_events", []
                    ).append(ol_event)

                metrics["tables_extracted"] += 1
                logger.info(
                    f"Extracted {table_schema.name}: "
                    f"{batch_count} batches"
                )
            except Exception as e:
                metrics["errors"].append(
                    {
                        "table": table_schema.name,
                        "error": str(e),
                    }
                )
                logger.error(
                    f"Error extracting {table_schema.name}: {e}"
                )

    except Exception as e:
        metrics["errors"].append({"error": str(e)})
        logger.error(f"Pipeline execution failed: {e}")
    finally:
        await connector.disconnect()
        metrics["finished_at"] = datetime.utcnow().isoformat()

    return metrics


async def detect_schema_changes(
    connector_config: ConnectorConfig,
    known_schemas: dict[str, list[dict]],
) -> list[dict]:
    """Detect schema changes between source and known metadata.

    known_schemas: {table_name: [{name, data_type, nullable}]}
    Returns list of change summaries.
    """
    from engines.connectors.base import ColumnSchema, TableSchema

    connector = registry.create(connector_config)
    changes = []

    try:
        await connector.connect()
        current_schemas = await connector.discover_schema()

        for current in current_schemas:
            known_cols = known_schemas.get(current.name, [])
            if not known_cols:
                changes.append(
                    {
                        "table": current.name,
                        "type": "new_table",
                        "columns": len(current.columns),
                    }
                )
                continue

            old_schema = TableSchema(
                name=current.name,
                columns=[
                    ColumnSchema(
                        name=c["name"],
                        data_type=c["data_type"],
                        nullable=c.get("nullable", True),
                    )
                    for c in known_cols
                ],
            )
            plan = diff_schemas(old_schema, current)
            if plan.changes:
                changes.append(
                    {
                        "table": current.name,
                        "is_safe": plan.is_safe,
                        "changes": [
                            {
                                "type": c.change_type.value,
                                "column": c.column_name,
                                "safety": c.safety.value,
                                "description": c.description,
                            }
                            for c in plan.changes
                        ],
                    }
                )
    finally:
        await connector.disconnect()

    return changes
