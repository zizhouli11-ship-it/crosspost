from crosspost.adapters.xhs import XhsAdapter
from crosspost.models import Post, Media


def test_skip_when_no_media():
    a = XhsAdapter()
    v = a.validate(Post(title="t", body="b"))
    assert v.status == "skip"
    assert "图" in v.message or "视频" in v.message


def test_warn_when_title_too_long():
    a = XhsAdapter()
    post = Post(title="一" * 21, body="b", media=[Media("a.jpg", "image")])
    v = a.validate(post)
    assert v.status == "warn"


def test_ok_with_image():
    a = XhsAdapter()
    post = Post(title="标题", body="b", media=[Media("a.jpg", "image")])
    assert a.validate(post).status == "ok"


def test_adapt_appends_tags_to_content_last_line():
    a = XhsAdapter()
    post = Post(title="标题", body="正文", tags=["AI", "出海"],
                media=[Media("a.jpg", "image")])
    payload = a.adapt(post)
    assert payload["title"] == "标题"
    assert payload["content"].endswith("#AI #出海")
    assert payload["content"].startswith("正文")
    assert payload["images"] == ["a.jpg"]
    assert payload["video"] is None


def test_adapt_video():
    a = XhsAdapter()
    post = Post(title="标题", body="正文", media=[Media("v.mp4", "video")])
    payload = a.adapt(post)
    assert payload["video"] == "v.mp4"
    assert payload["images"] == []
