from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 - register ORM models before create_all
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="HirePilot AI API", version="1.0.0", description="Agentic recruitment and career copilot API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/")
def root():
    return {"name": "HirePilot AI", "status": "running", "docs": "/docs", "health": "/api/health"}
