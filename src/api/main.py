"""
FastAPI application entry-point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router, init_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_services()
    yield
    # Shutdown (nothing special needed)


app = FastAPI(
    title="Hinglish Semantic Chat Search",
    description="Meaning-aware search over Hinglish group chats",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "service": "Hinglish Semantic Chat Search",
        "docs": "/docs",
        "health": "/health",
    }