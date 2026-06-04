from __future__ import annotations
from crosspost.models import Post, Validation

TITLE_MAX = 100


class YoutubeAdapter:
    platform = "youtube"

    def validate(self, post: Post) -> Validation:
        if not post.videos():
            return Validation(status="skip", message="YouTube 需要一个视频文件")
        if len(post.title) > TITLE_MAX:
            return Validation(status="warn",
                              message=f"标题超过 {TITLE_MAX} 字,会被截断")
        return Validation(status="ok")

    def adapt(self, post: Post) -> dict:
        return {
            "video_path": post.videos()[0].path,
            "snippet": {
                "title": post.title,
                "description": post.body,
                "tags": list(post.tags),
            },
        }
