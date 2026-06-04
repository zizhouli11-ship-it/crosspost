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


class XCredsIn(BaseModel):
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str


class TiktokCredsIn(BaseModel):
    access_token: str
    refresh_token: str = ""
    client_key: str = ""
    client_secret: str = ""


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


@app.post("/api/credentials/x")
def save_x_credentials(c: XCredsIn):
    """保存 X 的 API 密钥到本地 credentials.json(不进 git)。"""
    creds.set("x", c.model_dump())
    return {"platform": "x", "ready": publishers["x"].login_status()}


@app.post("/api/credentials/tiktok")
def save_tiktok_credentials(c: TiktokCredsIn):
    """保存 TikTok 凭证(至少 access_token)到本地 credentials.json。"""
    creds.set("tiktok", c.model_dump())
    return {"platform": "tiktok", "ready": publishers["tiktok"].login_status()}


@app.post("/api/youtube/authorize")
def youtube_authorize():
    """触发 YouTube OAuth:打开本地浏览器走授权,成功后写入 token。
    需要先把 Google 下载的 client secret 放到 config/youtube_client_secret.json。
    """
    try:
        publishers["youtube"].authorize()
    except FileNotFoundError:
        return {"ok": False,
                "message": "缺少 config/youtube_client_secret.json,"
                           "请先从 Google Cloud Console 下载放入该位置"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "message": f"授权失败: {e}"}
    return {"ok": True, "ready": publishers["youtube"].login_status()}


app.mount("/web", StaticFiles(directory=WEB), name="web")
