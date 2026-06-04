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
