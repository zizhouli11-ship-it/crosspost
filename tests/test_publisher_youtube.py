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
