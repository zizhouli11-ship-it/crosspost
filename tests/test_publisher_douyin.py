from crosspost.publishers.douyin import DouyinPublisher
from crosspost.adapters.douyin import DouyinAdapter
from crosspost.models import Post, Media


def test_login_status_false_when_chrome_down():
    pub = DouyinPublisher(adapter=DouyinAdapter(), port=59999)
    assert pub.login_status() is False


def test_publish_needs_login_when_chrome_down():
    pub = DouyinPublisher(adapter=DouyinAdapter(), port=59999)
    r = pub.publish(Post(title="t", body="b", media=[Media("v.mp4", "video")]))
    assert r.status == "needs_login"
    assert r.platform == "douyin"
