from __future__ import annotations
from crosspost.models import Post, Result


def publish_all(post: Post, platforms: list[str],
                publishers: dict, adapters: dict) -> list[Result]:
    results: list[Result] = []
    for platform in platforms:
        adapter = adapters.get(platform)
        publisher = publishers.get(platform)
        if adapter is None or publisher is None:
            results.append(Result(platform=platform, status="failed",
                                  message="未注册的平台"))
            continue
        validation = adapter.validate(post)
        if validation.status == "skip":
            results.append(Result(platform=platform, status="skipped",
                                  message=validation.message))
            continue
        try:
            results.append(publisher.publish(post.for_platform(platform)))
        except Exception as e:  # noqa: BLE001
            results.append(Result(platform=platform, status="failed",
                                  message=f"发布异常: {e}"))
    return results
