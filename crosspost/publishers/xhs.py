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
