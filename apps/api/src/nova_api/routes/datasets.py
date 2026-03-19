import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nova_api.database import get_db
from nova_api.models import Column, Dataset, DatasetZone, Project
from nova_api.schemas import (
    DatasetCreate,
    DatasetListItem,
    DatasetResponse,
    DatasetUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/datasets", tags=["datasets"])


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    project_id: uuid.UUID,
    body: DatasetCreate,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = Dataset(
        project_id=project_id,
        name=body.name,
        description=body.description,
        zone=DatasetZone(body.zone),
        owner=body.owner,
        tags=body.tags or {},
        freshness_slo_seconds=body.freshness_slo_seconds,
    )
    db.add(dataset)
    await db.flush()

    for i, col in enumerate(body.columns):
        column = Column(
            dataset_id=dataset.id,
            name=col.name,
            data_type=col.data_type,
            nullable=col.nullable,
            description=col.description,
            is_pii=col.is_pii,
            is_partition_key=col.is_partition_key,
            ordinal_position=col.ordinal_position or i,
        )
        db.add(column)

    await db.flush()
    await db.refresh(dataset)

    # Reload with columns
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.columns))
        .where(Dataset.id == dataset.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[DatasetListItem])
async def list_datasets(
    project_id: uuid.UUID,
    zone: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Dataset).where(Dataset.project_id == project_id)
    if zone:
        stmt = stmt.where(Dataset.zone == DatasetZone(zone))
    stmt = stmt.order_by(Dataset.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    project_id: uuid.UUID,
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.columns))
        .where(Dataset.id == dataset_id, Dataset.project_id == project_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.patch("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    project_id: uuid.UUID,
    dataset_id: uuid.UUID,
    body: DatasetUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset)
        .options(selectinload(Dataset.columns))
        .where(Dataset.id == dataset_id, Dataset.project_id == project_id)
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(dataset, field, value)
    await db.flush()
    await db.refresh(dataset)
    return dataset


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    project_id: uuid.UUID,
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Dataset).where(
            Dataset.id == dataset_id, Dataset.project_id == project_id
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset)
    await db.flush()
