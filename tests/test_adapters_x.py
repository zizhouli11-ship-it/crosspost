from crosspost.adapters.x import XAdapter
from crosspost.models import Post, Media


def test_ok_text_only():
    a = XAdapter()
    assert a.validate(Post(title="t", body="hello")).status == "ok"


def test_skip_when_over_280():
    a = XAdapter()
    post = Post(title="", body="x" * 281)
    v = a.validate(post)
    assert v.status == "skip"


def test_warn_when_more_than_4_images():
    a = XAdapter()
    post = Post(title="", body="hi",
                media=[Media(f"{i}.jpg", "image") for i in range(5)])
    assert a.validate(post).status == "warn"


def test_adapt_builds_text_with_tags():
    a = XAdapter()
    post = Post(title="ignored", body="hello world", tags=["AI"])
    payload = a.adapt(post)
    assert payload["text"] == "hello world\n#AI"
    assert payload["image_paths"] == []


def test_adapt_caps_images_at_4():
    a = XAdapter()
    post = Post(title="", body="hi",
                media=[Media(f"{i}.jpg", "image") for i in range(6)])
    payload = a.adapt(post)
    assert len(payload["image_paths"]) == 4
