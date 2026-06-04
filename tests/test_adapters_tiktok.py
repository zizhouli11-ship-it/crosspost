from crosspost.adapters.tiktok import TiktokAdapter
from crosspost.models import Post, Media


def test_skip_when_no_video():
    a = TiktokAdapter()
    v = a.validate(Post(title="t", body="b", media=[Media("a.jpg", "image")]))
    assert v.status == "skip"
    assert "视频" in v.message


def test_ok_with_video():
    a = TiktokAdapter()
    assert a.validate(Post(title="t", body="b",
                           media=[Media("v.mp4", "video")])).status == "ok"


def test_warn_when_caption_too_long():
    a = TiktokAdapter()
    post = Post(title="", body="x" * 2201, media=[Media("v.mp4", "video")])
    assert a.validate(post).status == "warn"


def test_adapt_caption_with_tags():
    a = TiktokAdapter()
    p = Post(title="", body="hello", tags=["AI"],
             media=[Media("v.mp4", "video")])
    payload = a.adapt(p)
    assert payload["caption"] == "hello #AI"
    assert payload["video_path"] == "v.mp4"
