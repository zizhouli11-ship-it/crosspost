from pathlib import Path
from typing import List
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from crosspost.models import Post, Media
from crosspost.orchestrator import publish_all
from crosspost.registry import build_registry

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"

app = FastAPI(title="crosspost")
adapters, publishers, creds = build_registry()


class MediaIn(BaseModel):
    path: str
    type: str


class PostIn(BaseModel):
    title: str = ""
    body: str = ""
    media: List[MediaIn] = []
    tags: List[str] = []
    overrides: dict = {}


class PublishIn(BaseModel):
    post: PostIn
    platforms: List[str]


def _to_post(p: PostIn) -> Post:
    return Post(
        title=p.title, body=p.body,
        media=[Media(path=m.path, type=m.type) for m in p.media],
        tags=p.tags, overrides=p.overrides,
    )


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/platforms")
def platforms():
    return [
        {"platform": name, "ready": publishers[name].login_status()}
        for name in publishers
    ]


@app.post("/api/validate")
def validate(p: PostIn):
    post = _to_post(p)
    out = {}
    for name, adapter in adapters.items():
        v = adapter.validate(post)
        out[name] = {"status": v.status, "message": v.message}
    return out


@app.post("/api/publish")
def publish(req: PublishIn):
    post = _to_post(req.post)
    results = publish_all(post, req.platforms, publishers, adapters)
    return [vars(r) for r in results]


app.mount("/web", StaticFiles(directory=WEB), name="web")
