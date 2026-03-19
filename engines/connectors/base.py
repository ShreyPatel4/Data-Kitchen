"""Base classes for Nova connectors.

Two families:
- PullConnector: for APIs and files (batch extraction)
- CDCConnector: for databases with change data capture (streaming)

Connectors are decoupled from the ORM — they use plain dataclasses
so they can run in the data plane agent without importing API code.
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColumnSchema:
    name: str
    data_type: str  # Iceberg-compatible type string
    nullable: bool = True
    is_pii: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class TableSchema:
    name: str
    columns: list[ColumnSchema]
    primary_key: list[str] = field(default_factory=list)
    row_count_estimate: int | None = None


@dataclass
class ExtractBatch:
    records: list[dict]
    schema: TableSchema
    source_table: str
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    is_last: bool = False


@dataclass
class ConnectorMetrics:
    rows_extracted: int = 0
    bytes_extracted: int = 0
    tables_discovered: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    rate_limit_waits: int = 0


@dataclass
class ConnectorConfig:
    id: str
    name: str
    source_type: str
    config: dict = field(default_factory=dict)
    credentials: dict = field(default_factory=dict)
    batch_size: int = 10_000
    max_retries: int = 3
    rate_limit_rps: float | None = None


class PullConnector(ABC):
    """Base class for batch/pull-based connectors (APIs, files)."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.metrics = ConnectorMetrics()

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the source."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the source."""

    @abstractmethod
    async def discover_schema(self) -> list[TableSchema]:
        """Introspect source and return available table schemas."""

    @abstractmethod
    async def extract_table(
        self,
        table: str,
        since: datetime | None = None,
    ) -> AsyncIterator[ExtractBatch]:
        """Extract data from a single table, yielding batches."""
        yield  # type: ignore[misc]

    async def health_check(self) -> bool:
        """Check if the source is reachable."""
        try:
            await self.connect()
            await self.disconnect()
            return True
        except Exception:
            return False

    def build_openlineage_event(
        self, table: str, batch: ExtractBatch
    ) -> dict:
        """Build an OpenLineage RunEvent for this extraction."""
        return {
            "eventType": "COMPLETE",
            "eventTime": batch.extracted_at.isoformat() + "Z",
            "producer": f"nova-connector-{self.config.source_type}",
            "run": {"runId": batch.batch_id},
            "job": {
                "namespace": "nova",
                "name": (
                    f"extract.{self.config.source_type}.{table}"
                ),
            },
            "inputs": [
                {
                    "namespace": self.config.source_type,
                    "name": table,
                    "facets": {
                        "schema": {
                            "fields": [
                                {
                                    "name": c.name,
                                    "type": c.data_type,
                                }
                                for c in batch.schema.columns
                            ]
                        }
                    },
                }
            ],
            "outputs": [
                {
                    "namespace": "nova-lakehouse",
                    "name": f"raw.{table}",
                }
            ],
        }


class CDCConnector(PullConnector):
    """Base class for CDC/streaming connectors (databases)."""

    @abstractmethod
    async def get_current_position(self) -> str:
        """Return the current replication position (LSN, binlog pos)."""

    @abstractmethod
    async def stream_changes(
        self,
        tables: list[str],
        from_position: str | None = None,
    ) -> AsyncIterator[ExtractBatch]:
        """Stream change events from the source."""
        yield  # type: ignore[misc]
