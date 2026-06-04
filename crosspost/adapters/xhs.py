from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags

TITLE_MAX = 20


class XhsAdapter:
    platform = "xhs"

    def validate(self, post: Post) -> Validation:
        if not post.media:
            return Validation(status="skip", message="小红书需要至少一张图或一个视频")
        if len(post.title) > TITLE_MAX:
            return Validation(status="warn",
                              message=f"标题超过 {TITLE_MAX} 字,可能被截断")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        content = post.body
        if post.tags:
            content = f"{content}\n{join_tags(post.tags)}"
        videos = post.videos()
        return {
            "title": post.title,
            "content": content,
            "images": [m.path for m in post.images()],
            "video": videos[0].path if videos else None,
        }
