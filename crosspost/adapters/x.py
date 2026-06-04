from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags

TWEET_MAX = 280
IMAGE_MAX = 4


def _text(post: Post) -> str:
    text = post.body
    if post.tags:
        text = f"{text}\n{join_tags(post.tags)}"
    return text


class XAdapter:
    platform = "x"

    def validate(self, post: Post) -> Validation:
        if len(_text(post)) > TWEET_MAX:
            return Validation(status="skip",
                              message=f"超过 {TWEET_MAX} 字,X 无法发布")
        if len(post.images()) > IMAGE_MAX:
            return Validation(status="warn",
                              message=f"图片多于 {IMAGE_MAX} 张,只取前 {IMAGE_MAX} 张")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        return {
            "text": _text(post),
            "image_paths": [m.path for m in post.images()][:IMAGE_MAX],
        }
