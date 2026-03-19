import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_api.database import get_db
from nova_api.models import Connector, ConnectorType, Project
from nova_api.schemas import (
    ConnectorCreate,
    ConnectorResponse,
    ConnectorUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/connectors", tags=["connectors"]
)


@router.post("", response_model=ConnectorResponse, status_code=201)
async def create_connector(
    project_id: uuid.UUID,
    body: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    connector = Connector(
        project_id=project_id,
        name=body.name,
        connector_type=ConnectorType(body.connector_type),
        source_type=body.source_type,
        config=body.config,
        credentials_ref=body.credentials_ref,
    )
    db.add(connector)
    await db.flush()
    await db.refresh(connector)
    return connector


@router.get("", response_model=list[ConnectorResponse])
async def list_connectors(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Connector)
        .where(Connector.project_id == project_id)
        .order_by(Connector.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{connector_id}", response_model=ConnectorResponse
)
async def get_connector(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.project_id == project_id,
        )
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(
            status_code=404, detail="Connector not found"
        )
    return connector


@router.patch(
    "/{connector_id}", response_model=ConnectorResponse
)
async def update_connector(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    body: ConnectorUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.project_id == project_id,
        )
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(
            status_code=404, detail="Connector not found"
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(connector, field, value)
    await db.flush()
    await db.refresh(connector)
    return connector


@router.delete("/{connector_id}", status_code=204)
async def delete_connector(
    project_id: uuid.UUID,
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.project_id == project_id,
        )
    )
    connector = result.scalar_one_or_none()
    if not connector:
        raise HTTPException(
            status_code=404, detail="Connector not found"
        )
    await db.delete(connector)
    await db.flush()
