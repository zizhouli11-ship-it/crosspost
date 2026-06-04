"""精简的同步 CDP(Chrome DevTools Protocol)客户端。

只实现浏览器自动化发布需要的最小能力:连接到一个已开启远程调试端口的
Chrome、执行 JS、导航、给文件上传控件塞本地文件。供抖音/视频号这类没有
开放发布 API、只能走浏览器的平台复用。

依赖 websockets 的同步客户端(websockets.sync.client),本机已装。
连接方式与 post-to-xhs 的 cdp_publish 一致(同步 send/recv)。
"""
from __future__ import annotations
import json
import time
import urllib.request
from typing import Any, Optional

from websockets.sync.client import connect as ws_connect


class CDPError(Exception):
    pass


class CDPClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9222,
                 command_timeout: float = 30.0):
        self.host = host
        self.port = port
        self.command_timeout = command_timeout
        self.ws = None
        self._msg_id = 0

    @property
    def _base(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ---- 发现 / 连接 ----------------------------------------------------
    def list_targets(self) -> list:
        with urllib.request.urlopen(f"{self._base}/json", timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def is_up(self) -> bool:
        """Chrome 调试端口是否可达(便宜的检查,不验证登录态)。"""
        try:
            self.list_targets()
            return True
        except Exception:
            return False

    def connect(self, url_prefix: str = "") -> str:
        """连接到一个 page 类型的标签页;优先 url 以 url_prefix 开头的那个,
        否则取第一个 page。返回所连标签页的当前 url。"""
        targets = self.list_targets()
        pages = [t for t in targets if t.get("type") == "page"]
        if not pages:
            raise CDPError("没有可用的浏览器标签页(page target)")
        chosen = None
        if url_prefix:
            for t in pages:
                if (t.get("url") or "").startswith(url_prefix):
                    chosen = t
                    break
        chosen = chosen or pages[0]
        ws_url = chosen.get("webSocketDebuggerUrl")
        if not ws_url:
            raise CDPError("标签页缺少 webSocketDebuggerUrl")
        self.ws = ws_connect(ws_url, max_size=None)
        return chosen.get("url", "")

    def disconnect(self) -> None:
        if self.ws:
            try:
                self.ws.close()
            finally:
                self.ws = None

    # ---- 底层命令 -------------------------------------------------------
    def send(self, method: str, params: Optional[dict] = None,
             timeout: Optional[float] = None) -> dict:
        if not self.ws:
            raise CDPError("未连接,先调用 connect()")
        self._msg_id += 1
        message_id = self._msg_id
        msg = {"id": message_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        deadline = time.monotonic() + max(0.1, float(timeout or self.command_timeout))
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CDPError(f"等待 {method} 响应超时")
            raw = self.ws.recv(timeout=max(0.1, remaining))
            data = json.loads(raw)
            if data.get("id") == message_id:
                if "error" in data:
                    raise CDPError(f"CDP error on {method}: {data['error']}")
                return data.get("result", {})
            # 否则是事件,忽略继续等

    # ---- 高层便捷封装 ---------------------------------------------------
    def evaluate(self, expression: str, await_promise: bool = False) -> Any:
        """执行 JS 并按值返回结果。"""
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        })
        if result.get("exceptionDetails"):
            raise CDPError(f"JS 异常: {result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def navigate(self, url: str) -> None:
        self.send("Page.enable")
        self.send("Page.navigate", {"url": url})

    def set_file_input(self, selector: str, paths: list) -> None:
        """给页面上匹配 selector 的 <input type=file> 塞入本地文件(绝对路径)。"""
        self.send("DOM.enable")
        root = self.send("DOM.getDocument", {"depth": 0})
        root_id = root["root"]["nodeId"]
        found = self.send("DOM.querySelector",
                          {"nodeId": root_id, "selector": selector})
        node_id = found.get("nodeId")
        if not node_id:
            raise CDPError(f"找不到文件上传控件: {selector}")
        self.send("DOM.setFileInputFiles",
                  {"files": list(paths), "nodeId": node_id})

    def wait_for_js(self, expression: str, timeout: float = 30.0,
                    interval: float = 0.5) -> bool:
        """轮询直到 JS 表达式为真,或超时。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.evaluate(expression):
                return True
            time.sleep(interval)
        return False
