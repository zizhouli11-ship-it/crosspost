from __future__ import annotations
from crosspost.models import Post, Validation
from crosspost.adapters.base import join_tags

CAPTION_MAX = 2200


class TiktokAdapter:
    platform = "tiktok"

    def validate(self, post: Post) -> Validation:
        if not post.videos():
            return Validation(status="skip", message="TikTok 需要一个视频文件")
        if len(post.body) > CAPTION_MAX:
            return Validation(status="warn",
                              message=f"文案超过 {CAPTION_MAX} 字,会被截断")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        caption = post.body
        if post.tags:
            caption = f"{caption} {join_tags(post.tags)}".strip()
        return {
            "video_path": post.videos()[0].path,
            "caption": caption,
        }
