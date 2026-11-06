"""Image validation, resizing and WebP re-encoding for ticket #50.

The browser uploads a file; this module decides whether it is a real image,
re-encodes it to WebP and writes two files: a display image capped at
``MAX_DIMENSION`` and a thumbnail capped at ``THUMB_DIMENSION``. The database
stores only the filenames (see :class:`app.models.Upload`), so the SQLite file
stays small enough for the backup script.

Everything here is deliberately strict:

* only JPEG, PNG, WebP and GIF are accepted, and the format is read from the
  bytes rather than trusted from the request's ``Content-Type``;
* decompression bombs are refused by pixel count before any resize happens;
* EXIF orientation is applied, then all metadata is dropped by the re-encode;
* filenames are random and generated here, never derived from the upload's name.
"""

from __future__ import annotations

import io
import logging
import re
import secrets
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

log = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SOURCE_PIXELS = 40_000_000
MAX_DIMENSION = 1600
THUMB_DIMENSION = 480
WEBP_QUALITY = 82
THUMB_QUALITY = 78

# Pillow's own guard uses this global. Keeping it at the same value as our
# explicit check means a crafted image is refused by either path.
Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS

_FILENAME_RE = r"^[a-f0-9]{32}(-thumb)?\.webp$"


class UploadError(Exception):
    """Base class for a rejected upload."""


class UnsupportedImage(UploadError):
    """The bytes are not one of the accepted image formats."""


class ImageTooLarge(UploadError):
    """The file or its decoded pixel count is over the limit."""


class CorruptImage(UploadError):
    """The bytes claim to be an image but cannot be decoded."""


def upload_dir() -> Path:
    """The configured upload directory, resolved once per call."""
    return Path(settings.UPLOAD_DIR).expanduser().resolve()


def ensure_upload_dir() -> Path:
    directory = upload_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_filename(name: str) -> bool:
    """True for a name this module generated, and nothing else."""
    return bool(re.fullmatch(_FILENAME_RE, name or ""))


def path_for(name: str) -> Path | None:
    """Resolve a stored filename inside the upload directory, or ``None``.

    The regex is the first line of defence; ``Path.name`` and the resolved
    parent check are the second, so a traversal attempt can never escape even if
    the regex is loosened later.
    """
    if not safe_filename(name):
        return None
    directory = upload_dir()
    candidate = (directory / name).resolve()
    if candidate.parent != directory:
        return None
    return candidate


def _to_webp_mode(image: Image.Image) -> Image.Image:
    """Keep transparency where it exists; otherwise use plain RGB."""
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        return image.convert("RGBA")
    return image.convert("RGB")


def _encode(image: Image.Image, max_dimension: int, quality: int) -> tuple[bytes, int, int]:
    """Resize a copy to fit ``max_dimension`` and encode it as WebP."""
    copy = image.copy()
    copy.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    copy.save(buffer, format="WEBP", quality=quality, method=6)
    return buffer.getvalue(), copy.width, copy.height


def process_image(raw: bytes) -> dict:
    """Validate and re-encode one upload, returning the two WebP payloads.

    Raises :class:`UnsupportedImage`, :class:`ImageTooLarge` or
    :class:`CorruptImage`; callers turn those into HTTP responses.
    """
    if not raw:
        raise UnsupportedImage("The file is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ImageTooLarge("The file is larger than 10 MB")

    try:
        with Image.open(io.BytesIO(raw)) as opened:
            if opened.format not in ALLOWED_FORMATS:
                raise UnsupportedImage("Only JPEG, PNG, WebP and GIF are accepted")

            width, height = opened.size
            if width * height > MAX_SOURCE_PIXELS:
                raise ImageTooLarge("The image has too many pixels")

            # Animated GIFs: the first frame is the still image we keep.
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            image = _to_webp_mode(image)

            full_bytes, full_width, full_height = _encode(
                image, MAX_DIMENSION, WEBP_QUALITY
            )
            thumb_bytes, thumb_width, thumb_height = _encode(
                image, THUMB_DIMENSION, THUMB_QUALITY
            )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise CorruptImage("The file could not be read as an image") from exc
    except Image.DecompressionBombError as exc:  # pragma: no cover - Pillow guard
        raise ImageTooLarge("The image has too many pixels") from exc

    return {
        "full": full_bytes,
        "thumb": thumb_bytes,
        "width": full_width,
        "height": full_height,
        "thumb_width": thumb_width,
        "thumb_height": thumb_height,
    }


def store_image(raw: bytes, original_name: str) -> dict:
    """Validate, re-encode and write both files; return their metadata.

    The names are random, so two uploads can never overwrite each other and a
    filename is safe to cache forever. If the second write fails, the first file
    is removed so a failed upload leaves no orphan.
    """
    processed = process_image(raw)
    directory = ensure_upload_dir()

    stem = secrets.token_hex(16)
    filename = f"{stem}.webp"
    thumb_filename = f"{stem}-thumb.webp"
    full_path = directory / filename
    thumb_path = directory / thumb_filename

    try:
        full_path.write_bytes(processed["full"])
        thumb_path.write_bytes(processed["thumb"])
    except OSError:
        for path in (full_path, thumb_path):
            try:
                path.unlink()
            except OSError:
                pass
        raise

    return {
        "filename": filename,
        "thumb_filename": thumb_filename,
        "original_name": Path(original_name or "upload").name[:255],
        "mime_type": "image/webp",
        "width": processed["width"],
        "height": processed["height"],
        "size_bytes": len(processed["full"]),
    }


def delete_image(filename: str, thumb_filename: str = "") -> None:
    """Remove an upload's files, ignoring a file that is already gone."""
    for name in (filename, thumb_filename):
        path = path_for(name) if name else None
        if path is None:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            # The row is already gone; a stray file is a cleanup problem, not a
            # reason to fail the delete request.
            log.warning("Could not remove upload file %s", path, exc_info=True)
