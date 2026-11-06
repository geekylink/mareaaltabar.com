"""Tests for the admin image upload pipeline (#50).

The failures that matter here are boundary failures: an unauthenticated upload,
a file that only claims to be an image, a decompression bomb, a path-traversal
request for a file outside the upload directory, and a delete that leaves the
files or the row behind. The happy path is also checked for what the ticket
promises — WebP output, a capped display size, a thumbnail and an immutable
cache header.
"""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import select

from app import images
from app.config import settings
from app.models import AuditEntry, Upload


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    """Point the app at a per-test directory so no test touches real uploads."""
    target = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(target))
    return target


def image_bytes(size=(2000, 1000), fmt="JPEG", mode="RGB", colour=(200, 80, 40)):
    buffer = BytesIO()
    Image.new(mode, size, colour).save(buffer, format=fmt)
    return buffer.getvalue()


def upload(client, csrf_token, data=None, name="photo.jpg", content_type="image/jpeg"):
    return client.post(
        "/api/uploads",
        files={"file": (name, data if data is not None else image_bytes(), content_type)},
        headers={"X-CSRF-Token": csrf_token},
    )


def rows(db_session):
    return list(db_session.execute(select(Upload)).scalars().all())


def audits(db_session):
    return list(db_session.execute(select(AuditEntry)).scalars().all())


# --- The happy path --------------------------------------------------------


def test_an_admin_can_upload_a_photo(client, auth_cookies, csrf_token, upload_dir, db_session):
    resp = upload(client, csrf_token)
    assert resp.status_code == 201

    body = resp.json()
    assert body["mime_type"] == "image/webp"
    assert body["original_name"] == "photo.jpg"
    assert body["width"] == images.MAX_DIMENSION
    assert body["height"] == images.MAX_DIMENSION // 2
    assert body["url"] == f"/uploads/{body['filename']}"
    assert body["thumb_url"] == f"/uploads/{body['thumb_filename']}"

    full = upload_dir / body["filename"]
    thumb = upload_dir / body["thumb_filename"]
    assert full.is_file()
    assert thumb.is_file()
    assert body["size_bytes"] == full.stat().st_size

    with Image.open(full) as stored:
        assert stored.format == "WEBP"
        assert stored.size == (images.MAX_DIMENSION, images.MAX_DIMENSION // 2)
    with Image.open(thumb) as stored_thumb:
        assert stored_thumb.format == "WEBP"
        assert max(stored_thumb.size) == images.THUMB_DIMENSION

    stored_rows = rows(db_session)
    assert len(stored_rows) == 1
    assert stored_rows[0].filename == body["filename"]


def test_a_photo_can_be_fetched_publicly_with_a_long_cache(
    client, auth_cookies, csrf_token, upload_dir
):
    body = upload(client, csrf_token).json()

    resp = client.get(body["url"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    assert "immutable" in resp.headers["cache-control"]
    assert resp.content.startswith(b"RIFF")
    assert b"WEBP" in resp.content[:16]

    assert client.get(body["thumb_url"]).status_code == 200


def test_png_transparency_is_kept_as_webp_alpha(
    client, auth_cookies, csrf_token, upload_dir
):
    data = image_bytes(size=(400, 400), fmt="PNG", mode="RGBA", colour=(0, 0, 0, 0))
    body = upload(client, csrf_token, data=data, name="logo.png", content_type="image/png").json()

    with Image.open(upload_dir / body["filename"]) as stored:
        assert stored.format == "WEBP"
        assert stored.mode == "RGBA"


def test_an_upload_is_logged(client, auth_cookies, csrf_token, upload_dir, db_session):
    body = upload(client, csrf_token).json()
    entries = audits(db_session)
    assert len(entries) == 1
    assert entries[0].area == "content"
    assert entries[0].target == f"upload:{body['id']}"
    assert entries[0].target_name == "photo.jpg"


# --- Access control --------------------------------------------------------


def test_uploading_needs_a_session(client, upload_dir):
    assert upload(client, "").status_code == 401


def test_uploading_needs_a_csrf_token(client, auth_cookies, upload_dir):
    resp = client.post(
        "/api/uploads",
        files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
    )
    assert resp.status_code == 403


def test_the_admin_library_needs_a_session(client, upload_dir):
    assert client.get("/api/uploads").status_code == 401


def test_the_admin_page_needs_a_session(client, upload_dir):
    assert client.get("/admin/uploads").status_code == 401


def test_the_admin_page_renders_for_an_admin(client, auth_cookies, upload_dir):
    body = client.get("/admin/uploads").text
    assert "/api/uploads" in body
    assert "uploads_heading" in body
    assert "/admin/static/admin_i18n.js" in body


def test_the_dashboard_links_to_the_image_library(client, auth_cookies, upload_dir):
    body = client.get("/admin").text
    assert 'href="/admin/uploads"' in body
    assert "card_uploads_title" in body


# --- Rejections ------------------------------------------------------------


def test_a_text_file_is_not_an_image(client, auth_cookies, csrf_token, upload_dir):
    resp = upload(
        client, csrf_token, data=b"this is not an image", name="notes.txt",
        content_type="text/plain",
    )
    assert resp.status_code == 400
    assert rows_count(upload_dir) == 0


def test_a_corrupt_jpeg_is_rejected(client, auth_cookies, csrf_token, upload_dir):
    resp = upload(client, csrf_token, data=b"\xff\xd8\xff\xe0not really")
    assert resp.status_code == 400


def test_a_valid_but_unsupported_format_is_rejected(
    client, auth_cookies, csrf_token, upload_dir
):
    resp = upload(
        client, csrf_token, data=image_bytes(fmt="BMP"), name="photo.bmp",
        content_type="image/bmp",
    )
    assert resp.status_code == 415


def test_a_file_over_ten_megabytes_is_rejected(client, auth_cookies, csrf_token, upload_dir):
    resp = upload(client, csrf_token, data=b"x" * (images.MAX_UPLOAD_BYTES + 1))
    assert resp.status_code == 413


def test_a_decompression_bomb_is_rejected(
    client, auth_cookies, csrf_token, upload_dir, monkeypatch
):
    monkeypatch.setattr(images, "MAX_SOURCE_PIXELS", 1000)
    resp = upload(client, csrf_token, data=image_bytes(size=(200, 100)))
    assert resp.status_code == 413


def test_a_missing_file_is_a_validation_error(client, auth_cookies, csrf_token, upload_dir):
    resp = client.post("/api/uploads", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 422


def test_an_unknown_filename_is_404(client, auth_cookies, upload_dir):
    assert client.get("/uploads/not-a-real-file.webp").status_code == 404


def test_a_traversal_attempt_cannot_reach_a_source_file(client, auth_cookies, upload_dir):
    # The filename regex rejects the encoded separators before any path is built.
    assert client.get("/uploads/..%2F..%2Fapp%2Fconfig.py").status_code == 404
    assert images.path_for("../config.py") is None
    assert images.path_for("../../etc/passwd") is None


# --- Captions and deletion -------------------------------------------------


def test_an_admin_can_edit_the_caption(client, auth_cookies, csrf_token, upload_dir, db_session):
    body = upload(client, csrf_token).json()

    resp = client.patch(
        f"/api/uploads/{body['id']}",
        json={"caption_en": "Sunset on the terrace.", "caption_es": "Atardecer en la terraza."},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    assert resp.json()["caption_en"] == "Sunset on the terrace."
    assert resp.json()["caption_es"] == "Atardecer en la terraza."
    assert rows(db_session)[0].caption_en == "Sunset on the terrace."

    assert len(audits(db_session)) == 2


def test_a_caption_is_sanitised(client, auth_cookies, csrf_token, upload_dir):
    body = upload(client, csrf_token).json()
    resp = client.patch(
        f"/api/uploads/{body['id']}",
        json={"caption_en": "<script>alert(1)</script>Terrace", "caption_es": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 200
    assert "<script>" not in resp.json()["caption_en"]
    assert "Terrace" in resp.json()["caption_en"]


def test_an_admin_can_delete_an_image_and_its_files(
    client, auth_cookies, csrf_token, upload_dir, db_session
):
    body = upload(client, csrf_token).json()
    full = upload_dir / body["filename"]
    thumb = upload_dir / body["thumb_filename"]

    resp = client.delete(
        f"/api/uploads/{body['id']}", headers={"X-CSRF-Token": csrf_token}
    )
    assert resp.status_code == 204
    assert not full.exists()
    assert not thumb.exists()
    assert rows(db_session) == []
    assert client.get(body["url"]).status_code == 404

    again = client.delete(
        f"/api/uploads/{body['id']}", headers={"X-CSRF-Token": csrf_token}
    )
    assert again.status_code == 404


def test_the_library_lists_newest_first(client, auth_cookies, csrf_token, upload_dir):
    first = upload(client, csrf_token, name="first.jpg").json()
    second = upload(client, csrf_token, name="second.jpg").json()

    listed = client.get("/api/uploads").json()
    assert [row["id"] for row in listed] == [second["id"], first["id"]]


def rows_count(upload_dir):
    return len(list(Path(upload_dir).glob("*"))) if Path(upload_dir).exists() else 0
