"""The admin panel uses the same branded icons as the public site.

The emoji favicon was duplicated as a data URI in every template, so replacing
the brand mark meant remembering every page. These tests keep the icon set and
the templates in step: no template may reintroduce the emoji, and every file the
templates point at has to exist at the advertised size.
"""

from pathlib import Path
import struct

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEMPLATES = BACKEND_DIR / "app" / "templates"
ICONS = BACKEND_DIR.parent / "frontend" / "public" / "icons"

ADMIN_PAGES = (
    "login.html",
    "admin/dashboard.html",
    "admin/schedule.html",
    "admin/menu.html",
    "admin/notices.html",
    "admin/logs.html",
    "admin/account.html",
)


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def test_every_admin_page_uses_the_branded_icon_set():
    for page in ADMIN_PAGES:
        html = (TEMPLATES / page).read_text(encoding="utf-8")
        assert "data:image/svg+xml" not in html, f"{page} still has the emoji favicon"
        assert 'href="/icons/favicon.svg"' in html
        assert 'href="/icons/favicon-32.png"' in html
        assert 'href="/icons/favicon-16.png"' in html
        assert 'href="/icons/apple-touch-icon.png"' in html


def test_icon_files_exist_at_the_advertised_sizes():
    expected = {
        "favicon-16.png": (16, 16),
        "favicon-32.png": (32, 32),
        "apple-touch-icon.png": (180, 180),
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
    }
    for name, size in expected.items():
        assert _png_size(ICONS / name) == size, name

    assert (ICONS / "favicon.svg").read_text(encoding="utf-8").startswith("<svg")
    assert (ICONS / "favicon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
