from __future__ import annotations
import os
import requests
from crosspost.models import Post, Result
from crosspost.adapters.tiktok import TiktokAdapter
from crosspost.credentials import CredentialStore

INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"


class TiktokPublisher:
    platform = "tiktok"

    def __init__(self, adapter: TiktokAdapter, creds: CredentialStore):
        self.adapter = adapter
        self.creds = creds

    def login_status(self) -> bool:
        return self.creds.has("tiktok", ["access_token"])

    def _access_token(self) -> str:
        return self.creds.get("tiktok").get("access_token", "")

    def _refresh(self) -> bool:
        c = self.creds.get("tiktok")
        if not (c.get("refresh_token") and c.get("client_key")
                and c.get("client_secret")):
            return False
        resp = requests.post(TOKEN_URL, data={
            "client_key": c["client_key"],
            "client_secret": c["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": c["refresh_token"],
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if resp.status_code >= 300:
            return False
        data = resp.json()
        c["access_token"] = data.get("access_token", c.get("access_token"))
        if data.get("refresh_token"):
            c["refresh_token"] = data["refresh_token"]
        self.creds.set("tiktok", c)
        return True

    def _init_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    def publish(self, post: Post) -> Result:
        if not self.login_status():
            return Result(platform=self.platform, status="needs_login",
                          message="TikTok 未配置,请在面板填写 access_token")
        payload = self.adapter.adapt(post)
        try:
            return self._upload_to_inbox(payload)
        except Exception as e:  # noqa: BLE001
            return Result(platform=self.platform, status="failed",
                          message=f"上传失败: {e}")

    def _upload_to_inbox(self, payload: dict) -> Result:
        path = payload["video_path"]
        size = os.path.getsize(path)
        init_body = {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            }
        }
        resp = requests.post(INBOX_INIT_URL, json=init_body,
                             headers=self._init_headers())
        if resp.status_code == 401 and self._refresh():
            resp = requests.post(INBOX_INIT_URL, json=init_body,
                                 headers=self._init_headers())
        if resp.status_code >= 300:
            return Result(platform=self.platform, status="failed",
                          message=f"TikTok init {resp.status_code}: {resp.text}")
        data = resp.json().get("data", {})
        upload_url = data.get("upload_url")
        if not upload_url:
            return Result(platform=self.platform, status="failed",
                          message=f"TikTok 未返回 upload_url: {resp.text}")
        with open(path, "rb") as fh:
            video_bytes = fh.read()
        put = requests.put(upload_url, data=video_bytes, headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        })
        if put.status_code >= 300:
            return Result(platform=self.platform, status="failed",
                          message=f"TikTok 视频上传 {put.status_code}: {put.text}")
        return Result(platform=self.platform, status="success",
                      message="已上传到 TikTok 草稿箱(请在 App 里完成发布)")
