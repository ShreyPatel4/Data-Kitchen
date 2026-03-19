"""Kafka sink — writes ExtractBatch records to Kafka topics.

Topic naming convention: nova.cdc.{source_type}.{table_name}
"""

import json
import logging

from engines.connectors.base import ConnectorConfig, ExtractBatch

logger = logging.getLogger(__name__)


class KafkaSink:
    """Writes extracted data to Kafka for downstream processing."""

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self._producer = None

    async def connect(
        self, bootstrap_servers: str = "localhost:9092"
    ) -> None:
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as e:
            raise ImportError(
                "aiokafka is required for KafkaSink"
            ) from e

        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: (
                k.encode("utf-8") if k else None
            ),
            compression_type="snappy",
            acks="all",
            enable_idempotence=True,
        )
        await self._producer.start()

    async def disconnect(self) -> None:
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def write_batch(self, batch: ExtractBatch) -> int:
        """Write a batch of records to Kafka. Returns count written."""
        if not self._producer:
            raise RuntimeError("Not connected")

        topic = self._build_topic(batch.source_table)
        pk_fields = batch.schema.primary_key
        count = 0

        for record in batch.records:
            # Build message key from primary key columns
            key = None
            if pk_fields:
                key_parts = [
                    str(record.get(f, "")) for f in pk_fields
                ]
                key = "|".join(key_parts)

            # Add Nova metadata envelope
            message = {
                "data": record,
                "_nova_metadata": {
                    "batch_id": batch.batch_id,
                    "source_table": batch.source_table,
                    "extracted_at": (
                        batch.extracted_at.isoformat()
                    ),
                },
            }

            await self._producer.send(
                topic,
                value=message,
                key=key,
                headers=[
                    (
                        "nova-batch-id",
                        batch.batch_id.encode("utf-8"),
                    ),
                    (
                        "nova-source",
                        batch.source_table.encode("utf-8"),
                    ),
                ],
            )
            count += 1

        return count

    def _build_topic(self, table_name: str) -> str:
        """Build Kafka topic name from source and table."""
        source = self.config.source_type
        # Sanitize table name for Kafka topic
        safe_table = (
            table_name.replace(".", "_").replace("-", "_")
        )
        return f"nova.cdc.{source}.{safe_table}"
