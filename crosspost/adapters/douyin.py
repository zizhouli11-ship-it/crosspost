from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags


class DouyinAdapter:
    platform = "douyin"

    def validate(self, post: Post) -> Validation:
        if not post.videos():
            return Validation(status="skip", message="抖音需要一个视频文件")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        caption = post.body
        if post.tags:
            caption = f"{caption} {join_tags(post.tags)}".strip()
        return {
            "video_path": post.videos()[0].path,
            "title": post.title,
            "caption": caption,
        }
