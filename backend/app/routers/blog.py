"""News posts (ticket #24).

The same public/admin split as the rest of the content API: the site sees only
active posts published by today at the bar, while the panel sees drafts and
scheduled posts so they can be written first. Writes require an admin session
and CSRF token, and every change is written to the content area of the audit log
in the same transaction.
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app import audit
from app.audit import ChangeAuthor
from app.database import get_db
from app.dependencies import change_author, csrf_protect, get_current_admin
from app.models import BlogPost
from app.schemas import BlogPostResponse, BlogPostWrite
from app.ssr import load_blog_post, load_blog_posts

router = APIRouter()

write_guard = [Depends(get_current_admin), Depends(csrf_protect)]

READ_CACHE_CONTROL = {"Cache-Control": "no-cache"}

BLOG_FIELDS = (
    "slug",
    "title_en",
    "title_es",
    "excerpt_en",
    "excerpt_es",
    "body_en",
    "body_es",
    "image_url",
    "published_on",
    "is_active",
)


def _response(post: dict) -> BlogPostResponse:
    return BlogPostResponse(**post)


def _get_post(db: DBSession, post_id: int) -> BlogPost:
    post = db.get(BlogPost, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


# --- Public reads ----------------------------------------------------------


@router.get("/api/posts", response_model=list[BlogPostResponse])
async def list_posts(response: Response, db: DBSession = Depends(get_db)):
    """Public: published posts, newest first."""
    response.headers.update(READ_CACHE_CONTROL)
    return [_response(post) for post in load_blog_posts(db)]


@router.get("/api/posts/all", response_model=list[BlogPostResponse], dependencies=[Depends(get_current_admin)])
async def list_all_posts(response: Response, db: DBSession = Depends(get_db)):
    """Admin: every post, including drafts and posts dated in the future."""
    response.headers.update(READ_CACHE_CONTROL)
    return [_response(post) for post in load_blog_posts(db, include_inactive=True)]


@router.get("/api/posts/{slug}", response_model=BlogPostResponse)
async def get_post(slug: str, response: Response, db: DBSession = Depends(get_db)):
    """Public: one published post by slug."""
    response.headers.update(READ_CACHE_CONTROL)
    post = load_blog_post(db, slug)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _response(post)


# --- Admin writes ----------------------------------------------------------


@router.post("/api/posts", response_model=BlogPostResponse, status_code=201, dependencies=write_guard)
async def create_post(
    data: BlogPostWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: publish or schedule a post."""
    if db.execute(select(BlogPost).where(BlogPost.slug == data.slug)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A post with this slug already exists")

    post = BlogPost(
        slug=data.slug,
        title_en=data.title_en,
        title_es=data.title_es,
        excerpt_en=data.excerpt_en,
        excerpt_es=data.excerpt_es,
        body_en=data.body_en,
        body_es=data.body_es,
        image_url=data.image_url,
        published_on=data.published_on,
        is_active=data.is_active,
    )
    db.add(post)
    db.flush()

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_CREATE,
        author=author,
        target=audit.format_target(audit.TARGET_BLOG_POST, post.id),
        target_name=post.title_en or post.title_es,
        details=audit.snapshot(post, BLOG_FIELDS),
    )

    db.commit()
    return _response(load_blog_post(db, data.slug, include_inactive=True))


@router.put("/api/posts/{post_id}", response_model=BlogPostResponse, dependencies=write_guard)
async def update_post(
    post_id: int,
    data: BlogPostWrite,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: edit a post, including its slug, date and active flag."""
    post = _get_post(db, post_id)

    if data.slug != post.slug:
        clash = db.execute(select(BlogPost).where(BlogPost.slug == data.slug)).scalar_one_or_none()
        if clash:
            raise HTTPException(status_code=409, detail="A post with this slug already exists")

    before = audit.snapshot(post, BLOG_FIELDS)

    post.slug = data.slug
    post.title_en = data.title_en
    post.title_es = data.title_es
    post.excerpt_en = data.excerpt_en
    post.excerpt_es = data.excerpt_es
    post.body_en = data.body_en
    post.body_es = data.body_es
    post.image_url = data.image_url
    post.published_on = data.published_on
    post.is_active = data.is_active

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_UPDATE,
        author=author,
        target=audit.format_target(audit.TARGET_BLOG_POST, post.id),
        target_name=post.title_en or post.title_es,
        details=audit.diff(before, audit.snapshot(post, BLOG_FIELDS)),
    )

    db.commit()
    return _response(load_blog_post(db, post.slug, include_inactive=True))


@router.delete("/api/posts/{post_id}", status_code=204, dependencies=write_guard)
async def delete_post(
    post_id: int,
    db: DBSession = Depends(get_db),
    author: ChangeAuthor = Depends(change_author),
):
    """Admin: delete a post."""
    post = _get_post(db, post_id)

    audit.log_change(
        db,
        area=audit.AREA_CONTENT,
        action=audit.ACTION_DELETE,
        author=author,
        target=audit.format_target(audit.TARGET_BLOG_POST, post.id),
        target_name=post.title_en or post.title_es,
        details=audit.snapshot(post, BLOG_FIELDS),
    )

    db.delete(post)
    db.commit()
