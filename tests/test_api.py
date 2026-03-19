import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "nova-api"
    assert "version" in data


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "description": "A test"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient):
    await client.post(
        "/api/v1/projects", json={"name": "Project A"}
    )
    await client.post(
        "/api/v1/projects", json={"name": "Project B"}
    )
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/projects/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_dataset_with_columns(client: AsyncClient):
    # Create project first
    proj = await client.post(
        "/api/v1/projects", json={"name": "DS Project"}
    )
    project_id = proj.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={
            "name": "orders",
            "zone": "raw",
            "owner": "data-team",
            "columns": [
                {
                    "name": "id",
                    "data_type": "long",
                    "nullable": False,
                },
                {
                    "name": "customer_email",
                    "data_type": "string",
                    "is_pii": True,
                },
                {"name": "amount", "data_type": "double"},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "orders"
    assert data["zone"] == "raw"
    assert len(data["columns"]) == 3
    pii_col = [
        c for c in data["columns"] if c["name"] == "customer_email"
    ][0]
    assert pii_col["is_pii"] is True


@pytest.mark.asyncio
async def test_list_datasets_filter_by_zone(client: AsyncClient):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Zone Project"}
    )
    project_id = proj.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "raw_table", "zone": "raw"},
    )
    await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "curated_table", "zone": "curated"},
    )

    resp = await client.get(
        f"/api/v1/projects/{project_id}/datasets?zone=curated"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "curated_table"


@pytest.mark.asyncio
async def test_create_connector(client: AsyncClient):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Conn Project"}
    )
    project_id = proj.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/connectors",
        json={
            "name": "prod-postgres",
            "connector_type": "cdc",
            "source_type": "postgresql",
            "config": {
                "host": "prod-db.example.com",
                "port": 5432,
                "database": "orders",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "prod-postgres"
    assert data["connector_type"] == "cdc"
    assert data["source_type"] == "postgresql"


@pytest.mark.asyncio
async def test_create_pipeline(client: AsyncClient):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Pipe Project"}
    )
    project_id = proj.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/pipelines",
        json={
            "name": "orders-pipeline",
            "graph": {
                "nodes": [
                    {"id": "src", "type": "source"},
                    {"id": "xform", "type": "transform"},
                    {"id": "sink", "type": "output"},
                ],
                "edges": [
                    {"from": "src", "to": "xform"},
                    {"from": "xform", "to": "sink"},
                ],
            },
            "schedule": "0 6 * * *",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "orders-pipeline"
    assert data["status"] == "draft"
    assert data["schedule"] == "0 6 * * *"
    assert len(data["graph"]["nodes"]) == 3


@pytest.mark.asyncio
async def test_create_contract(client: AsyncClient):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Contract Project"}
    )
    project_id = proj.json()["id"]

    ds = await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "users", "zone": "curated"},
    )
    dataset_id = ds.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/datasets/{dataset_id}/contracts",
        json={
            "name": "age-range-check",
            "rules": {
                "column": "age",
                "type": "range",
                "min": 0,
                "max": 150,
            },
            "severity": "error",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "age-range-check"
    assert data["severity"] == "error"
    assert data["rules"]["column"] == "age"


@pytest.mark.asyncio
async def test_lineage_graph(client: AsyncClient):
    proj = await client.post(
        "/api/v1/projects", json={"name": "Lineage Project"}
    )
    project_id = proj.json()["id"]

    src = await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "source_table", "zone": "raw"},
    )
    tgt = await client.post(
        f"/api/v1/projects/{project_id}/datasets",
        json={"name": "target_table", "zone": "curated"},
    )
    src_id = src.json()["id"]
    tgt_id = tgt.json()["id"]

    # Create lineage edge
    edge_resp = await client.post(
        "/api/v1/lineage/edges",
        json={
            "source_dataset_id": src_id,
            "target_dataset_id": tgt_id,
            "transformation_type": "direct",
            "job_name": "etl-job",
        },
    )
    assert edge_resp.status_code == 201

    # Query lineage for target — should have source as upstream
    graph = await client.get(f"/api/v1/lineage/datasets/{tgt_id}")
    assert graph.status_code == 200
    data = graph.json()
    assert len(data["upstream"]) == 1
    assert data["upstream"][0]["source_dataset_id"] == src_id
    assert len(data["downstream"]) == 0

    # Query lineage for source — should have target as downstream
    graph2 = await client.get(
        f"/api/v1/lineage/datasets/{src_id}"
    )
    data2 = graph2.json()
    assert len(data2["downstream"]) == 1
    assert len(data2["upstream"]) == 0


@pytest.mark.asyncio
async def test_ai_skills(client: AsyncClient):
    resp = await client.get("/api/v1/ai/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    skill_ids = [s["id"] for s in data]
    assert "root-cause-analysis" in skill_ids
    assert "sql-assistant" in skill_ids
    assert "pipeline-proposal" in skill_ids
