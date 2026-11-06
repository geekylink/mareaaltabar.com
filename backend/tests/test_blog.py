"""Tests for the news/blog engine (ticket #24).

The important behaviour is the publication window: a draft or a future-dated
post must be invisible on the site and still editable in the panel. The rest is
ordinary CRUD, the audit trail every write leaves, and the server-rendered
article a crawler receives.
"""

import pytest
from sqlalchemy import select

from app import main as main_module
from app import ssr as ssr_module
from app.audit import AREA_CONTENT
from app.models import AuditEntry
from app.seed import seed_blog

BUILT_NEWS = (
    "<!doctype html>\n<html lang=\"en\">\n  <head>\n"
    "    <meta name=\"description\" content=\"News from Marea Alta.\" />\n"
    "    <title>News · Marea Alta Surf Bar</title>\n"
    "    <link rel=\"canonical\" href=\"https://mareaaltabar.com/news\" />\n"
    "    <meta property=\"og:title\" content=\"News · Marea Alta Surf Bar\" />\n"
    "    <meta property=\"og:description\" content=\"News from Marea Alta.\" />\n"
    "    <meta property=\"og:url\" content=\"https://mareaaltabar.com/news\" />\n"
    "    <meta name=\"twitter:title\" content=\"News · Marea Alta Surf Bar\" />\n"
    "    <meta name=\"twitter:description\" content=\"News from Marea Alta.\" />\n"
    "  </head>\n  <body>\n    <div id=\"app\"></div>\n"
    "    <script type=\"module\" crossorigin src=\"/assets/news-abc.js\"></script>\n"
    "  </body>\n</html>\n"
)


@pytest.fixture()
def edit_as_admin(client, auth_cookies, csrf_token):
    def _edit(method, url, **kwargs):
        return client.request(method, url, headers={"X-CSRF-Token": csrf_token}, **kwargs)

    return _edit


@pytest.fixture()
def news_site(client, monkeypatch, tmp_path):
    """The test client with a built news.html in place."""
    news = tmp_path / "news.html"
    news.write_text(BUILT_NEWS, encoding="utf-8")
    monkeypatch.setattr(main_module, "NEWS_HTML", news)
    monkeypatch.setattr(ssr_module, "NEWS_HTML", news)
    return client


def make_post(edit_as_admin, **over):
    payload = {
        "slug": "",
        "title_en": "A new cocktail",
        "title_es": "Un cóctel nuevo",
        "excerpt_en": "Something fresh at the bar.",
        "excerpt_es": "Algo fresco en el bar.",
        "body_en": "First paragraph.\n\nSecond paragraph.",
        "body_es": "Primer párrafo.\n\nSegundo párrafo.",
        "image_url": "",
        "published_on": "2026-01-01",
        "is_active": True,
    }
    payload.update(over)
    resp = edit_as_admin("POST", "/api/posts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- Seed ------------------------------------------------------------------


def test_the_launch_post_is_seeded_once(client, db_session):
    posts = client.get("/api/posts").json()
    assert len(posts) == 1
    assert posts[0]["slug"] == "website-launch"
    assert posts[0]["title_en"] == "The new Marea Alta website is live"
    assert "mareaaltabar.com" in posts[0]["body_en"]

    seed_blog(db_session)
    assert len(client.get("/api/posts").json()) == 1


def test_the_launch_post_has_spanish_copy(client):
    post = client.get("/api/posts/website-launch").json()
    assert post["title_es"] == "Ya está en línea el nuevo sitio de Marea Alta"
    assert "nuevo hogar" in post["body_es"]


# --- Public and admin reads ------------------------------------------------


def test_a_draft_and_a_future_post_stay_off_the_site(client, edit_as_admin):
    make_post(edit_as_admin, title_en="Draft", is_active=False)
    make_post(edit_as_admin, title_en="Future", published_on="2999-01-01")

    public = client.get("/api/posts").json()
    assert [post["title_en"] for post in public] == ["The new Marea Alta website is live"]

    admin = client.get("/api/posts/all").json()
    assert {post["title_en"] for post in admin} == {
        "The new Marea Alta website is live",
        "Draft",
        "Future",
    }
    assert next(post for post in admin if post["title_en"] == "Draft")["is_live"] is False
    assert next(post for post in admin if post["title_en"] == "Future")["is_live"] is False


def test_the_admin_read_requires_a_session(client):
    assert client.get("/api/posts/all").status_code == 401


def test_one_post_is_fetched_by_slug(client, edit_as_admin):
    post = make_post(edit_as_admin, slug="new-cocktail")
    resp = client.get("/api/posts/new-cocktail")
    assert resp.status_code == 200
    assert resp.json()["id"] == post["id"]

    assert client.get("/api/posts/nope").status_code == 404


def test_an_inactive_post_is_not_publicly_addressable(client, edit_as_admin):
    make_post(edit_as_admin, slug="hidden-story", is_active=False)
    assert client.get("/api/posts/hidden-story").status_code == 404


# --- Writes ----------------------------------------------------------------


def test_a_blank_slug_and_date_are_filled_in(client, edit_as_admin):
    post = make_post(edit_as_admin, title_en="A brand new story", published_on="")
    assert post["slug"] == "a-brand-new-story"
    assert post["published_on"]
    assert post["is_live"] is True


def test_duplicate_slugs_are_rejected(client, edit_as_admin):
    make_post(edit_as_admin, slug="same-slug")
    resp = edit_as_admin(
        "POST",
        "/api/posts",
        json={"title_en": "Another", "slug": "same-slug", "published_on": "2026-01-01"},
    )
    assert resp.status_code == 409


def test_a_post_can_be_edited_and_deleted(client, edit_as_admin):
    post = make_post(edit_as_admin)
    resp = edit_as_admin(
        "PUT",
        f"/api/posts/{post['id']}",
        json={
            "title_en": "Edited title",
            "slug": post["slug"],
            "body_en": "Edited body.",
            "published_on": post["published_on"],
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title_en"] == "Edited title"

    resp = edit_as_admin("DELETE", f"/api/posts/{post['id']}")
    assert resp.status_code == 204
    assert client.get(f"/api/posts/{post['slug']}").status_code == 404


def test_image_urls_are_validated(client, edit_as_admin):
    resp = edit_as_admin(
        "POST",
        "/api/posts",
        json={"title_en": "Bad image", "image_url": "javascript:alert(1)", "published_on": "2026-01-01"},
    )
    assert resp.status_code == 422


def test_every_write_is_audited(client, edit_as_admin, db_session):
    post = make_post(edit_as_admin, title_en="Audited post")
    entry = db_session.execute(
        select(AuditEntry).where(AuditEntry.target == f"post:{post['id']}")
    ).scalar_one()
    assert entry.area == AREA_CONTENT
    assert entry.action == "create"
    assert entry.target_name == "Audited post"


# --- Server-rendered pages -------------------------------------------------


def test_the_news_index_is_rendered_for_crawlers(news_site):
    resp = news_site.get("/news")
    assert resp.status_code == 200
    assert "The new Marea Alta website is live" in resp.text
    assert "The new site has a launch post" not in resp.text
    assert 'href="/news/website-launch"' in resp.text


def test_the_news_index_renders_spanish(news_site):
    resp = news_site.get("/news?lang=es")
    assert resp.status_code == 200
    assert "Ya está en línea el nuevo sitio de Marea Alta" in resp.text
    assert '<html lang="es">' in resp.text


def test_an_article_is_rendered_with_its_metadata(news_site):
    resp = news_site.get("/news/website-launch")
    assert resp.status_code == 200
    assert "After a good run" in resp.text
    assert "<title>The new Marea Alta website is live · Marea Alta Surf Bar</title>" in resp.text
    assert '<link rel="canonical" href="https://mareaaltabar.com/news/website-launch" />' in resp.text
    assert "BlogPosting" in resp.text
    assert "/news/website-launch" in resp.text


def test_an_unknown_article_is_a_real_404(news_site):
    resp = news_site.get("/news/not-a-story")
    assert resp.status_code == 404
    assert "That story could not be found." in resp.text


def test_admin_entered_markup_is_escaped(news_site, edit_as_admin):
    make_post(
        edit_as_admin,
        slug="escaped-story",
        title_en="<script>alert(1)</script>",
        body_en="<b>not bold</b>",
    )
    resp = news_site.get("/news/escaped-story")
    assert "<script>alert(1)</script>" not in resp.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in resp.text
    assert "&lt;b&gt;not bold&lt;/b&gt;" in resp.text


# --- Sitemap ---------------------------------------------------------------


def test_the_sitemap_lists_published_posts(client, edit_as_admin):
    make_post(edit_as_admin, slug="visible-story")
    make_post(edit_as_admin, slug="hidden-story", is_active=False)

    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "https://mareaaltabar.com/news" in resp.text
    assert "https://mareaaltabar.com/news/website-launch" in resp.text
    assert "https://mareaaltabar.com/news/visible-story" in resp.text
    assert "hidden-story" not in resp.text
