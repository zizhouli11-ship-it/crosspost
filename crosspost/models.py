from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

MediaType = Literal["image", "video"]
ResultStatus = Literal["success", "failed", "skipped", "needs_login"]
ValidationStatus = Literal["ok", "warn", "skip"]


@dataclass
class Media:
    path: str
    type: MediaType


@dataclass
class Post:
    title: str
    body: str
    media: list[Media] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    overrides: dict[str, dict] = field(default_factory=dict)

    def images(self) -> list[Media]:
        return [m for m in self.media if m.type == "image"]

    def videos(self) -> list[Media]:
        return [m for m in self.media if m.type == "video"]

    def for_platform(self, platform: str) -> "Post":
        ov = self.overrides.get(platform, {})
        return Post(
            title=ov.get("title", self.title),
            body=ov.get("body", self.body),
            media=list(self.media),
            tags=ov.get("tags", self.tags),
            overrides={},
        )


@dataclass
class Result:
    platform: str
    status: ResultStatus
    url: str | None = None
    message: str | None = None


@dataclass
class Validation:
    status: ValidationStatus
    message: str = ""
