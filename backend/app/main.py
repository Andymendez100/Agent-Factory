import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.platforms import router as platforms_router
from app.api.runs import router as runs_router
from app.api.tasks import router as tasks_router
from app.api.websocket import router as ws_router
from app.db.seed import seed_demo_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — seed demo data (idempotent)
    try:
        await seed_demo_data()
    except Exception:
        logger.warning("Seed failed (DB may not be ready yet)", exc_info=True)
    yield
    # Shutdown


app = FastAPI(
    title="Agent Factory",
    description="No-Code AI Agent Platform for BPO Operations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(platforms_router)
app.include_router(runs_router)
app.include_router(tasks_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
