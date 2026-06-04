from __future__ import annotations
from typing import Protocol
from crosspost.models import Post, Result


class Publisher(Protocol):
    platform: str

    def login_status(self) -> bool:
        """该平台是否已就绪(浏览器:已登录;API:凭证齐全)。"""
        ...

    def publish(self, post: Post) -> Result:
        """发布已应用 overrides 的 Post,返回 Result。不得抛异常给编排器以外。"""
        ...
