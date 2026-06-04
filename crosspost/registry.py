from __future__ import annotations
from pathlib import Path
from crosspost.credentials import CredentialStore
from crosspost.adapters.xhs import XhsAdapter
from crosspost.adapters.x import XAdapter
from crosspost.adapters.youtube import YoutubeAdapter
from crosspost.publishers.xhs import XhsPublisher
from crosspost.publishers.x import XPublisher
from crosspost.publishers.youtube import YoutubePublisher

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def build_registry():
    creds = CredentialStore(CONFIG_DIR / "credentials.json")
    yt_conf = creds.get("youtube")
    adapters = {
        "xhs": XhsAdapter(),
        "x": XAdapter(),
        "youtube": YoutubeAdapter(),
    }
    publishers = {
        "xhs": XhsPublisher(adapter=adapters["xhs"]),
        "x": XPublisher(adapter=adapters["x"], creds=creds),
        "youtube": YoutubePublisher(
            adapter=adapters["youtube"],
            client_secret_file=CONFIG_DIR / "youtube_client_secret.json",
            token_file=Path(yt_conf.get("token_file",
                            str(CONFIG_DIR / "youtube_token.json"))),
        ),
    }
    return adapters, publishers, creds
