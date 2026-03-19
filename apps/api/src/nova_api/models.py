import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from nova_api.database import Base


class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses String(36) on all backends."""

    impl = String
    cache_ok = True

    def __init__(self):
        super().__init__(length=36)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return uuid.UUID(value)
        return value

# ── Enums ──────────────────────────────────────────────────────────────


class DatasetZone(str, enum.Enum):
    raw = "raw"
    staging = "staging"
    curated = "curated"


class DatasetFormat(str, enum.Enum):
    iceberg = "iceberg"


class ConnectorType(str, enum.Enum):
    cdc = "cdc"
    api = "api"
    file = "file"


class PipelineStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    failed = "failed"
    archived = "archived"


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class ContractSeverity(str, enum.Enum):
    warn = "warn"
    error = "error"
    block = "block"


# ── Models ─────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    connectors: Mapped[list["Connector"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    pipelines: Mapped[list["Pipeline"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_dataset_project_name"),
        Index("ix_dataset_zone", "zone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    zone: Mapped[DatasetZone] = mapped_column(
        Enum(DatasetZone), default=DatasetZone.raw
    )
    format: Mapped[DatasetFormat] = mapped_column(
        Enum(DatasetFormat), default=DatasetFormat.iceberg
    )
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    owner: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[dict | None] = mapped_column(JSON, default=dict)
    table_location: Mapped[str | None] = mapped_column(Text)
    freshness_slo_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="datasets")
    columns: Mapped[list["Column"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    contracts: Mapped[list["DataContract"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class Column(Base):
    __tablename__ = "columns"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "name", name="uq_column_dataset_name"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(100), nullable=False)
    nullable: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_pii: Mapped[bool] = mapped_column(default=False)
    is_partition_key: Mapped[bool] = mapped_column(default=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSON, default=dict
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="columns")


class DataContract(Base):
    __tablename__ = "data_contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    severity: Mapped[ContractSeverity] = mapped_column(
        Enum(ContractSeverity), default=ContractSeverity.warn
    )
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="contracts")


class Connector(Base):
    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[ConnectorType] = mapped_column(
        Enum(ConnectorType), nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "postgresql", "salesforce", "s3"
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    credentials_ref: Mapped[str | None] = mapped_column(
        String(500)
    )  # vault path or secret name
    enabled: Mapped[bool] = mapped_column(default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="connectors")


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    graph: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )  # DAG definition: {nodes: [], edges: []}
    schedule: Mapped[str | None] = mapped_column(
        String(100)
    )  # cron expression
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), default=PipelineStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="pipelines")
    runs: Mapped[list["PipelineRun"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_run_pipeline_status", "pipeline_id", "status"),
        Index("ix_run_started_at", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), default=RunStatus.pending
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict | None] = mapped_column(JSON, default=dict)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="runs")


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_dataset_id",
            "target_dataset_id",
            "source_column",
            "target_column",
            name="uq_lineage_edge",
        ),
        Index("ix_lineage_source", "source_dataset_id"),
        Index("ix_lineage_target", "target_dataset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    source_dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    target_dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    source_column: Mapped[str | None] = mapped_column(String(255))
    target_column: Mapped[str | None] = mapped_column(String(255))
    transformation_type: Mapped[str | None] = mapped_column(
        String(100)
    )  # e.g. "direct", "aggregation", "filter"
    transformation_sql: Mapped[str | None] = mapped_column(Text)
    job_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_dataset: Mapped["Dataset"] = relationship(
        foreign_keys=[source_dataset_id]
    )
    target_dataset: Mapped["Dataset"] = relationship(
        foreign_keys=[target_dataset_id]
    )


class QuarantineRecord(Base):
    __tablename__ = "quarantine_records"
    __table_args__ = (Index("ix_quarantine_dataset", "dataset_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="SET NULL")
    )
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_contracts.id", ondelete="SET NULL")
    )
    row_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    error_reason: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False)
    quarantined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
