"""Admin image uploads and the public file route (ticket #50).

One write and three session-guarded admin routes:

* ``POST /api/uploads`` — multipart upload, admin + CSRF. The bytes are
  validated, resized and re-encoded to WebP by :mod:`app.images`.
* ``GET /api/uploads`` — the admin library, newest first.
* ``PATCH /api/uploads/{id}`` — edit the bilingual caption.
* ``DELETE /api/uploads/{id}`` — remove the row and both files.
* ``GET /uploads/{filename}`` — the public image itself, with an immutable
  cache header because the filename is random and never reused.

There is deliberately no public metadata endpoint yet: #8 (gallery) will decide
what a gallery needs, and the image URL is enough for a content row today.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from starlette.concurrency import run_in_threadpool

from app import audit, images
from app.audit import ChangeAuthor
from app.database import get_db
from app.dependencies import change_author, csrf_protect, get_current_admin
from app.models import Upload
from app.schemas import UploadResponse, UploadUpdate

log = logging.getLogger(__name__)

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}
# A filename is a random 128-bit value and is never rewritten, so a year of
# caching is safe and makes the gallery cheap.
IMAGE_CACHE_CONTROL = {"Cache-Control": "public, max-age=31536000, immutable"}

UPLOAD_FIELDS = ("caption_en", "caption_es")


def _url(filename: str) -> str:
    return f"/uploads/{filename}"


def _response(row: Upload) -> UploadResponse:
    return UploadResponse(
        id=row.id,
        filename=row.filename,
        thumb_filename=row.thumb_filename,
        url=_url(row.filename),
        thumb_url=_url(row.thumb_filename) if row.thumb_filename else "",
        original_name=row.original_name,
        mime_type=row.mime_type,
        width=row.width,
        height=row.height,
        size_bytes=row.size_bytes,
        caption_en=row.caption_en,
        caption_es=row.caption_es,
        created_at=row.created_at,
    )


def _get_upload(db: DBSession, upload_id: int) -> Upload:
    row = db.get(Upload, upload_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Upload not found")
    return row


# --- Public image ----------------------------------------------------------


@router.get("/uploads/{filename}", include_in_schema=False)
async def serve_upload(filename: str):
    """Public: one stored image, or 404 for anything this app did not name."""
    path = images.path_for(filename)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type="image/webp",
        headers=IMAGE_CACHE_CONTROL,
    )


# --- Admin library ---------------------------------------------------------


@router.get(
    "/api/uploads",
    response_model=list[UploadResponse],
    dependencies=[Depends(get_current_admin)],
)
async def list_uploads(db: DBSession = Depends(get_db)):
    """Admin: every uploaded image, newest first."""
    rows = db.execute(
        select(Upload).order_by(Upload.created_at.desc(), Upload.id.desc())
    ).scalars().all()
    return [_response(row) for row in rows]


@router.post(
    "/api/uploads",
    response_model=UploadResponse,
    status_code=201,
    dependencies=write_guard,
)
async def create_upload(
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: upload one image.

    The size check happens before Pillow sees the bytes, and the processing runs
    in a worker thread so a large resize does not block every other request on
    the single uvicorn worker.
    """
    raw = await file.read(images.MAX_UPLOAD_BYTES + 1)
    if len(raw) > images.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The file is larger than 10 MB")

    try:
        stored = await run_in_threadpool(
            images.store_image, raw, file.filename or "upload"
        )
    except images.UnsupportedImage as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except images.ImageTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except images.CorruptImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        log.exception("Could not store an uploaded image")
        raise HTTPException(status_code=500, detail="Could not store the image") from exc

    row = Upload(
        filename=stored["filename"],
        thumb_filename=stored["thumb_filename"],
        original_name=stored["original_name"],
        mime_type=stored["mime_type"],
        width=stored["width"],
        height=stored["height"],
        size_bytes=stored["size_bytes"],
        caption_en="",
        caption_es="",
    )
    db.add(row)

    try:
        db.flush()
        audit.log_change(
            db,
            area=audit.AREA_CONTENT,
            action=audit.ACTION_CREATE,
            author=author,
            target=audit.format_target(audit.TARGET_UPLOAD, row.id),
            target_name=row.original_name,
            details=audit.snapshot(row, UPLOAD_FIELDS),
        )
        db.commit()
    except Exception:
        db.rollback()
        images.delete_image(stored["filename"], stored["thumb_filename"])
        raise

    db.refresh(row)
    return _response(row)


@router.patch(
    "/api/uploads/{upload_id}",
    response_model=UploadResponse,
    dependencies=write_guard,
)
async def update_upload(
    upload_id: int,
    data: UploadUpdate,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: edit the bilingual caption shown with the image."""
    row = _get_upload(db, upload_id)
    before = audit.snapshot(row, UPLOAD_FIELDS)

    row.caption_en = data.caption_en
    row.caption_es = data.caption_es

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_UPLOAD, row.id),
        target_name=row.original_name,
        details=audit.diff(before, audit.snapshot(row, UPLOAD_FIELDS)),
    )

    db.commit()
    db.refresh(row)
    return _response(row)


@router.delete("/api/uploads/{upload_id}", status_code=204, dependencies=write_guard)
async def delete_upload(
    upload_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: delete the row, then its display image and thumbnail."""
    row = _get_upload(db, upload_id)
    filename, thumb_filename = row.filename, row.thumb_filename

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_UPLOAD, row.id),
        target_name=row.original_name,
        details=audit.snapshot(row, UPLOAD_FIELDS),
    )

    db.delete(row)
    db.commit()
    images.delete_image(filename, thumb_filename)
