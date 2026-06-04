import json
from crosspost.cdp import CDPClient


class FakeWS:
    def __init__(self, responses):
        self.sent = []
        self._responses = list(responses)

    def send(self, raw):
        self.sent.append(raw)

    def recv(self, timeout=None):
        return self._responses.pop(0)

    def close(self):
        pass


def test_send_skips_events_and_returns_matching_result():
    c = CDPClient()
    c.ws = FakeWS([
        json.dumps({"method": "Some.event", "params": {}}),
        json.dumps({"id": 1, "result": {"ok": True}}),
    ])
    res = c.send("Test.method", {"a": 1})
    assert res == {"ok": True}
    sent = json.loads(c.ws.sent[0])
    assert sent["method"] == "Test.method"
    assert sent["id"] == 1
    assert sent["params"] == {"a": 1}


def test_evaluate_returns_value():
    c = CDPClient()
    c.ws = FakeWS([json.dumps({"id": 1, "result": {"result": {"value": 42}}})])
    assert c.evaluate("1+41") == 42


def test_is_up_false_when_port_closed():
    # 59999 端口基本不会有人监听 -> 连接被拒,快速返回 False
    assert CDPClient(port=59999).is_up() is False
