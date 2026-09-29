import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.db.sqlite import BASE_DIR, insert_source

router = APIRouter()

UPLOAD_DIR = BASE_DIR / "data" / "uploads"


@router.post("/sources")
async def upload_source(file: UploadFile = File(...)):
    source_id = str(uuid.uuid4())
    file_type = file.filename.rsplit(".", 1)[-1].lower()
    if file_type != "pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")
    created_at = datetime.now(timezone.utc).isoformat()

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = UPLOAD_DIR / f"{source_id}_{file.filename}"
    contents = await file.read()
    dest_path.write_bytes(contents)

    insert_source(source_id, file.filename, file_type, "pending", created_at)

    return {"source_id": source_id, "filename": file.filename, "status": "pending"}
