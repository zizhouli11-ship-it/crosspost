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
