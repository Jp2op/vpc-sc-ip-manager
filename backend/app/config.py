from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "VPC SC IP Manager"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Auth — API key for securing endpoints
    api_key: str = ""  # Set via IPMGR_API_KEY env var. Empty = auth disabled (dev only)

    # Storage: "memory", "firestore", or "mongodb"
    storage_backend: str = "firestore"

    # Firestore (native)
    gcp_project_id: str = ""
    firestore_collection: str = "ip_whitelist"

    # MongoDB / Firestore MongoDB-compatible
    mongo_uri: str = ""                           # SCRAM connection string
    mongo_db: str = "ip_manager"                  # Database name

    # GitHub
    github_token: str = ""
    github_repo: str = ""                        # e.g. "Jp2op/vpc-sc-ip-manager"
    github_config_path: str = "access_config.json"
    github_branch: str = "main"

    # Admin IPs (comma-separated, always included in config)
    admin_ips: str = ""                           # e.g. "10.20.30.40,10.20.30.41"

    # CORS
    cors_origins: str = "*"                       # Comma-separated origins

    model_config = {"env_prefix": "IPMGR_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
