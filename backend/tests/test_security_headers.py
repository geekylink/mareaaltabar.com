"""Tests for the security headers (ticket #45).

The CSP matters because the admin panel holds a session cookie. Its script
policy is nonce-based, so the thing worth guarding is not the header's presence
but that *every* inline script the app actually serves carries the same nonce
the header advertises. One template that forgets the attribute is a page whose
JavaScript silently stops running in the browser, which no other test would
catch.
"""

import re

import pytest

from app import main as main_module
from app.config import settings

BUILT_INDEX = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Marea Alta</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/index-abc.js\"></script>\n"
    "  </body>\n</html>\n"
)

BUILT_MENU = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n    <title>Menu</title>\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/menu-xyz.js\"></script>\n"
    "  </body>\n</html>\n"
)


@pytest.fixture()
def built_site(client, monkeypatch, tmp_path):
    """The test client with both built documents in place."""
    index = tmp_path / "index.html"
    index.write_text(BUILT_INDEX, encoding="utf-8")
    menu = tmp_path / "menu.html"
    menu.write_text(BUILT_MENU, encoding="utf-8")
    monkeypatch.setattr(main_module, "INDEX_HTML", index)
    monkeypatch.setattr(main_module, "MENU_HTML", menu)
    return client


def nonce_from(response) -> str:
    csp = response.headers["content-security-policy"]
    match = re.search(r"'nonce-([^']+)'", csp)
    assert match is not None, f"no nonce in CSP: {csp}"
    return match.group(1)


def inline_script_tags(html: str) -> list[str]:
    """Opening tags for scripts with no ``src``, i.e. the ones CSP covers."""
    return re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", html)


# --- The header set --------------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "content-security-policy",
        "permissions-policy",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
    ],
)
def test_every_response_carries_the_security_headers(client, header):
    assert header in client.get("/healthz").headers


def test_the_csp_locks_down_the_obvious_defaults(client):
    csp = client.get("/healthz").headers["content-security-policy"]

    for directive in (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ):
        assert directive in csp


def test_script_src_never_allows_unsafe_inline(client):
    csp = client.get("/healthz").headers["content-security-policy"]
    script_src = next(part for part in csp.split("; ") if part.startswith("script-src"))

    assert "'unsafe-inline'" not in script_src
    assert "'unsafe-eval'" not in script_src
    assert "'self'" in script_src


def test_the_csp_keeps_the_public_page_same_origin(client):
    """Fonts are self-hosted and the surf report is proxied (#34)."""
    csp = client.get("/healthz").headers["content-security-policy"]

    assert "fonts.googleapis.com" not in csp
    assert "fonts.gstatic.com" not in csp
    assert "open-meteo.com" not in csp
    assert "font-src 'self'" in csp
    assert "connect-src 'self'" in csp


def test_permissions_policy_disables_the_sensors_a_bar_does_not_need(client):
    policy = client.get("/healthz").headers["permissions-policy"]

    for feature in ("camera", "microphone", "geolocation", "payment", "usb"):
        assert f"{feature}=()" in policy


# --- The nonce is on every inline script -----------------------------------


def test_homepage_inline_scripts_use_the_header_nonce(built_site):
    response = built_site.get("/")
    nonce = nonce_from(response)

    tags = inline_script_tags(response.text)
    assert tags, "the homepage should have at least the data-seed script"
    for tag in tags:
        assert f'nonce="{nonce}"' in tag, tag


def test_menu_json_ld_carries_the_nonce_too(built_site):
    response = built_site.get("/menu")
    nonce = nonce_from(response)

    assert f'<script type="application/ld+json" nonce="{nonce}">' in response.text
    for tag in inline_script_tags(response.text):
        assert f'nonce="{nonce}"' in tag, tag


def test_the_login_page_inline_scripts_use_the_nonce(client):
    response = client.get("/admin/login")
    nonce = nonce_from(response)

    tags = inline_script_tags(response.text)
    assert tags
    for tag in tags:
        assert f'nonce="{nonce}"' in tag, tag


@pytest.mark.parametrize(
    "path",
    [
        "/admin",
        "/admin/schedule",
        "/admin/menu",
        "/admin/notices",
        "/admin/logs",
        "/admin/account",
        "/admin/data",
    ],
)
def test_every_admin_page_inline_scripts_use_the_nonce(client, auth_cookies, path):
    response = client.get(path)
    assert response.status_code == 200
    nonce = nonce_from(response)

    tags = inline_script_tags(response.text)
    assert tags, f"{path} should have inline scripts"
    for tag in tags:
        assert f'nonce="{nonce}"' in tag, f"{path}: {tag}"


def test_each_response_gets_a_fresh_nonce(client):
    first = nonce_from(client.get("/healthz"))
    second = nonce_from(client.get("/healthz"))

    assert first != second
    assert len(first) >= 16


def test_the_development_docs_are_not_blocked_by_the_site_csp(client):
    """Swagger UI comes from a CDN; the site policy would break it in dev."""
    assert "content-security-policy" not in client.get("/docs").headers


# --- HSTS ------------------------------------------------------------------


def test_hsts_is_not_sent_in_development(client):
    """Sending HSTS from a plain-HTTP dev server would poison localhost."""
    assert "strict-transport-security" not in client.get("/healthz").headers


def test_hsts_is_sent_in_production(client, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    hsts = client.get("/healthz").headers["strict-transport-security"]

    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts
