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
    assert any("2/tweets" in url for url, _ in fake.posted)
