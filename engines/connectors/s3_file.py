"""S3/MinIO file connector.

Reads CSV, JSON, and Parquet files from S3-compatible storage.
Infers schema from file content.
"""

import csv
import io
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime

from engines.connectors.base import (
    ColumnSchema,
    ConnectorConfig,
    ExtractBatch,
    PullConnector,
    TableSchema,
)

logger = logging.getLogger(__name__)


def infer_type(value: str) -> str:
    """Infer Iceberg-compatible type from a string value."""
    if value is None or value == "":
        return "string"
    v = str(value).strip()
    if v.lower() in ("true", "false"):
        return "boolean"
    try:
        int(v)
        return "long"
    except ValueError:
        pass
    try:
        float(v)
        return "double"
    except ValueError:
        pass
    # Check for date/timestamp patterns
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            datetime.strptime(v, fmt)
            return "timestamp" if " " in v or "T" in v else "date"
        except ValueError:
            continue
    return "string"


def infer_schema_from_records(
    records: list[dict], table_name: str
) -> TableSchema:
    """Infer a TableSchema by sampling records."""
    if not records:
        return TableSchema(name=table_name, columns=[])

    # Sample up to 100 records for type inference
    sample = records[:100]
    type_votes: dict[str, list[str]] = {}
    for record in sample:
        for key, value in record.items():
            type_votes.setdefault(key, []).append(infer_type(value))

    # Pick the most common type per column
    columns = []
    for col_name, votes in type_votes.items():
        # Most frequent type wins, with string as fallback
        type_counts: dict[str, int] = {}
        for t in votes:
            type_counts[t] = type_counts.get(t, 0) + 1
        best_type = max(type_counts, key=type_counts.get)  # type: ignore[arg-type]
        columns.append(
            ColumnSchema(name=col_name, data_type=best_type)
        )

    return TableSchema(name=table_name, columns=columns)


class S3FileConnector(PullConnector):
    """Reads files from S3/MinIO and infers schema."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        try:
            import boto3
        except ImportError as e:
            raise ImportError(
                "boto3 is required for S3FileConnector"
            ) from e

        self._client = boto3.client(
            "s3",
            endpoint_url=self.config.config.get(
                "endpoint_url", "http://localhost:9000"
            ),
            aws_access_key_id=self.config.credentials.get(
                "access_key", "minioadmin"
            ),
            aws_secret_access_key=self.config.credentials.get(
                "secret_key", "minioadmin"
            ),
        )

    async def disconnect(self) -> None:
        self._client = None

    async def discover_schema(self) -> list[TableSchema]:
        if not self._client:
            raise RuntimeError("Not connected")

        bucket = self.config.config.get("bucket", "raw")
        prefix = self.config.config.get("prefix", "")
        file_format = self.config.config.get("format", "csv")

        response = self._client.list_objects_v2(
            Bucket=bucket, Prefix=prefix, MaxKeys=10
        )
        tables = []

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue

            # Read a sample to infer schema
            sample_records = await self._read_file(
                bucket, key, file_format, limit=100
            )
            table_name = (
                key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            )
            schema = infer_schema_from_records(
                sample_records, table_name
            )
            schema.row_count_estimate = len(sample_records)
            tables.append(schema)

        self.metrics.tables_discovered = len(tables)
        return tables

    async def extract_table(
        self,
        table: str,
        since: datetime | None = None,
    ) -> AsyncIterator[ExtractBatch]:
        if not self._client:
            raise RuntimeError("Not connected")

        bucket = self.config.config.get("bucket", "raw")
        prefix = self.config.config.get("prefix", "")
        file_format = self.config.config.get("format", "csv")

        # List matching objects
        response = self._client.list_objects_v2(
            Bucket=bucket, Prefix=prefix
        )
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue

            # Incremental: skip files older than `since`
            if since and obj["LastModified"].replace(
                tzinfo=None
            ) < since:
                continue

            records = await self._read_file(
                bucket, key, file_format
            )
            if not records:
                continue

            table_name = (
                key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            )
            schema = infer_schema_from_records(records, table_name)

            # Yield in batches
            batch_size = self.config.batch_size
            for i in range(0, len(records), batch_size):
                chunk = records[i: i + batch_size]
                self.metrics.rows_extracted += len(chunk)
                yield ExtractBatch(
                    records=chunk,
                    schema=schema,
                    source_table=table_name,
                    is_last=(i + batch_size >= len(records)),
                )

    async def _read_file(
        self,
        bucket: str,
        key: str,
        file_format: str,
        limit: int | None = None,
    ) -> list[dict]:
        """Read a file from S3 and return records."""
        response = self._client.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()

        if file_format == "csv":
            return self._parse_csv(body, limit)
        elif file_format == "json":
            return self._parse_json(body, limit)
        elif file_format == "parquet":
            return self._parse_parquet(body, limit)
        else:
            logger.warning(f"Unknown format: {file_format}")
            return []

    def _parse_csv(
        self, data: bytes, limit: int | None = None
    ) -> list[dict]:
        delimiter = self.config.config.get("delimiter", ",")
        reader = csv.DictReader(
            io.StringIO(data.decode("utf-8")),
            delimiter=delimiter,
        )
        records = []
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            records.append(dict(row))
        return records

    def _parse_json(
        self, data: bytes, limit: int | None = None
    ) -> list[dict]:
        text = data.decode("utf-8").strip()
        if text.startswith("["):
            # JSON array
            records = json.loads(text)
        else:
            # NDJSON
            records = [
                json.loads(line)
                for line in text.split("\n")
                if line.strip()
            ]
        return records[:limit] if limit else records

    def _parse_parquet(
        self, data: bytes, limit: int | None = None
    ) -> list[dict]:
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(io.BytesIO(data))
            df = table.to_pandas()
            if limit:
                df = df.head(limit)
            return df.to_dict("records")
        except ImportError:
            logger.warning(
                "pyarrow not installed, cannot read Parquet"
            )
            return []
