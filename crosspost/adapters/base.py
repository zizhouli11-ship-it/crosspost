from __future__ import annotations
from typing import Protocol
from crosspost.models import Post, Validation


class Adapter(Protocol):
    platform: str

    def validate(self, post: Post) -> Validation:
        """发布前校验该平台是否可发;返回 ok / warn / skip。"""
        ...

    def adapt(self, post: Post) -> dict:
        """把(已应用 overrides 的)Post 翻译成该平台 payload dict。"""
        ...


def join_tags(tags: list[str], prefix: str = "#", sep: str = " ") -> str:
    """["AI","出海"] -> "#AI #出海" """
    return sep.join(f"{prefix}{t.lstrip('#')}" for t in tags)
