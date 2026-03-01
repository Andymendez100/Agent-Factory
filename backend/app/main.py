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
    """Application lifespan: seed demo data on startup."""
    try:
        await seed_demo_data()
        logger.info("Demo data seeded successfully")
    except Exception:
        logger.warning("Seed failed (DB may not be ready yet)", exc_info=True)
    yield


DESCRIPTION = """\
**Agent Factory** is a No-Code AI Agent Platform for BPO operations.

Users define a **goal** and the AI agent autonomously decides how to accomplish
it using available tools — browser automation, data analysis, and alerting.

## Key Concepts

- **Platforms** — Internal BPO tools with stored credentials (e.g. employee portals)
- **Tasks** — A goal + which platforms to use + constraints
- **Runs** — A single execution of a task by the AI agent (LangGraph ReAct loop)
- **Steps** — Individual agent reasoning and tool call events during a run

## Architecture

The agent uses a **ReAct pattern** powered by LangGraph:
`Agent thinks → picks tool → executes → observes → repeats → final answer`

Live execution is streamed via **WebSocket** to the React frontend,
where steps appear as nodes on a React Flow canvas in real-time.
"""

app = FastAPI(
    title="Agent Factory",
    summary="No-Code AI Agent Platform for BPO Operations",
    description=DESCRIPTION,
    version="1.0.0",
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "platforms",
            "description": "Manage BPO platform configurations and credentials.",
        },
        {
            "name": "tasks",
            "description": "Define agent tasks with goals, platforms, and constraints.",
        },
        {
            "name": "runs",
            "description": "Trigger and monitor agent execution runs.",
        },
        {
            "name": "websocket",
            "description": "Real-time streaming of agent execution events.",
        },
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3333"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(platforms_router)
app.include_router(runs_router)
app.include_router(tasks_router)
app.include_router(ws_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Returns the health status of the API server."""
    return {"status": "healthy"}
