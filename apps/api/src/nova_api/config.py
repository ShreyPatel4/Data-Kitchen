from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nova_metadata"
    )

    # Neo4j (lineage graph)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4jpassword"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_use_ssl: bool = False
    s3_bucket_raw: str = "raw"
    s3_bucket_staging: str = "staging"
    s3_bucket_curated: str = "curated"

    # Temporal
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"

    # Auth (JWT for MVP, SSO later)
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # App
    app_name: str = "Nova"
    app_version: str = "0.1.0"
    debug: bool = True

    model_config = {"env_prefix": "NOVA_"}


settings = Settings()
