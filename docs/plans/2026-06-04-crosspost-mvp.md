# 跨平台发布工具 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一个本地网页面板,把一份内容(图文/视频)一键发布到小红书、X、YouTube,并展示每个平台的发布结果。

**Architecture:** Python + FastAPI 本地服务。通用 `Post` 模型经各平台 `Adapter` 校验/翻译,再由统一接口的 `Publisher` 发布——浏览器引擎(小红书)通过子进程复用现有 `post-to-xhs/publish_pipeline.py`,API 引擎(X/YouTube)调官方接口。`Orchestrator` 逐平台独立捕获异常并汇总 `Result`。

**Tech Stack:** Python 3.11+、FastAPI、uvicorn、requests、requests-oauthlib(X)、google-api-python-client + google-auth-oauthlib(YouTube)、pytest。

**复用资产:** `C:\Users\30488\.claude\skills\post-to-xhs\scripts\publish_pipeline.py`
- 入参:`--title`、`--content`(标签写在正文最后一行,形如 `#AI #出海`)、`--images PATH...`、`--video PATH`、`--skip-file-check`、`--reuse-existing-tab`
- 退出码:`0`=成功(stdout 含 `PUBLISH_STATUS: PUBLISHED`)、`1`=未登录(stdout `NOT_LOGGED_IN`)、`2`=错误(stderr 含原因)

---

## 文件结构

```
crosspost/
  requirements.txt
  .gitignore
  app.py                      # FastAPI 入口 + 路由
  crosspost/
    __init__.py
    models.py                 # Post / Media / Result / Validation
    credentials.py            # CredentialStore (读写 config/credentials.json)
    orchestrator.py           # publish_all() 编排
    registry.py               # 平台 -> Publisher 实例 的装配
    adapters/
      __init__.py
      base.py                 # Adapter 协议 + 通用 helper
      xhs.py                  # 小红书适配
      x.py                    # X 适配
      youtube.py              # YouTube 适配
    publishers/
      __init__.py
      base.py                 # Publisher 协议
      xhs.py                  # 子进程调 publish_pipeline.py
      x.py                    # X API
      youtube.py              # YouTube API
  web/
    index.html
    app.js
    style.css
  config/
    credentials.example.json
    # credentials.json (gitignored, 运行时生成)
  tests/
    test_models.py
    test_adapters_xhs.py
    test_adapters_x.py
    test_adapters_youtube.py
    test_credentials.py
    test_orchestrator.py
    test_publisher_xhs.py
    test_publisher_x.py
    test_publisher_youtube.py
  docs/
    specs/2026-06-04-crosspost-design.md
    plans/2026-06-04-crosspost-mvp.md
```

**职责边界:** `models` 纯数据;`adapters/*` 只做"校验 + 把 Post 翻译成平台 payload"(无副作用、易测);`publishers/*` 只做"拿 payload 去发"(有副作用);`orchestrator` 只做编排与异常隔离;`registry` 只做装配;`app.py` 只做 HTTP。

---

## Task 1: 项目脚手架

**Files:**
- Create: `crosspost/requirements.txt`
- Create: `crosspost/.gitignore`
- Create: `crosspost/config/credentials.example.json`
- Create: `crosspost/crosspost/__init__.py`、`crosspost/adapters/__init__.py`、`crosspost/publishers/__init__.py`、`crosspost/tests/__init__.py`(空文件)

- [ ] **Step 1: 写 requirements.txt**

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
requests>=2.28.0
requests-oauthlib>=1.3.1
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.2.0
google-auth-httplib2>=0.2.0
pytest>=8.0.0
```

- [ ] **Step 2: 写 .gitignore**

```
__pycache__/
*.pyc
.venv/
config/credentials.json
config/youtube_token.json
.pytest_cache/
tmp/
```

- [ ] **Step 3: 写 config/credentials.example.json**(供用户照抄填真值)

```json
{
  "x": {
    "api_key": "",
    "api_secret": "",
    "access_token": "",
    "access_token_secret": ""
  },
  "youtube": {
    "client_secret_file": "config/youtube_client_secret.json",
    "token_file": "config/youtube_token.json"
  }
}
```

- [ ] **Step 4: 建空的包初始化文件**

创建空文件:`crosspost/crosspost/__init__.py`、`crosspost/crosspost/adapters/__init__.py`、`crosspost/crosspost/publishers/__init__.py`、`crosspost/tests/__init__.py`。

- [ ] **Step 5: 建虚拟环境并安装依赖**

Run(PowerShell,工作目录 `C:\Users\30488\crosspost`):
```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
Expected: 安装成功,无报错。

- [ ] **Step 6: 初始化 git 并提交**

```powershell
git init
git add .
git commit -m "chore: scaffold crosspost project"
```

---

## Task 2: 数据模型

**Files:**
- Create: `crosspost/crosspost/models.py`
- Test: `crosspost/tests/test_models.py`

- [ ] **Step 1: 写失败测试**

`tests/test_models.py`:
```python
from crosspost.models import Post, Media, Result, Validation


def test_media_defaults():
    m = Media(path="a.jpg", type="image")
    assert m.path == "a.jpg"
    assert m.type == "image"


def test_post_holds_fields():
    p = Post(
        title="标题",
        body="正文",
        media=[Media(path="a.jpg", type="image")],
        tags=["AI", "出海"],
        overrides={"xhs": {"title": "小红书标题"}},
    )
    assert p.title == "标题"
    assert p.tags == ["AI", "出海"]
    assert p.overrides["xhs"]["title"] == "小红书标题"


def test_post_optional_fields_default_empty():
    p = Post(title="t", body="b")
    assert p.media == []
    assert p.tags == []
    assert p.overrides == {}


def test_result_skipped():
    r = Result(platform="youtube", status="skipped", message="需要视频")
    assert r.status == "skipped"
    assert r.url is None
    assert r.message == "需要视频"


def test_validation_ok():
    v = Validation(status="ok", message="")
    assert v.status == "ok"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'crosspost.models'`

- [ ] **Step 3: 写实现**

`crosspost/models.py`:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

MediaType = Literal["image", "video"]
ResultStatus = Literal["success", "failed", "skipped", "needs_login"]
ValidationStatus = Literal["ok", "warn", "skip"]


@dataclass
class Media:
    path: str
    type: MediaType


@dataclass
class Post:
    title: str
    body: str
    media: list[Media] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    overrides: dict[str, dict] = field(default_factory=dict)

    def images(self) -> list[Media]:
        return [m for m in self.media if m.type == "image"]

    def videos(self) -> list[Media]:
        return [m for m in self.media if m.type == "video"]

    def for_platform(self, platform: str) -> "Post":
        """返回应用了该平台 overrides 的副本(title/body/tags)。"""
        ov = self.overrides.get(platform, {})
        return Post(
            title=ov.get("title", self.title),
            body=ov.get("body", self.body),
            media=list(self.media),
            tags=ov.get("tags", self.tags),
            overrides={},
        )


@dataclass
class Result:
    platform: str
    status: ResultStatus
    url: str | None = None
    message: str | None = None


@dataclass
class Validation:
    status: ValidationStatus
    message: str = ""
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_models.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/models.py tests/test_models.py
git commit -m "feat: add Post/Media/Result/Validation models"
```

---

## Task 3: Adapter 基类

**Files:**
- Create: `crosspost/crosspost/adapters/base.py`

- [ ] **Step 1: 写实现(无独立测试,接口由各平台测试覆盖)**

`crosspost/adapters/base.py`:
```python
from __future__ import annotations
from typing import Protocol
from crosspost.models import Post, Validation


class Adapter(Protocol):
    platform: str

    def validate(self, post: Post) -> Validation:
        """发布前校验该平台是否可发;返回 ok / warn / skip。"""
        ...

    def adapt(self, post: Post) -> dict:
        """把(已应用 overrides 的)Post 翻译成该平台 payload dict。"""
        ...


def join_tags(tags: list[str], prefix: str = "#", sep: str = " ") -> str:
    """["AI","出海"] -> "#AI #出海" """
    return sep.join(f"{prefix}{t.lstrip('#')}" for t in tags)
```

- [ ] **Step 2: 提交**

```powershell
git add crosspost/adapters/base.py
git commit -m "feat: add Adapter protocol and join_tags helper"
```

---

## Task 4: 小红书 Adapter

**Files:**
- Create: `crosspost/crosspost/adapters/xhs.py`
- Test: `crosspost/tests/test_adapters_xhs.py`

小红书规则:标题 ≤20 字(超出 warn);至少要有图或视频(否则 skip);标签拼到正文最后一行 `#tag`。

- [ ] **Step 1: 写失败测试**

`tests/test_adapters_xhs.py`:
```python
from crosspost.adapters.xhs import XhsAdapter
from crosspost.models import Post, Media


def test_skip_when_no_media():
    a = XhsAdapter()
    v = a.validate(Post(title="t", body="b"))
    assert v.status == "skip"
    assert "图" in v.message or "视频" in v.message


def test_warn_when_title_too_long():
    a = XhsAdapter()
    post = Post(title="一" * 21, body="b", media=[Media("a.jpg", "image")])
    v = a.validate(post)
    assert v.status == "warn"


def test_ok_with_image():
    a = XhsAdapter()
    post = Post(title="标题", body="b", media=[Media("a.jpg", "image")])
    assert a.validate(post).status == "ok"


def test_adapt_appends_tags_to_content_last_line():
    a = XhsAdapter()
    post = Post(title="标题", body="正文", tags=["AI", "出海"],
                media=[Media("a.jpg", "image")])
    payload = a.adapt(post)
    assert payload["title"] == "标题"
    assert payload["content"].endswith("#AI #出海")
    assert payload["content"].startswith("正文")
    assert payload["images"] == ["a.jpg"]
    assert payload["video"] is None


def test_adapt_video():
    a = XhsAdapter()
    post = Post(title="标题", body="正文", media=[Media("v.mp4", "video")])
    payload = a.adapt(post)
    assert payload["video"] == "v.mp4"
    assert payload["images"] == []
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_xhs.py -v`
Expected: FAIL —— `ModuleNotFoundError: No module named 'crosspost.adapters.xhs'`

- [ ] **Step 3: 写实现**

`crosspost/adapters/xhs.py`:
```python
from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags

TITLE_MAX = 20


class XhsAdapter:
    platform = "xhs"

    def validate(self, post: Post) -> Validation:
        if not post.media:
            return Validation(status="skip", message="小红书需要至少一张图或一个视频")
        if len(post.title) > TITLE_MAX:
            return Validation(status="warn",
                              message=f"标题超过 {TITLE_MAX} 字,可能被截断")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        content = post.body
        if post.tags:
            content = f"{content}\n{join_tags(post.tags)}"
        videos = post.videos()
        return {
            "title": post.title,
            "content": content,
            "images": [m.path for m in post.images()],
            "video": videos[0].path if videos else None,
        }
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_xhs.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/adapters/xhs.py tests/test_adapters_xhs.py
git commit -m "feat: add Xiaohongshu adapter"
```

---

## Task 5: X Adapter

**Files:**
- Create: `crosspost/crosspost/adapters/x.py`
- Test: `crosspost/tests/test_adapters_x.py`

X 规则:无标题;tweet 文本 = 正文 + 换行 + `#tag`;>280 字 skip(报错跳过);图最多 4 张(超出取前 4 张并 warn);只支持图片(视频 MVP 不发,有视频无图则 skip)。

- [ ] **Step 1: 写失败测试**

`tests/test_adapters_x.py`:
```python
from crosspost.adapters.x import XAdapter
from crosspost.models import Post, Media


def test_ok_text_only():
    a = XAdapter()
    assert a.validate(Post(title="t", body="hello")).status == "ok"


def test_skip_when_over_280():
    a = XAdapter()
    post = Post(title="", body="x" * 281)
    v = a.validate(post)
    assert v.status == "skip"


def test_warn_when_more_than_4_images():
    a = XAdapter()
    post = Post(title="", body="hi",
                media=[Media(f"{i}.jpg", "image") for i in range(5)])
    assert a.validate(post).status == "warn"


def test_adapt_builds_text_with_tags():
    a = XAdapter()
    post = Post(title="ignored", body="hello world", tags=["AI"])
    payload = a.adapt(post)
    assert payload["text"] == "hello world\n#AI"
    assert payload["image_paths"] == []


def test_adapt_caps_images_at_4():
    a = XAdapter()
    post = Post(title="", body="hi",
                media=[Media(f"{i}.jpg", "image") for i in range(6)])
    payload = a.adapt(post)
    assert len(payload["image_paths"]) == 4
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_x.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/adapters/x.py`:
```python
from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags

TWEET_MAX = 280
IMAGE_MAX = 4


def _text(post: Post) -> str:
    text = post.body
    if post.tags:
        text = f"{text}\n{join_tags(post.tags)}"
    return text


class XAdapter:
    platform = "x"

    def validate(self, post: Post) -> Validation:
        if len(_text(post)) > TWEET_MAX:
            return Validation(status="skip",
                              message=f"超过 {TWEET_MAX} 字,X 无法发布")
        if len(post.images()) > IMAGE_MAX:
            return Validation(status="warn",
                              message=f"图片多于 {IMAGE_MAX} 张,只取前 {IMAGE_MAX} 张")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        return {
            "text": _text(post),
            "image_paths": [m.path for m in post.images()][:IMAGE_MAX],
        }
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_x.py -v`
Expected: PASS(5 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/adapters/x.py tests/test_adapters_x.py
git commit -m "feat: add X adapter"
```

---

## Task 6: YouTube Adapter

**Files:**
- Create: `crosspost/crosspost/adapters/youtube.py`
- Test: `crosspost/tests/test_adapters_youtube.py`

YouTube 规则:必须有视频(无视频 skip);title→视频标题(>100 字 warn);body→description;tags→ tags 字段(原样,不带 #)。

- [ ] **Step 1: 写失败测试**

`tests/test_adapters_youtube.py`:
```python
from crosspost.adapters.youtube import YoutubeAdapter
from crosspost.models import Post, Media


def test_skip_when_no_video():
    a = YoutubeAdapter()
    post = Post(title="t", body="b", media=[Media("a.jpg", "image")])
    v = a.validate(post)
    assert v.status == "skip"
    assert "视频" in v.message


def test_ok_with_video():
    a = YoutubeAdapter()
    post = Post(title="t", body="b", media=[Media("v.mp4", "video")])
    assert a.validate(post).status == "ok"


def test_warn_long_title():
    a = YoutubeAdapter()
    post = Post(title="a" * 101, body="b", media=[Media("v.mp4", "video")])
    assert a.validate(post).status == "warn"


def test_adapt_payload():
    a = YoutubeAdapter()
    post = Post(title="标题", body="描述", tags=["AI", "tech"],
                media=[Media("v.mp4", "video")])
    payload = a.adapt(post)
    assert payload["video_path"] == "v.mp4"
    assert payload["snippet"]["title"] == "标题"
    assert payload["snippet"]["description"] == "描述"
    assert payload["snippet"]["tags"] == ["AI", "tech"]
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_youtube.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/adapters/youtube.py`:
```python
from __future__ import annotations
from crosspost.models import Post, Validation

TITLE_MAX = 100


class YoutubeAdapter:
    platform = "youtube"

    def validate(self, post: Post) -> Validation:
        if not post.videos():
            return Validation(status="skip", message="YouTube 需要一个视频文件")
        if len(post.title) > TITLE_MAX:
            return Validation(status="warn",
                              message=f"标题超过 {TITLE_MAX} 字,会被截断")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        return {
            "video_path": post.videos()[0].path,
            "snippet": {
                "title": post.title,
                "description": post.body,
                "tags": list(post.tags),
            },
        }
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_adapters_youtube.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/adapters/youtube.py tests/test_adapters_youtube.py
git commit -m "feat: add YouTube adapter"
```

---

## Task 7: 凭证存储

**Files:**
- Create: `crosspost/crosspost/credentials.py`
- Test: `crosspost/tests/test_credentials.py`

- [ ] **Step 1: 写失败测试**

`tests/test_credentials.py`:
```python
import json
from crosspost.credentials import CredentialStore


def test_get_returns_empty_dict_when_missing(tmp_path):
    store = CredentialStore(tmp_path / "creds.json")
    assert store.get("x") == {}


def test_set_then_get(tmp_path):
    path = tmp_path / "creds.json"
    store = CredentialStore(path)
    store.set("x", {"api_key": "k"})
    assert store.get("x") == {"api_key": "k"}
    # 持久化:新实例能读到
    assert CredentialStore(path).get("x")["api_key"] == "k"


def test_has_true_only_when_all_keys_present(tmp_path):
    store = CredentialStore(tmp_path / "creds.json")
    store.set("x", {"api_key": "k", "api_secret": ""})
    assert store.has("x", ["api_key"]) is True
    assert store.has("x", ["api_key", "api_secret"]) is False
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_credentials.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/credentials.py`:
```python
from __future__ import annotations
import json
from pathlib import Path


class CredentialStore:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, platform: str) -> dict:
        return self._load().get(platform, {})

    def set(self, platform: str, data: dict) -> None:
        all_creds = self._load()
        all_creds[platform] = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(all_creds, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def has(self, platform: str, required_keys: list[str]) -> bool:
        creds = self.get(platform)
        return all(creds.get(k) for k in required_keys)
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_credentials.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/credentials.py tests/test_credentials.py
git commit -m "feat: add CredentialStore"
```

---

## Task 8: Publisher 基类

**Files:**
- Create: `crosspost/crosspost/publishers/base.py`

- [ ] **Step 1: 写实现**

`crosspost/publishers/base.py`:
```python
from __future__ import annotations
from typing import Protocol
from crosspost.models import Post, Result


class Publisher(Protocol):
    platform: str

    def login_status(self) -> bool:
        """该平台是否已就绪(浏览器:已登录;API:凭证齐全)。"""
        ...

    def publish(self, post: Post) -> Result:
        """发布已应用 overrides 的 Post,返回 Result。不得抛异常给编排器以外。"""
        ...
```

- [ ] **Step 2: 提交**

```powershell
git add crosspost/publishers/base.py
git commit -m "feat: add Publisher protocol"
```

---

## Task 9: 小红书 Publisher(子进程复用现有脚本)

**Files:**
- Create: `crosspost/crosspost/publishers/xhs.py`
- Test: `crosspost/tests/test_publisher_xhs.py`

通过 `subprocess` 调用 `publish_pipeline.py`。**关键:** 运行前清除代理环境变量(否则本地 CDP 走 SOCKS5 卡死,见 spec §6.1)。退出码 0=成功、1=未登录、2=失败。

- [ ] **Step 1: 写失败测试(用 monkeypatch 替换 subprocess.run,不真发)**

`tests/test_publisher_xhs.py`:
```python
import subprocess
import types
from crosspost.publishers.xhs import XhsPublisher
from crosspost.adapters.xhs import XhsAdapter
from crosspost.models import Post, Media


def _fake_run(returncode, stdout="", stderr=""):
    def run(cmd, capture_output, text, env, timeout, cwd):  # noqa: ARG001
        return types.SimpleNamespace(
            returncode=returncode, stdout=stdout, stderr=stderr
        )
    return run


def _post():
    return Post(title="标题", body="正文", tags=["AI"],
                media=[Media("a.jpg", "image")])


def test_build_command_includes_title_content_images(monkeypatch):
    captured = {}

    def run(cmd, **kw):
        captured["cmd"] = cmd
        captured["env"] = kw["env"]
        return types.SimpleNamespace(returncode=0,
                                     stdout="PUBLISH_STATUS: PUBLISHED",
                                     stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    pub = XhsPublisher(adapter=XhsAdapter())
    pub.publish(_post())
    cmd = captured["cmd"]
    assert "--title" in cmd and "标题" in cmd
    assert "--content" in cmd
    assert "--images" in cmd and "a.jpg" in cmd
    # 代理变量被清空
    assert captured["env"].get("HTTP_PROXY", "") == ""
    assert captured["env"].get("ALL_PROXY", "") == ""


def test_success_result(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        _fake_run(0, "PUBLISH_STATUS: PUBLISHED"))
    r = XhsPublisher(adapter=XhsAdapter()).publish(_post())
    assert r.status == "success"
    assert r.platform == "xhs"


def test_not_logged_in_result(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _fake_run(1, "NOT_LOGGED_IN"))
    r = XhsPublisher(adapter=XhsAdapter()).publish(_post())
    assert r.status == "needs_login"


def test_error_result(monkeypatch):
    monkeypatch.setattr(subprocess, "run",
                        _fake_run(2, "", "Error: boom"))
    r = XhsPublisher(adapter=XhsAdapter()).publish(_post())
    assert r.status == "failed"
    assert "boom" in r.message
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_xhs.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/publishers/xhs.py`:
```python
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
from crosspost.models import Post, Result
from crosspost.adapters.xhs import XhsAdapter

PIPELINE = Path(
    r"C:\Users\30488\.claude\skills\post-to-xhs\scripts\publish_pipeline.py"
)
PROXY_VARS = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"]
TIMEOUT_SECONDS = 300


def _clean_env() -> dict:
    env = dict(os.environ)
    for v in PROXY_VARS:
        env[v] = ""
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class XhsPublisher:
    platform = "xhs"

    def __init__(self, adapter: XhsAdapter, pipeline: Path = PIPELINE):
        self.adapter = adapter
        self.pipeline = pipeline

    def login_status(self) -> bool:
        # 登录态由浏览器决定,这里只确认脚本存在;实际登录在发布时检测。
        return self.pipeline.exists()

    def _build_cmd(self, payload: dict) -> list[str]:
        cmd = [sys.executable, str(self.pipeline),
               "--title", payload["title"],
               "--content", payload["content"],
               "--skip-file-check"]
        if payload["images"]:
            cmd += ["--images", *payload["images"]]
        if payload["video"]:
            cmd += ["--video", payload["video"]]
        return cmd

    def publish(self, post: Post) -> Result:
        payload = self.adapter.adapt(post)
        cmd = self._build_cmd(payload)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                env=_clean_env(), timeout=TIMEOUT_SECONDS,
                cwd=str(self.pipeline.parent),
            )
        except subprocess.TimeoutExpired:
            return Result(platform=self.platform, status="failed",
                          message="发布超时(浏览器引擎可能卡住)")
        if proc.returncode == 0:
            return Result(platform=self.platform, status="success",
                          message="已发布")
        if proc.returncode == 1:
            return Result(platform=self.platform, status="needs_login",
                          message="小红书未登录,请先在 Chrome 中登录")
        err = (proc.stderr or proc.stdout or "未知错误").strip()
        return Result(platform=self.platform, status="failed", message=err)
```

注:测试里 `subprocess.run` 被 monkeypatch 成关键字参数形式;实现中调用也用关键字传参,签名一致。

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_xhs.py -v`
Expected: PASS(4 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/publishers/xhs.py tests/test_publisher_xhs.py
git commit -m "feat: add Xiaohongshu publisher via subprocess reuse"
```

---

## Task 10: X Publisher(API)

**Files:**
- Create: `crosspost/crosspost/publishers/x.py`
- Test: `crosspost/tests/test_publisher_x.py`

用 `requests_oauthlib.OAuth1Session`:图片走 v1.1 `media/upload`,推文走 v2 `POST /2/tweets`。测试只验证「凭证缺失→needs_login」「成功路径返回带链接的 success(mock session)」。

- [ ] **Step 1: 写失败测试**

`tests/test_publisher_x.py`:
```python
from crosspost.publishers.x import XPublisher
from crosspost.adapters.x import XAdapter
from crosspost.models import Post
from crosspost.credentials import CredentialStore


def test_needs_login_when_no_creds(tmp_path):
    store = CredentialStore(tmp_path / "c.json")
    pub = XPublisher(adapter=XAdapter(), creds=store)
    r = pub.publish(Post(title="", body="hi"))
    assert r.status == "needs_login"


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self):
        self.posted = []

    def post(self, url, **kw):
        self.posted.append((url, kw))
        return _FakeResp(201, {"data": {"id": "12345"}})


def test_success_returns_url(tmp_path, monkeypatch):
    store = CredentialStore(tmp_path / "c.json")
    store.set("x", {"api_key": "a", "api_secret": "b",
                    "access_token": "c", "access_token_secret": "d"})
    pub = XPublisher(adapter=XAdapter(), creds=store)
    fake = _FakeSession()
    monkeypatch.setattr(pub, "_session", lambda: fake)
    r = pub.publish(Post(title="", body="hello"))
    assert r.status == "success"
    assert "12345" in r.url
    # 调了发推接口
    assert any("2/tweets" in url for url, _ in fake.posted)
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_x.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/publishers/x.py`:
```python
from __future__ import annotations
from requests_oauthlib import OAuth1Session
from crosspost.models import Post, Result
from crosspost.adapters.x import XAdapter
from crosspost.credentials import CredentialStore

REQUIRED = ["api_key", "api_secret", "access_token", "access_token_secret"]
UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
TWEETS_URL = "https://api.twitter.com/2/tweets"


class XPublisher:
    platform = "x"

    def __init__(self, adapter: XAdapter, creds: CredentialStore):
        self.adapter = adapter
        self.creds = creds

    def login_status(self) -> bool:
        return self.creds.has("x", REQUIRED)

    def _session(self) -> OAuth1Session:
        c = self.creds.get("x")
        return OAuth1Session(
            c["api_key"], c["api_secret"],
            c["access_token"], c["access_token_secret"],
        )

    def _upload_image(self, session, path: str) -> str:
        with open(path, "rb") as fh:
            resp = session.post(UPLOAD_URL, files={"media": fh})
        resp_json = resp.json()
        return str(resp_json["media_id_string"])

    def publish(self, post: Post) -> Result:
        if not self.login_status():
            return Result(platform=self.platform, status="needs_login",
                          message="X 凭证未配置,请在面板填写 API key")
        payload = self.adapter.adapt(post)
        session = self._session()
        try:
            media_ids = [self._upload_image(session, p)
                         for p in payload["image_paths"]]
            body = {"text": payload["text"]}
            if media_ids:
                body["media"] = {"media_ids": media_ids}
            resp = session.post(TWEETS_URL, json=body)
            if resp.status_code >= 300:
                return Result(platform=self.platform, status="failed",
                              message=f"X API {resp.status_code}: {resp.text}")
            tweet_id = resp.json()["data"]["id"]
            return Result(platform=self.platform, status="success",
                          url=f"https://x.com/i/web/status/{tweet_id}",
                          message="已发布")
        except Exception as e:  # noqa: BLE001 - 隔离给编排器,不外泄
            return Result(platform=self.platform, status="failed",
                          message=f"发布失败: {e}")
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_x.py -v`
Expected: PASS(2 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/publishers/x.py tests/test_publisher_x.py
git commit -m "feat: add X publisher (API)"
```

---

## Task 11: YouTube Publisher(API)

**Files:**
- Create: `crosspost/crosspost/publishers/youtube.py`
- Test: `crosspost/tests/test_publisher_youtube.py`

用 `google-api-python-client` 的 resumable 上传 + `google-auth-oauthlib` 走 OAuth。需要 `config/youtube_client_secret.json`(用户从 Google Cloud Console 下载)。测试只验证「缺 token 文件→needs_login」与「成功路径(mock 掉 build 出来的 service)」。

- [ ] **Step 1: 写失败测试**

`tests/test_publisher_youtube.py`:
```python
from crosspost.publishers.youtube import YoutubePublisher
from crosspost.adapters.youtube import YoutubeAdapter
from crosspost.models import Post, Media


def test_needs_login_when_no_token(tmp_path):
    pub = YoutubePublisher(
        adapter=YoutubeAdapter(),
        client_secret_file=tmp_path / "missing.json",
        token_file=tmp_path / "token.json",
    )
    r = pub.publish(Post(title="t", body="b",
                         media=[Media("v.mp4", "video")]))
    assert r.status == "needs_login"


class _FakeInsert:
    def next_chunk(self):
        return None, {"id": "vid123"}


class _FakeVideos:
    def insert(self, part, body, media_body):  # noqa: ARG002
        return _FakeInsert()


class _FakeService:
    def videos(self):
        return _FakeVideos()


def test_success_returns_url(tmp_path, monkeypatch):
    token = tmp_path / "token.json"
    token.write_text("{}", encoding="utf-8")
    pub = YoutubePublisher(
        adapter=YoutubeAdapter(),
        client_secret_file=tmp_path / "cs.json",
        token_file=token,
    )
    monkeypatch.setattr(pub, "_service", lambda: _FakeService())
    monkeypatch.setattr(pub, "_media_body", lambda path: "MEDIA")
    r = pub.publish(Post(title="t", body="b",
                         media=[Media("v.mp4", "video")]))
    assert r.status == "success"
    assert "vid123" in r.url
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_youtube.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/publishers/youtube.py`:
```python
from __future__ import annotations
from pathlib import Path
from crosspost.models import Post, Result
from crosspost.adapters.youtube import YoutubeAdapter

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YoutubePublisher:
    platform = "youtube"

    def __init__(self, adapter: YoutubeAdapter,
                 client_secret_file, token_file):
        self.adapter = adapter
        self.client_secret_file = Path(client_secret_file)
        self.token_file = Path(token_file)

    def login_status(self) -> bool:
        return self.token_file.exists()

    def authorize(self) -> None:
        """首次授权:打开浏览器走 OAuth,存 token。面板的“连接账号”调用它。"""
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_file), SCOPES)
        creds = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")

    def _service(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_file(
            str(self.token_file), SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=creds)

    def _media_body(self, path: str):
        from googleapiclient.http import MediaFileUpload
        return MediaFileUpload(path, chunksize=-1, resumable=True)

    def publish(self, post: Post) -> Result:
        if not self.login_status():
            return Result(platform=self.platform, status="needs_login",
                          message="YouTube 未授权,请在面板点“连接账号”")
        payload = self.adapter.adapt(post)
        try:
            service = self._service()
            request = service.videos().insert(
                part="snippet,status",
                body={"snippet": payload["snippet"],
                      "status": {"privacyStatus": "private"}},
                media_body=self._media_body(payload["video_path"]),
            )
            response = None
            while response is None:
                _, response = request.next_chunk()
            vid = response["id"]
            return Result(platform=self.platform, status="success",
                          url=f"https://youtu.be/{vid}",
                          message="已上传(默认 private,可在 YouTube 改公开)")
        except Exception as e:  # noqa: BLE001
            return Result(platform=self.platform, status="failed",
                          message=f"上传失败: {e}")
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_publisher_youtube.py -v`
Expected: PASS(2 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/publishers/youtube.py tests/test_publisher_youtube.py
git commit -m "feat: add YouTube publisher (API)"
```

---

## Task 12: 编排器

**Files:**
- Create: `crosspost/crosspost/orchestrator.py`
- Test: `crosspost/tests/test_orchestrator.py`

`publish_all(post, platforms, publishers, adapters)`:逐平台先 `adapter.validate`(skip→直接出 skipped 结果,不发),否则用 `post.for_platform()` 应用 overrides 后 `publisher.publish`,任何异常被捕获成 `failed`,一个平台失败不影响其他平台。

- [ ] **Step 1: 写失败测试**

`tests/test_orchestrator.py`:
```python
from crosspost.orchestrator import publish_all
from crosspost.models import Post, Result, Validation, Media


class _Adapter:
    def __init__(self, platform, validation):
        self.platform = platform
        self._v = validation

    def validate(self, post):
        return self._v


class _Publisher:
    def __init__(self, platform, result=None, raises=False):
        self.platform = platform
        self._result = result
        self._raises = raises
        self.called = False

    def publish(self, post):
        self.called = True
        if self._raises:
            raise RuntimeError("kaboom")
        return self._result


def test_skip_does_not_call_publisher():
    adapters = {"youtube": _Adapter("youtube", Validation("skip", "需要视频"))}
    pub = _Publisher("youtube")
    results = publish_all(Post(title="t", body="b"), ["youtube"],
                          {"youtube": pub}, adapters)
    assert pub.called is False
    assert results[0].status == "skipped"
    assert results[0].message == "需要视频"


def test_failure_isolated_between_platforms():
    adapters = {
        "x": _Adapter("x", Validation("ok")),
        "xhs": _Adapter("xhs", Validation("ok")),
    }
    publishers = {
        "x": _Publisher("x", raises=True),
        "xhs": _Publisher("xhs", Result("xhs", "success", url="u")),
    }
    post = Post(title="t", body="b", media=[Media("a.jpg", "image")])
    results = publish_all(post, ["x", "xhs"], publishers, adapters)
    by = {r.platform: r for r in results}
    assert by["x"].status == "failed"
    assert "kaboom" in by["x"].message
    assert by["xhs"].status == "success"


def test_applies_overrides_before_publish():
    seen = {}

    class CapturePub:
        platform = "x"
        def publish(self, post):
            seen["title"] = post.title
            return Result("x", "success")

    adapters = {"x": _Adapter("x", Validation("ok"))}
    post = Post(title="原", body="b", overrides={"x": {"title": "改"}})
    publish_all(post, ["x"], {"x": CapturePub()}, adapters)
    assert seen["title"] == "改"
```

- [ ] **Step 2: 运行确认失败**

Run: `.venv\Scripts\python.exe -m pytest tests/test_orchestrator.py -v`
Expected: FAIL —— `ModuleNotFoundError`

- [ ] **Step 3: 写实现**

`crosspost/orchestrator.py`:
```python
from __future__ import annotations
from crosspost.models import Post, Result


def publish_all(post: Post, platforms: list[str],
                publishers: dict, adapters: dict) -> list[Result]:
    results: list[Result] = []
    for platform in platforms:
        adapter = adapters.get(platform)
        publisher = publishers.get(platform)
        if adapter is None or publisher is None:
            results.append(Result(platform=platform, status="failed",
                                  message="未注册的平台"))
            continue
        validation = adapter.validate(post)
        if validation.status == "skip":
            results.append(Result(platform=platform, status="skipped",
                                  message=validation.message))
            continue
        try:
            results.append(publisher.publish(post.for_platform(platform)))
        except Exception as e:  # noqa: BLE001 - 隔离每个平台
            results.append(Result(platform=platform, status="failed",
                                  message=f"发布异常: {e}"))
    return results
```

- [ ] **Step 4: 运行确认通过**

Run: `.venv\Scripts\python.exe -m pytest tests/test_orchestrator.py -v`
Expected: PASS(3 passed)

- [ ] **Step 5: 提交**

```powershell
git add crosspost/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator with per-platform isolation"
```

---

## Task 13: 平台装配(registry)

**Files:**
- Create: `crosspost/crosspost/registry.py`

把凭证、适配器、发布器装配成 `(adapters, publishers)` 两个 dict,供 app 使用。无独立单测(在 Task 14 的端到端冒烟里覆盖)。

- [ ] **Step 1: 写实现**

`crosspost/registry.py`:
```python
from __future__ import annotations
from pathlib import Path
from crosspost.credentials import CredentialStore
from crosspost.adapters.xhs import XhsAdapter
from crosspost.adapters.x import XAdapter
from crosspost.adapters.youtube import YoutubeAdapter
from crosspost.publishers.xhs import XhsPublisher
from crosspost.publishers.x import XPublisher
from crosspost.publishers.youtube import YoutubePublisher

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def build_registry():
    creds = CredentialStore(CONFIG_DIR / "credentials.json")
    yt_conf = creds.get("youtube")
    adapters = {
        "xhs": XhsAdapter(),
        "x": XAdapter(),
        "youtube": YoutubeAdapter(),
    }
    publishers = {
        "xhs": XhsPublisher(adapter=adapters["xhs"]),
        "x": XPublisher(adapter=adapters["x"], creds=creds),
        "youtube": YoutubePublisher(
            adapter=adapters["youtube"],
            client_secret_file=CONFIG_DIR / "youtube_client_secret.json",
            token_file=Path(yt_conf.get("token_file",
                            CONFIG_DIR / "youtube_token.json")),
        ),
    }
    return adapters, publishers, creds
```

- [ ] **Step 2: 冒烟验证可导入**

Run: `.venv\Scripts\python.exe -c "from crosspost.registry import build_registry; print(list(build_registry()[0]))"`
Expected: 输出 `['xhs', 'x', 'youtube']`

- [ ] **Step 3: 提交**

```powershell
git add crosspost/registry.py
git commit -m "feat: add platform registry assembly"
```

---

## Task 14: FastAPI 应用 + 路由

**Files:**
- Create: `crosspost/app.py`

端点:
- `GET /` → 返回 `web/index.html`
- `GET /api/platforms` → 列平台 + 登录状态
- `POST /api/validate` → 入参 `{post}`,返回每平台 `{status,message}`
- `POST /api/publish` → 入参 `{post, platforms}`,返回每平台 `Result`

- [ ] **Step 1: 写实现**

`crosspost/app.py`:
```python
from __future__ import annotations
from pathlib import Path
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
    media: list[MediaIn] = []
    tags: list[str] = []
    overrides: dict = {}


class PublishIn(BaseModel):
    post: PostIn
    platforms: list[str]


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
```

- [ ] **Step 2: 启动并冒烟 /api/platforms**

Run(后台启动):
```powershell
.venv\Scripts\python.exe -m uvicorn app:app --port 8765
```
另开请求(或浏览器访问):`http://127.0.0.1:8765/api/platforms`
Expected: 返回 JSON 数组,含 `xhs`/`x`/`youtube` 三项,各带 `ready` 布尔值。

- [ ] **Step 3: 提交**

```powershell
git add app.py
git commit -m "feat: add FastAPI app with platforms/validate/publish routes"
```

---

## Task 15: 前端面板

**Files:**
- Create: `crosspost/web/index.html`
- Create: `crosspost/web/app.js`
- Create: `crosspost/web/style.css`

界面:标题/正文/标签输入;媒体文件路径输入(每行一个本地路径,自动按扩展名判图/视频);平台勾选(显示就绪状态);"校验"按钮(显示每平台 ok/warn/skip);"发布"按钮(显示每平台结果 + 链接/原因)。不放 emoji(用文字状态标签)。

- [ ] **Step 1: 写 index.html**

`web/index.html`:
```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>跨平台发布</title>
  <link rel="stylesheet" href="/web/style.css">
</head>
<body>
  <main>
    <h1>跨平台发布</h1>
    <label>标题<input id="title" type="text"></label>
    <label>正文<textarea id="body" rows="6"></textarea></label>
    <label>标签(逗号分隔)<input id="tags" type="text" placeholder="AI, 出海"></label>
    <label>媒体文件路径(每行一个本地路径)
      <textarea id="media" rows="3"
        placeholder="C:\path\a.jpg&#10;C:\path\v.mp4"></textarea>
    </label>
    <fieldset>
      <legend>平台</legend>
      <div id="platforms"></div>
    </fieldset>
    <div class="actions">
      <button id="validate">校验</button>
      <button id="publish">发布</button>
    </div>
    <section id="results"></section>
  </main>
  <script src="/web/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 写 app.js**

`web/app.js`:
```javascript
const $ = (id) => document.getElementById(id);

function buildPost() {
  const tags = $("tags").value.split(",").map(s => s.trim()).filter(Boolean);
  const media = $("media").value.split("\n").map(s => s.trim()).filter(Boolean)
    .map(path => ({
      path,
      type: /\.(mp4|mov|avi|mkv|webm)$/i.test(path) ? "video" : "image",
    }));
  return { title: $("title").value, body: $("body").value, tags, media, overrides: {} };
}

function selectedPlatforms() {
  return [...document.querySelectorAll(".pf:checked")].map(c => c.value);
}

async function loadPlatforms() {
  const res = await fetch("/api/platforms").then(r => r.json());
  $("platforms").innerHTML = res.map(p => `
    <label class="pf-row">
      <input class="pf" type="checkbox" value="${p.platform}" checked>
      ${p.platform}
      <span class="${p.ready ? "ok" : "warn"}">
        ${p.ready ? "就绪" : "未连接/未登录"}
      </span>
    </label>`).join("");
}

function renderRows(rows) {
  $("results").innerHTML = rows.map(r => `
    <div class="result ${r.status}">
      <strong>${r.platform}</strong>
      <span>${r.status}</span>
      ${r.url ? `<a href="${r.url}" target="_blank">查看</a>` : ""}
      <span class="msg">${r.message || ""}</span>
    </div>`).join("");
}

$("validate").onclick = async () => {
  const out = await fetch("/api/validate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildPost()),
  }).then(r => r.json());
  renderRows(Object.entries(out).map(([platform, v]) =>
    ({ platform, status: v.status, message: v.message })));
};

$("publish").onclick = async () => {
  $("results").innerHTML = "发布中…";
  const out = await fetch("/api/publish", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post: buildPost(), platforms: selectedPlatforms() }),
  }).then(r => r.json());
  renderRows(out);
};

loadPlatforms();
```

- [ ] **Step 3: 写 style.css**

`web/style.css`:
```css
* { box-sizing: border-box; }
body { font-family: system-ui, "Microsoft YaHei", sans-serif;
       background: #f5f5f7; color: #1d1d1f; margin: 0; }
main { max-width: 640px; margin: 0 auto; padding: 32px 20px; }
h1 { font-size: 22px; }
label { display: block; margin: 14px 0; font-size: 14px; }
input[type=text], textarea {
  width: 100%; padding: 8px 10px; margin-top: 4px;
  border: 1px solid #d2d2d7; border-radius: 8px; font-size: 14px; }
fieldset { border: 1px solid #d2d2d7; border-radius: 10px; margin: 16px 0; }
.pf-row { display: flex; align-items: center; gap: 8px; }
.actions { display: flex; gap: 12px; margin: 16px 0; }
button { padding: 10px 22px; border: none; border-radius: 8px;
         background: #1d1d1f; color: #fff; font-size: 14px; cursor: pointer; }
button:hover { background: #333; }
.result { display: flex; gap: 12px; align-items: center;
          padding: 10px 12px; margin: 6px 0; border-radius: 8px;
          background: #fff; border-left: 4px solid #d2d2d7; }
.result.success { border-left-color: #2e7d32; }
.result.failed { border-left-color: #c62828; }
.result.skipped { border-left-color: #9e9e9e; }
.result.needs_login, .result.warn { border-left-color: #ef6c00; }
.ok { color: #2e7d32; } .warn { color: #ef6c00; }
.msg { color: #6e6e73; font-size: 13px; }
```

- [ ] **Step 4: 手动验证面板**

Run: `.venv\Scripts\python.exe -m uvicorn app:app --port 8765`
浏览器打开 `http://127.0.0.1:8765/`
Expected: 看到表单 + 三个平台勾选项(带就绪状态)。填一段纯文字、不选媒体,点"校验":xhs 显示 skip(需要图/视频)、x 显示 ok、youtube 显示 skip(需要视频)。

- [ ] **Step 5: 提交**

```powershell
git add web/
git commit -m "feat: add local web panel (validate + publish UI)"
```

---

## Task 16: 端到端真实发布验证(手动,逐平台)

**Files:** 无新文件;这是交付前的真实验证(见用户偏好:交付前必须亲自完整验证、自动化先做最小端到端)。

- [ ] **Step 1: 全量单测通过**

Run: `.venv\Scripts\python.exe -m pytest -v`
Expected: 全绿(约 28 passed)。

- [ ] **Step 2: 小红书真实发布(图文)**

前置:在 Chrome 中已登录小红书,且 Chrome 以 CDP 调试端口启动(同 `post-to-xhs` 平时用法)。
操作:面板填标题+正文+一张本地图片路径,只勾选 xhs,点发布。
Expected:`xhs` 返回 `success`;小红书后台/App 能看到这条笔记。若 `needs_login`,先登录再试。

- [ ] **Step 3: 小红书真实发布(视频)**

操作:媒体填一个本地 `.mp4` 路径,只勾选 xhs,发布。
Expected:`xhs` 返回 `success`,视频笔记发布成功。

- [ ] **Step 4: X 真实发布(图文)**

前置:先查证 X API 当前免费/付费层是否支持发推(见 spec §6.3),拿到 4 个密钥填入 `config/credentials.json` 的 `x` 段。
操作:面板填正文(<280 字)+ 可选 1 张图,只勾选 x,发布。
Expected:`x` 返回 `success` 且给出 `https://x.com/...` 链接,推文可见。失败时按返回的 API 错误码排查(权限/限额)。

- [ ] **Step 5: YouTube 真实上传(视频)**

前置:Google Cloud Console 建项目→启用 YouTube Data API v3→建 OAuth 客户端(桌面应用)→下载为 `config/youtube_client_secret.json`。首次在命令行跑一次授权:
```powershell
.venv\Scripts\python.exe -c "from crosspost.registry import build_registry; _,p,_=build_registry(); p['youtube'].authorize()"
```
按浏览器提示授权,生成 `config/youtube_token.json`。
操作:面板填标题+描述+一个 `.mp4` 路径,只勾选 youtube,发布。
Expected:`youtube` 返回 `success`,YouTube 工作室能看到该视频(默认 private)。

- [ ] **Step 6: 三平台合并发布冒烟**

操作:填一份带图 + 视频的内容,三个平台全勾,发布。
Expected:xhs success;x success(用图,忽略视频);youtube success(用视频);各自结果 + 链接正确展示,任一失败不影响其余。

- [ ] **Step 7: 记录验证结果并提交**

把第 2–6 步的实际结果(成功/失败/截图链接)记到 `docs/verification-2026-06-04.md`,提交。
```powershell
git add docs/verification-2026-06-04.md
git commit -m "test: record end-to-end publish verification"
```

---

## 自检小结(对照 spec)

- 数据模型(§4)→ Task 2 ✓
- 适配层 + 校验前置 + 类型不匹配跳过(§5)→ Task 4/5/6 + orchestrator skip(Task 12)✓
- 浏览器引擎复用 + 代理坑规避(§6.1)→ Task 9 ✓
- API 凭证本地隔离 + 不进 git(§6.2)→ Task 1(.gitignore)+ Task 7 ✓
- 待查证项(§6.3)→ Task 16 Step 4 前置 ✓
- 错误处理 + 平台间隔离 + 汇总(§7)→ Task 12 + 各 publisher 的 try ✓
- 本地网页面板(交互)→ Task 14/15 ✓
- 验收标准(§9)→ Task 16 逐条覆盖 ✓
- 单平台重试:面板可单独勾一个平台再发,等价于重试 ✓
```
