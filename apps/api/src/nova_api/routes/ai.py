from fastapi import APIRouter

from nova_api.schemas import SkillInfo

router = APIRouter(prefix="/ai", tags=["ai"])

SKILLS = [
    SkillInfo(
        id="root-cause-analysis",
        name="Root Cause Analysis",
        description="Diagnose why a dataset is stale or a pipeline failed",
        status="planned",
    ),
    SkillInfo(
        id="sql-assistant",
        name="SQL Assistant",
        description="Generate Trino SQL from natural language",
        status="planned",
    ),
    SkillInfo(
        id="pipeline-proposal",
        name="Pipeline Proposal",
        description="Design a pipeline from a natural language description",
        status="planned",
    ),
]


@router.get("/skills", response_model=list[SkillInfo])
async def list_skills():
    return SKILLS
