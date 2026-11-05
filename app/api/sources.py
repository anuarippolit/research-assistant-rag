import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException

from app.core.ingestion import ingest_source
from app.db.vector_store import delete_source_chunks
from app.db.sqlite import BASE_DIR, insert_source, list_sources, get_source, delete_source
from app.schemas import SourceOut

router = APIRouter()

UPLOAD_DIR = BASE_DIR / "data" / "uploads"


@router.post("/sources")
async def upload_source(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    source_id = str(uuid.uuid4())
    file_type = file.filename.rsplit(".", 1)[-1].lower()
    if file_type != "pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")
    created_at = datetime.now(timezone.utc).isoformat()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = UPLOAD_DIR / f"{source_id}_{file.filename}"
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    dest_path.write_bytes(contents)

    insert_source(source_id, file.filename, file_type, "pending", created_at)
    # runs AFTER the response is sent -> the client doesn't wait for parsing/embedding
    background_tasks.add_task(ingest_source, source_id, file.filename, dest_path)

    return {"source_id": source_id, "filename": file.filename, "status": "pending"}

@router.get("/sources", response_model=list[SourceOut])
def get_sources():
    sources = list_sources()
    return sources

@router.get("/sources/{source_id}", response_model=SourceOut)
def get_source_by_id(source_id: str):
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source

@router.delete("/sources/{source_id}")
def delete_source_by_id(source_id:str) -> dict:
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    delete_source_chunks(source_id)
    (UPLOAD_DIR / f"{source_id}_{source['filename']}").unlink(missing_ok=True)
    delete_source(source_id)
    return {"message": f"Source {source_id} deleted."}
