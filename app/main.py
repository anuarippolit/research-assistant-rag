import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import sources
from app.core.embeddings import get_model
from app.db.sqlite import init_db
from app.db.vector_store import ensure_collection

# uvicorn only configures its own loggers; without this, our logger.info(...) calls are silently dropped
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs once on startup (before first request), code after `yield` runs on shutdown
    init_db()
    ensure_collection()
    get_model()  # load the embedding model now, so the first upload isn't slow
    yield


app = FastAPI(title="Research Assistant RAG", lifespan=lifespan)
app.include_router(sources.router)


@app.get("/")
def health():
    return {"status": "ok"}
