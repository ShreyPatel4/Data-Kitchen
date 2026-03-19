import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nova_api.database import get_db
from nova_api.models import ContractSeverity, DataContract, Dataset
from nova_api.schemas import DataContractCreate, DataContractResponse

router = APIRouter(
    prefix="/projects/{project_id}/datasets/{dataset_id}/contracts",
    tags=["quality"],
)


@router.post("", response_model=DataContractResponse, status_code=201)
async def create_contract(
    project_id: uuid.UUID,
    dataset_id: uuid.UUID,
    body: DataContractCreate,
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

    contract = DataContract(
        dataset_id=dataset_id,
        name=body.name,
        description=body.description,
        rules=body.rules,
        severity=ContractSeverity(body.severity),
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)
    return contract


@router.get("", response_model=list[DataContractResponse])
async def list_contracts(
    project_id: uuid.UUID,
    dataset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataContract)
        .where(DataContract.dataset_id == dataset_id)
        .order_by(DataContract.created_at.desc())
    )
    return result.scalars().all()
