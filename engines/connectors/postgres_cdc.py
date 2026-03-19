"""PostgreSQL CDC connector using logical replication.

Uses native PostgreSQL logical replication for development.
For production, Debezium via Kafka Connect is recommended.
"""

import json
import logging
from collections.abc import AsyncIterator

from engines.connectors.base import (
    CDCConnector,
    ColumnSchema,
    ConnectorConfig,
    ExtractBatch,
    TableSchema,
)

logger = logging.getLogger(__name__)

# PostgreSQL → Iceberg type mapping
PG_TYPE_MAP = {
    "smallint": "int",
    "integer": "int",
    "bigint": "long",
    "real": "float",
    "double precision": "double",
    "numeric": "decimal",
    "boolean": "boolean",
    "character varying": "string",
    "varchar": "string",
    "character": "string",
    "char": "string",
    "text": "string",
    "bytea": "binary",
    "date": "date",
    "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz",
    "time without time zone": "time",
    "time with time zone": "time",
    "uuid": "string",
    "json": "string",
    "jsonb": "string",
    "inet": "string",
    "cidr": "string",
    "macaddr": "string",
    "interval": "string",
    "point": "string",
    "line": "string",
    "polygon": "string",
    "array": "string",
    "USER-DEFINED": "string",
}


def map_pg_type(pg_type: str) -> str:
    """Map a PostgreSQL type to an Iceberg-compatible type."""
    # Handle parameterized types like varchar(255), numeric(10,2)
    base_type = pg_type.split("(")[0].strip().lower()
    return PG_TYPE_MAP.get(base_type, "string")


class PostgresCDCConnector(CDCConnector):
    """PostgreSQL CDC connector using logical replication."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._conn = None
        self._slot_name = f"nova_{config.id.replace('-', '_')}"
        self._publication_name = f"nova_pub_{config.id.replace('-', '_')}"

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as e:
            raise ImportError(
                "asyncpg is required for PostgresCDCConnector"
            ) from e

        self._conn = await asyncpg.connect(
            host=self.config.config.get("host", "localhost"),
            port=self.config.config.get("port", 5432),
            database=self.config.config.get("database", "postgres"),
            user=self.config.credentials.get("username", "postgres"),
            password=self.config.credentials.get("password", "postgres"),
        )

    async def disconnect(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def discover_schema(self) -> list[TableSchema]:
        if not self._conn:
            raise RuntimeError("Not connected")

        schemas_to_scan = self.config.config.get(
            "schemas", ["public"]
        )
        tables = []

        for schema in schemas_to_scan:
            rows = await self._conn.fetch(
                """
                SELECT c.table_name, c.column_name, c.data_type,
                       c.is_nullable, c.ordinal_position
                FROM information_schema.columns c
                WHERE c.table_schema = $1
                  AND c.table_name NOT LIKE 'pg_%'
                ORDER BY c.table_name, c.ordinal_position
                """,
                schema,
            )

            # Get primary keys
            pk_rows = await self._conn.fetch(
                """
                SELECT tc.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = $1
                  AND tc.constraint_type = 'PRIMARY KEY'
                """,
                schema,
            )
            pk_map: dict[str, list[str]] = {}
            for pk_row in pk_rows:
                pk_map.setdefault(pk_row["table_name"], []).append(
                    pk_row["column_name"]
                )

            # Get row count estimates
            count_rows = await self._conn.fetch(
                """
                SELECT relname, reltuples::bigint AS estimate
                FROM pg_class
                JOIN pg_namespace ON pg_namespace.oid = relnamespace
                WHERE nspname = $1 AND relkind = 'r'
                """,
                schema,
            )
            count_map = {
                r["relname"]: r["estimate"] for r in count_rows
            }

            # Group by table
            current_table: str | None = None
            current_columns: list[ColumnSchema] = []

            for row in rows:
                if row["table_name"] != current_table:
                    if current_table and current_columns:
                        tables.append(
                            TableSchema(
                                name=f"{schema}.{current_table}",
                                columns=current_columns,
                                primary_key=pk_map.get(
                                    current_table, []
                                ),
                                row_count_estimate=count_map.get(
                                    current_table
                                ),
                            )
                        )
                    current_table = row["table_name"]
                    current_columns = []

                current_columns.append(
                    ColumnSchema(
                        name=row["column_name"],
                        data_type=map_pg_type(row["data_type"]),
                        nullable=row["is_nullable"] == "YES",
                    )
                )

            # Don't forget the last table
            if current_table and current_columns:
                tables.append(
                    TableSchema(
                        name=f"{schema}.{current_table}",
                        columns=current_columns,
                        primary_key=pk_map.get(current_table, []),
                        row_count_estimate=count_map.get(
                            current_table
                        ),
                    )
                )

        self.metrics.tables_discovered = len(tables)
        return tables

    async def get_current_position(self) -> str:
        if not self._conn:
            raise RuntimeError("Not connected")
        row = await self._conn.fetchrow(
            "SELECT pg_current_wal_lsn()::text AS lsn"
        )
        return row["lsn"]

    async def stream_changes(
        self,
        tables: list[str],
        from_position: str | None = None,
    ) -> AsyncIterator[ExtractBatch]:
        if not self._conn:
            raise RuntimeError("Not connected")

        # Create publication if not exists
        table_list = ", ".join(tables)
        await self._conn.execute(
            f"CREATE PUBLICATION IF NOT EXISTS "
            f"{self._publication_name} FOR TABLE {table_list}"
        )

        # Create replication slot if not exists
        try:
            await self._conn.execute(
                f"SELECT pg_create_logical_replication_slot("
                f"'{self._slot_name}', 'pgoutput')"
            )
        except Exception:
            pass  # Slot already exists

        # Poll for changes
        rows = await self._conn.fetch(
            f"SELECT * FROM "
            f"pg_logical_slot_peek_binary_changes("
            f"'{self._slot_name}', NULL, NULL, "
            f"'proto_version', '1', "
            f"'publication_names', '{self._publication_name}')"
        )

        # Group by table and yield batches
        changes_by_table: dict[str, list[dict]] = {}
        for row in rows:
            try:
                data = json.loads(row["data"])
                table_name = data.get("table", "unknown")
                changes_by_table.setdefault(table_name, []).append(
                    data
                )
            except (json.JSONDecodeError, KeyError):
                self.metrics.errors += 1
                continue

        schema_cache = {
            t.name: t for t in await self.discover_schema()
        }

        for table_name, records in changes_by_table.items():
            schema = schema_cache.get(
                table_name,
                TableSchema(name=table_name, columns=[]),
            )
            self.metrics.rows_extracted += len(records)
            yield ExtractBatch(
                records=records,
                schema=schema,
                source_table=table_name,
                is_last=True,
            )

    async def health_check(self) -> bool:
        try:
            await self.connect()
            # Verify wal_level=logical
            row = await self._conn.fetchrow("SHOW wal_level")
            is_logical = row[0] == "logical"
            await self.disconnect()
            return is_logical
        except Exception:
            return False
