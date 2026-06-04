from __future__ import annotations
from pathlib import Path
from crosspost.models import Post, Result
from crosspost.adapters.youtube import YoutubeAdapter

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YoutubePublisher:
    platform = "youtube"

    def __init__(self, adapter: YoutubeAdapter,
                 client_secret_file, token_file):
        self.adapter = adapter
        self.client_secret_file = Path(client_secret_file)
        self.token_file = Path(token_file)

    def login_status(self) -> bool:
        return self.token_file.exists()

    def authorize(self) -> None:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.client_secret_file), SCOPES)
        creds = flow.run_local_server(port=0)
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(creds.to_json(), encoding="utf-8")

    def _service(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_file(
            str(self.token_file), SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        return build("youtube", "v3", credentials=creds)

    def _media_body(self, path: str):
        from googleapiclient.http import MediaFileUpload
        return MediaFileUpload(path, chunksize=-1, resumable=True)

    def publish(self, post: Post) -> Result:
        if not self.login_status():
            return Result(platform=self.platform, status="needs_login",
                          message="YouTube wei shou quan, qing dian lian jie zhang hao")
        payload = self.adapter.adapt(post)
        try:
            service = self._service()
            request = service.videos().insert(
                part="snippet,status",
                body={"snippet": payload["snippet"],
                      "status": {"privacyStatus": "private"}},
                media_body=self._media_body(payload["video_path"]),
            )
            response = None
            while response is None:
                _, response = request.next_chunk()
            vid = response["id"]
            return Result(platform=self.platform, status="success",
                          url=f"https://youtu.be/{vid}",
                          message="已上传(默认 private,可在 YouTube 改公开)")
        except Exception as e:  # noqa: BLE001
            return Result(platform=self.platform, status="failed",
                          message=f"上传失败: {e}")
