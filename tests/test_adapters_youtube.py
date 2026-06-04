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
