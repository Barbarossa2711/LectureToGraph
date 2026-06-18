from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.neo4j import init_driver, close_driver
from app.api.routes import lectures, nodes, edges, graph, jobs, config_meta


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.workspace_dir.mkdir(parents=True, exist_ok=True)
    await init_driver()
    yield
    await close_driver()


app = FastAPI(title="LectureToGraph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lectures.router, prefix="/api")
app.include_router(nodes.router, prefix="/api")
app.include_router(edges.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(config_meta.router, prefix="/api")
