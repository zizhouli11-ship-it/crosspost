import json
from crosspost.credentials import CredentialStore


def test_get_returns_empty_dict_when_missing(tmp_path):
    store = CredentialStore(tmp_path / "creds.json")
    assert store.get("x") == {}


def test_set_then_get(tmp_path):
    path = tmp_path / "creds.json"
    store = CredentialStore(path)
    store.set("x", {"api_key": "k"})
    assert store.get("x") == {"api_key": "k"}
    assert CredentialStore(path).get("x")["api_key"] == "k"


def test_has_true_only_when_all_keys_present(tmp_path):
    store = CredentialStore(tmp_path / "creds.json")
    store.set("x", {"api_key": "k", "api_secret": ""})
    assert store.has("x", ["api_key"]) is True
    assert store.has("x", ["api_key", "api_secret"]) is False
