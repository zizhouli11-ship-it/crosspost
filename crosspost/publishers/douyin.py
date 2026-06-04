"""抖音发布器(浏览器自动化,走 CDP)。

抖音开放平台的发布能力对个人不可行,所以走浏览器自动化:连接到一个已经
登录抖音、并开启了远程调试端口(9222)的 Chrome,在创作者后台上传页完成
上传与发布。CDP 底层管道见 crosspost/cdp.py。

重要:下面 SELECTORS 里的选择器是初版猜测,抖音创作者后台经常改版,
需要对着真实页面用 probe() 调一轮再定。改选择器时只动这个字典即可。
"""
from __future__ import annotations
import time

from crosspost.cdp import CDPClient, CDPError
from crosspost.models import Post, Result
from crosspost.adapters.douyin import DouyinAdapter

UPLOAD_URL = "https://creator.douyin.com/creator-micro/content/upload"

# 待 live 调试确认的选择器集中在此
SELECTORS = {
    # 视频文件上传控件
    "file_input": 'input[type="file"]',
    # 已登录标志:登录后页面通常有头像/发布按钮;未登录会有“登录”入口
    "login_marker": '.semi-avatar, [class*="avatar"]',
    # 作品描述输入框(富文本编辑器)
    "caption_editor": '[class*="editor"] [contenteditable="true"], .zone-container',
    # 发布按钮(文案“发布”)
    "publish_button": 'button',
    # 上传完成标志(出现封面/进度 100% 等)
    "upload_done_marker": '[class*="success"], [class*="finish"]',
}


class DouyinPublisher:
    platform = "douyin"

    def __init__(self, adapter: DouyinAdapter, host: str = "127.0.0.1",
                 port: int = 9222, auto_publish: bool = True):
        self.adapter = adapter
        self.host = host
        self.port = port
        self.auto_publish = auto_publish

    def login_status(self) -> bool:
        """便宜的就绪检查:调试端口是否可达。真正的登录态在 publish 时检测。"""
        return CDPClient(self.host, self.port).is_up()

    def probe(self) -> dict:
        """live 调试用:连接并打开上传页,回报当前 url、标题、各关键选择器是否命中。
        第一轮最小端到端就先跑它,确认能连上、能定位元素,再做真正上传。"""
        client = CDPClient(self.host, self.port)
        if not client.is_up():
            return {"ok": False, "message": "Chrome 调试端口(9222)不可达,请用带 --remote-debugging-port=9222 的 Chrome 打开并登录抖音"}
        try:
            client.connect(url_prefix="https://creator.douyin.com")
            client.navigate(UPLOAD_URL)
            client.wait_for_js("document.readyState === 'complete'", timeout=15)
            time.sleep(2)
            found = {}
            for name, sel in SELECTORS.items():
                expr = "!!document.querySelector(%s)" % _js_str(sel)
                try:
                    found[name] = bool(client.evaluate(expr))
                except CDPError:
                    found[name] = False
            return {
                "ok": True,
                "url": client.evaluate("location.href"),
                "title": client.evaluate("document.title"),
                "selectors_found": found,
            }
        finally:
            client.disconnect()

    def publish(self, post: Post) -> Result:
        payload = self.adapter.adapt(post)
        client = CDPClient(self.host, self.port)
        if not client.is_up():
            return Result(platform=self.platform, status="needs_login",
                          message="未检测到调试中的 Chrome(9222),请用带远程调试端口的 Chrome 打开并登录抖音")
        try:
            client.connect(url_prefix="https://creator.douyin.com")
            client.navigate(UPLOAD_URL)
            if not client.wait_for_js("document.readyState === 'complete'", timeout=20):
                return self._fail("页面加载超时")
            time.sleep(2)
            # 登录检测
            if not client.evaluate("!!document.querySelector(%s)" % _js_str(SELECTORS["login_marker"])):
                return Result(platform=self.platform, status="needs_login",
                              message="抖音未登录,请先在该 Chrome 里登录创作者后台")
            # 上传视频
            client.set_file_input(SELECTORS["file_input"], [payload["video_path"]])
            if not client.wait_for_js(
                    "!!document.querySelector(%s)" % _js_str(SELECTORS["upload_done_marker"]),
                    timeout=180):
                return self._fail("视频上传/转码超时(或上传完成标志选择器需调整)")
            # 填文案
            caption = payload["caption"] or payload["title"]
            if caption:
                _fill_caption(client, caption)
            if not self.auto_publish:
                return Result(platform=self.platform, status="success",
                              message="已填好内容(未点发布,preview 模式)")
            # 点发布
            if not _click_publish(client):
                return self._fail("找不到发布按钮(选择器需调整)")
            time.sleep(3)
            return Result(platform=self.platform, status="success",
                          message="已点击发布(请到抖音确认作品状态)")
        except CDPError as e:
            return self._fail(str(e))
        except Exception as e:  # noqa: BLE001
            return self._fail(f"发布异常: {e}")
        finally:
            client.disconnect()

    def _fail(self, msg: str) -> Result:
        return Result(platform=self.platform, status="failed", message=msg)


def _js_str(s: str) -> str:
    """把字符串安全地嵌进 JS 源码(用 JSON 字面量)。"""
    import json
    return json.dumps(s)


def _fill_caption(client: CDPClient, caption: str) -> None:
    sel = SELECTORS["caption_editor"]
    js = (
        "(function(){var el=document.querySelector(%s);"
        "if(!el)return false;el.focus();"
        "document.execCommand&&document.execCommand('insertText',false,%s);"
        "el.dispatchEvent(new Event('input',{bubbles:true}));return true;})()"
        % (_js_str(sel), _js_str(caption))
    )
    client.evaluate(js)


def _click_publish(client: CDPClient) -> bool:
    """在所有按钮里找文案为“发布”的那个并点击。"""
    js = (
        "(function(){var bs=[].slice.call(document.querySelectorAll('button'));"
        "var t=bs.find(function(b){return (b.innerText||'').trim()==='发布';});"
        "if(!t)return false;t.click();return true;})()"
    )
    return bool(client.evaluate(js))
