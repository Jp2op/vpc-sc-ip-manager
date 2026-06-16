import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.auth import APIKeyMiddleware
from app.storage.base import BaseStorage
from app.storage.memory import MemoryStorage
from app.services.github_service import GitHubService
from app.services.ip_service import IPService
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.routers.ips import router as ips_router, init_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_storage() -> BaseStorage:
    s = get_settings()
    if s.storage_backend == "firestore":
        from app.storage.firestore import FirestoreStorage
        logger.info(f"Storage: Firestore (project={s.gcp_project_id})")
        return FirestoreStorage(project_id=s.gcp_project_id, collection=s.firestore_collection)
    logger.info("Storage: in-memory (data resets on restart)")
    return MemoryStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    logger.info(f"Starting {s.app_name} v{s.app_version}")
    logger.info(f"Storage: {s.storage_backend}")
    logger.info(f"GitHub: {'configured' if s.github_token else 'MOCK mode'}")
    logger.info(f"Auth: {'API key required' if s.api_key else 'DISABLED (dev mode)'}")

    storage = create_storage()
    github = GitHubService()
    service = IPService(storage=storage, github=github)
    init_service(service)

    start_scheduler()
    logger.info("Ready")

    yield

    shutdown_scheduler()
    logger.info("Shutdown complete")


app = FastAPI(
    title="VPC SC IP Manager",
    description="Self-service IP whitelisting for Vertex AI via VPC Service Controls.",
    version=get_settings().app_version,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(APIKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ips_router, prefix=get_settings().api_prefix)


@app.get("/health")
async def health():
    """Liveness probe — is the app running."""
    return {"status": "ok"}


@app.get("/readiness")
async def readiness():
    """Readiness probe — is the app ready to serve traffic."""
    return {"status": "ready", "service": get_settings().app_name}
