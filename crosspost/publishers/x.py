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
        except Exception as e:  # noqa: BLE001
            return Result(platform=self.platform, status="failed",
                          message=f"发布失败: {e}")
