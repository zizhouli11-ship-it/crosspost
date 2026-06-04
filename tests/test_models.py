from crosspost.models import Post, Media, Result, Validation


def test_media_defaults():
    m = Media(path="a.jpg", type="image")
    assert m.path == "a.jpg"
    assert m.type == "image"


def test_post_holds_fields():
    p = Post(
        title="标题",
        body="正文",
        media=[Media(path="a.jpg", type="image")],
        tags=["AI", "出海"],
        overrides={"xhs": {"title": "小红书标题"}},
    )
    assert p.title == "标题"
    assert p.tags == ["AI", "出海"]
    assert p.overrides["xhs"]["title"] == "小红书标题"


def test_post_optional_fields_default_empty():
    p = Post(title="t", body="b")
    assert p.media == []
    assert p.tags == []
    assert p.overrides == {}


def test_result_skipped():
    r = Result(platform="youtube", status="skipped", message="需要视频")
    assert r.status == "skipped"
    assert r.url is None
    assert r.message == "需要视频"


def test_validation_ok():
    v = Validation(status="ok", message="")
    assert v.status == "ok"
