import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_api.database import get_db
from nova_api.models import LineageEdge
from nova_api.schemas import (
    LineageEdgeCreate,
    LineageEdgeResponse,
    LineageGraphResponse,
)

router = APIRouter(prefix="/lineage", tags=["lineage"])


@router.post("/edges", response_model=LineageEdgeResponse, status_code=201)
async def create_lineage_edge(
    body: LineageEdgeCreate, db: AsyncSession = Depends(get_db)
):
    edge = LineageEdge(
        source_dataset_id=body.source_dataset_id,
        target_dataset_id=body.target_dataset_id,
        source_column=body.source_column,
        target_column=body.target_column,
        transformation_type=body.transformation_type,
        transformation_sql=body.transformation_sql,
        job_name=body.job_name,
    )
    db.add(edge)
    await db.flush()
    await db.refresh(edge)
    return edge


@router.get(
    "/datasets/{dataset_id}", response_model=LineageGraphResponse
)
async def get_lineage_graph(
    dataset_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    upstream_result = await db.execute(
        select(LineageEdge).where(
            LineageEdge.target_dataset_id == dataset_id
        )
    )
    downstream_result = await db.execute(
        select(LineageEdge).where(
            LineageEdge.source_dataset_id == dataset_id
        )
    )
    return LineageGraphResponse(
        dataset_id=dataset_id,
        upstream=upstream_result.scalars().all(),
        downstream=downstream_result.scalars().all(),
    )
