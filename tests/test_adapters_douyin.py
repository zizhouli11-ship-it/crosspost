from crosspost.adapters.douyin import DouyinAdapter
from crosspost.models import Post, Media


def test_skip_when_no_video():
    a = DouyinAdapter()
    v = a.validate(Post(title="t", body="b", media=[Media("a.jpg", "image")]))
    assert v.status == "skip"
    assert "视频" in v.message


def test_ok_with_video():
    a = DouyinAdapter()
    assert a.validate(Post(title="t", body="b",
                           media=[Media("v.mp4", "video")])).status == "ok"


def test_adapt_caption_with_tags():
    a = DouyinAdapter()
    p = Post(title="标题", body="正文", tags=["AI", "出海"],
             media=[Media("v.mp4", "video")])
    payload = a.adapt(p)
    assert payload["video_path"] == "v.mp4"
    assert payload["title"] == "标题"
    assert payload["caption"] == "正文 #AI #出海"
