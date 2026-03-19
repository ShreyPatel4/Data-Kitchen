import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Projects ───────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Columns ────────────────────────────────────────────────────────────


class ColumnCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    data_type: str = Field(min_length=1, max_length=100)
    nullable: bool = True
    description: str | None = None
    is_pii: bool = False
    is_partition_key: bool = False
    ordinal_position: int = 0


class ColumnResponse(BaseModel):
    id: uuid.UUID
    name: str
    data_type: str
    nullable: bool
    description: str | None
    is_pii: bool
    is_partition_key: bool
    ordinal_position: int

    model_config = {"from_attributes": True}


# ── Datasets ───────────────────────────────────────────────────────────


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    zone: str = "raw"
    owner: str | None = None
    tags: dict | None = None
    freshness_slo_seconds: int | None = None
    columns: list[ColumnCreate] = []


class DatasetUpdate(BaseModel):
    description: str | None = None
    owner: str | None = None
    tags: dict | None = None
    freshness_slo_seconds: int | None = None


class DatasetListItem(BaseModel):
    id: uuid.UUID
    name: str
    zone: str
    owner: str | None
    schema_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    zone: str
    format: str
    schema_version: int
    owner: str | None
    tags: dict | None
    table_location: str | None
    freshness_slo_seconds: int | None
    created_at: datetime
    updated_at: datetime
    columns: list[ColumnResponse] = []

    model_config = {"from_attributes": True}


# ── Data Contracts ─────────────────────────────────────────────────────


class DataContractCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rules: dict
    severity: str = "warn"


class DataContractResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    description: str | None
    rules: dict
    severity: str
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Connectors ─────────────────────────────────────────────────────────


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_type: str
    source_type: str = Field(min_length=1, max_length=100)
    config: dict = {}
    credentials_ref: str | None = None


class ConnectorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict | None = None
    enabled: bool | None = None


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    connector_type: str
    source_type: str
    config: dict
    enabled: bool
    last_sync_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Pipelines ──────────────────────────────────────────────────────────


class PipelineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    graph: dict = {}
    schedule: str | None = None


class PipelineUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    graph: dict | None = None
    schedule: str | None = None
    status: str | None = None


class PipelineResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    graph: dict
    schedule: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineRunResponse(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    temporal_workflow_id: str | None
    error_message: str | None
    metrics: dict | None
    rows_processed: int

    model_config = {"from_attributes": True}


# ── Lineage ────────────────────────────────────────────────────────────


class LineageEdgeCreate(BaseModel):
    source_dataset_id: uuid.UUID
    target_dataset_id: uuid.UUID
    source_column: str | None = None
    target_column: str | None = None
    transformation_type: str | None = None
    transformation_sql: str | None = None
    job_name: str | None = None


class LineageEdgeResponse(BaseModel):
    id: uuid.UUID
    source_dataset_id: uuid.UUID
    target_dataset_id: uuid.UUID
    source_column: str | None
    target_column: str | None
    transformation_type: str | None
    job_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LineageGraphResponse(BaseModel):
    dataset_id: uuid.UUID
    upstream: list[LineageEdgeResponse]
    downstream: list[LineageEdgeResponse]


# ── AI Skills ──────────────────────────────────────────────────────────


class SkillInfo(BaseModel):
    id: str
    name: str
    description: str
    status: str


# ── Generic ────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
