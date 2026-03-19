import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_api.database import get_db
from nova_api.models import Pipeline, PipelineRun, PipelineStatus, Project
from nova_api.schemas import (
    PipelineCreate,
    PipelineResponse,
    PipelineRunResponse,
    PipelineUpdate,
)

router = APIRouter(
    prefix="/projects/{project_id}/pipelines", tags=["pipelines"]
)


@router.post("", response_model=PipelineResponse, status_code=201)
async def create_pipeline(
    project_id: uuid.UUID,
    body: PipelineCreate,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pipeline = Pipeline(
        project_id=project_id,
        name=body.name,
        description=body.description,
        graph=body.graph,
        schedule=body.schedule,
    )
    db.add(pipeline)
    await db.flush()
    await db.refresh(pipeline)
    return pipeline


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines(
    project_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Pipeline)
        .where(Pipeline.project_id == project_id)
        .order_by(Pipeline.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.project_id == project_id,
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(
            status_code=404, detail="Pipeline not found"
        )
    return pipeline


@router.patch(
    "/{pipeline_id}", response_model=PipelineResponse
)
async def update_pipeline(
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    body: PipelineUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.project_id == project_id,
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(
            status_code=404, detail="Pipeline not found"
        )
    updates = body.model_dump(exclude_unset=True)
    if "status" in updates:
        updates["status"] = PipelineStatus(updates["status"])
    for field, value in updates.items():
        setattr(pipeline, field, value)
    await db.flush()
    await db.refresh(pipeline)
    return pipeline


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.project_id == project_id,
        )
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(
            status_code=404, detail="Pipeline not found"
        )
    await db.delete(pipeline)
    await db.flush()


@router.get(
    "/{pipeline_id}/runs",
    response_model=list[PipelineRunResponse],
)
async def list_pipeline_runs(
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.project_id == project_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=404, detail="Pipeline not found"
        )

    runs = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.pipeline_id == pipeline_id)
        .order_by(PipelineRun.started_at.desc().nulls_last())
    )
    return runs.scalars().all()
