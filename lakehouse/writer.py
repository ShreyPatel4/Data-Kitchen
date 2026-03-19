"""Iceberg table writer — writes ExtractBatch records to Iceberg tables on MinIO/S3.

This is the core data path: Connector → ExtractBatch → IcebergWriter → MinIO.
Trino then reads Iceberg tables directly.
"""

import logging
import uuid
from datetime import datetime

from engines.connectors.base import ExtractBatch, TableSchema

logger = logging.getLogger(__name__)


# Connector type → Iceberg type mapping
TYPE_MAP = {
    "string": "string",
    "long": "long",
    "int": "int",
    "double": "double",
    "float": "float",
    "boolean": "boolean",
    "date": "date",
    "timestamp": "timestamp",
    "timestamptz": "timestamptz",
    "decimal": "decimal(38,18)",
    "binary": "binary",
}


def _to_iceberg_type(connector_type: str) -> str:
    return TYPE_MAP.get(connector_type, "string")


class IcebergWriter:
    """Writes data batches to Iceberg tables stored on S3/MinIO.

    Uses PyIceberg when available, falls back to Parquet files
    with Iceberg-compatible naming for MVP.
    """

    def __init__(
        self,
        warehouse_path: str = "s3://warehouse/",
        s3_endpoint: str = "http://localhost:9000",
        s3_access_key: str = "minioadmin",
        s3_secret_key: str = "minioadmin",
    ):
        self.warehouse_path = warehouse_path
        self.s3_endpoint = s3_endpoint
        self.s3_access_key = s3_access_key
        self.s3_secret_key = s3_secret_key
        self._catalog = None

    async def initialize(self) -> None:
        """Initialize the Iceberg catalog connection."""
        try:
            from pyiceberg.catalog.sql import SqlCatalog

            self._catalog = SqlCatalog(
                "nova",
                **{
                    "uri": "sqlite:///iceberg_catalog.db",
                    "warehouse": self.warehouse_path,
                    "s3.endpoint": self.s3_endpoint,
                    "s3.access-key-id": self.s3_access_key,
                    "s3.secret-access-key": self.s3_secret_key,
                },
            )
            logger.info("PyIceberg catalog initialized")
        except ImportError:
            logger.warning(
                "PyIceberg not installed, using Parquet fallback"
            )

    async def create_table(
        self,
        namespace: str,
        table_name: str,
        schema: TableSchema,
    ) -> str:
        """Create an Iceberg table from a TableSchema.

        Returns the table location.
        """
        if self._catalog:
            return await self._create_iceberg_table(
                namespace, table_name, schema
            )
        return await self._create_parquet_fallback(
            namespace, table_name, schema
        )

    async def write_batch(
        self,
        namespace: str,
        table_name: str,
        batch: ExtractBatch,
    ) -> int:
        """Write an ExtractBatch to an Iceberg table. Returns rows written."""
        if not batch.records:
            return 0

        if self._catalog:
            return await self._write_iceberg(
                namespace, table_name, batch
            )
        return await self._write_parquet_fallback(
            namespace, table_name, batch
        )

    async def evolve_schema(
        self,
        namespace: str,
        table_name: str,
        new_schema: TableSchema,
        old_schema: TableSchema,
    ) -> list[str]:
        """Evolve table schema for additive changes.

        Returns list of changes applied.
        """
        changes = []
        old_col_names = {c.name for c in old_schema.columns}

        for col in new_schema.columns:
            if col.name not in old_col_names:
                changes.append(
                    f"ADD COLUMN {col.name} "
                    f"{_to_iceberg_type(col.data_type)}"
                )

        if changes and self._catalog:
            try:
                table = self._catalog.load_table(
                    f"{namespace}.{table_name}"
                )
                with table.update_schema() as update:
                    for col in new_schema.columns:
                        if col.name not in old_col_names:
                            iceberg_type = _to_iceberg_type(
                                col.data_type
                            )
                            update.add_column(
                                col.name,
                                iceberg_type,
                                required=not col.nullable,
                            )
                logger.info(
                    f"Schema evolved for {namespace}.{table_name}: "
                    f"{changes}"
                )
            except Exception as e:
                logger.error(f"Schema evolution failed: {e}")
                raise

        return changes

    async def _create_iceberg_table(
        self,
        namespace: str,
        table_name: str,
        schema: TableSchema,
    ) -> str:
        """Create table using PyIceberg."""
        from pyiceberg.schema import Schema
        from pyiceberg.types import (
            BooleanType,
            DateType,
            DoubleType,
            FloatType,
            IntegerType,
            LongType,
            NestedField,
            StringType,
            TimestampType,
            TimestamptzType,
        )

        type_map = {
            "string": StringType(),
            "long": LongType(),
            "int": IntegerType(),
            "double": DoubleType(),
            "float": FloatType(),
            "boolean": BooleanType(),
            "date": DateType(),
            "timestamp": TimestampType(),
            "timestamptz": TimestamptzType(),
        }

        fields = []
        for i, col in enumerate(schema.columns, start=1):
            iceberg_type = type_map.get(
                col.data_type, StringType()
            )
            fields.append(
                NestedField(
                    field_id=i,
                    name=col.name,
                    field_type=iceberg_type,
                    required=not col.nullable,
                )
            )

        iceberg_schema = Schema(*fields)

        try:
            self._catalog.create_namespace_if_not_exists(namespace)
        except Exception:
            pass

        table = self._catalog.create_table(
            f"{namespace}.{table_name}",
            schema=iceberg_schema,
        )
        location = str(table.location())
        logger.info(f"Created Iceberg table at {location}")
        return location

    async def _write_iceberg(
        self,
        namespace: str,
        table_name: str,
        batch: ExtractBatch,
    ) -> int:
        """Write batch using PyIceberg."""
        import pyarrow as pa

        table = self._catalog.load_table(
            f"{namespace}.{table_name}"
        )

        # Convert records to PyArrow table
        columns = {
            col.name: [r.get(col.name) for r in batch.records]
            for col in batch.schema.columns
        }
        arrow_table = pa.table(columns)

        table.append(arrow_table)
        count = len(batch.records)
        logger.info(
            f"Wrote {count} rows to {namespace}.{table_name}"
        )
        return count

    async def _create_parquet_fallback(
        self,
        namespace: str,
        table_name: str,
        schema: TableSchema,
    ) -> str:
        """Create table directory structure (no PyIceberg)."""
        location = (
            f"{self.warehouse_path}{namespace}/{table_name}"
        )
        logger.info(
            f"Parquet fallback: table location {location}"
        )
        return location

    async def _write_parquet_fallback(
        self,
        namespace: str,
        table_name: str,
        batch: ExtractBatch,
    ) -> int:
        """Write batch as Parquet file (no PyIceberg)."""
        try:
            import io

            import boto3
            import pyarrow as pa
            import pyarrow.parquet as pq

            columns = {
                col.name: [
                    r.get(col.name) for r in batch.records
                ]
                for col in batch.schema.columns
            }
            arrow_table = pa.table(columns)

            buf = io.BytesIO()
            pq.write_table(arrow_table, buf)
            buf.seek(0)

            s3 = boto3.client(
                "s3",
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
            )

            file_id = str(uuid.uuid4())[:8]
            key = (
                f"{namespace}/{table_name}/data/"
                f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                f"_{file_id}.parquet"
            )
            s3.put_object(
                Bucket="warehouse", Key=key, Body=buf.read()
            )
            count = len(batch.records)
            logger.info(
                f"Wrote {count} rows to s3://warehouse/{key}"
            )
            return count
        except ImportError as e:
            logger.error(
                f"pyarrow/boto3 needed for parquet fallback: {e}"
            )
            return 0
