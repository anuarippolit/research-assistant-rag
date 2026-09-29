from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import sources
from app.db.sqlite import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once on startup (before first request), code after `yield` runs on shutdown
    init_db()
    yield


app = FastAPI(title="Research Assistant RAG", lifespan=lifespan)
app.include_router(sources.router)


@app.get("/")
def health():
    return {"status": "ok"}
