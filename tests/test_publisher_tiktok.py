import crosspost.publishers.tiktok as tk
from crosspost.publishers.tiktok import TiktokPublisher
from crosspost.adapters.tiktok import TiktokAdapter
from crosspost.models import Post, Media
from crosspost.credentials import CredentialStore


def test_needs_login_when_no_token(tmp_path):
    store = CredentialStore(tmp_path / "c.json")
    pub = TiktokPublisher(adapter=TiktokAdapter(), creds=store)
    r = pub.publish(Post(title="", body="hi", media=[Media("v.mp4", "video")]))
    assert r.status == "needs_login"


class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_success_uploads_to_inbox(tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"abc")  # 3 bytes
    store = CredentialStore(tmp_path / "c.json")
    store.set("tiktok", {"access_token": "tok"})
    pub = TiktokPublisher(adapter=TiktokAdapter(), creds=store)

    calls = {}

    def fake_post(url, json=None, headers=None, data=None):
        calls["init_url"] = url
        calls["auth"] = headers.get("Authorization")
        return _Resp(200, {"data": {"upload_url": "https://up", "publish_id": "p1"}})

    def fake_put(url, data=None, headers=None):
        calls["put_url"] = url
        calls["range"] = headers.get("Content-Range")
        return _Resp(200)

    monkeypatch.setattr(tk.requests, "post", fake_post)
    monkeypatch.setattr(tk.requests, "put", fake_put)

    r = pub.publish(Post(title="", body="hi", media=[Media(str(video), "video")]))
    assert r.status == "success"
    assert "inbox" in calls["init_url"]
    assert calls["auth"] == "Bearer tok"
    assert calls["put_url"] == "https://up"
    assert calls["range"] == "bytes 0-2/3"


def test_init_error_returns_failed(tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"abc")
    store = CredentialStore(tmp_path / "c.json")
    store.set("tiktok", {"access_token": "tok"})
    pub = TiktokPublisher(adapter=TiktokAdapter(), creds=store)

    def fake_post(url, json=None, headers=None, data=None):
        return _Resp(403, {}, text="forbidden")

    monkeypatch.setattr(tk.requests, "post", fake_post)
    r = pub.publish(Post(title="", body="hi", media=[Media(str(video), "video")]))
    assert r.status == "failed"
    assert "403" in r.message
