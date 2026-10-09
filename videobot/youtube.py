"""YouTube upload with plain HTTP (OAuth refresh token + resumable upload). Free quota."""
import json
from pathlib import Path

import requests

from .config import config

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
THUMB_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"


def enabled():
    return bool(config.yt_client_id and config.yt_client_secret and config.yt_refresh_token)


def access_token():
    r = requests.post(TOKEN_URL, timeout=30, data={
        "client_id": config.yt_client_id, "client_secret": config.yt_client_secret,
        "refresh_token": config.yt_refresh_token, "grant_type": "refresh_token"})
    if not r.ok:
        raise RuntimeError(f"YouTube token refresh failed: {r.status_code} {r.text[:200]}")
    return r.json()["access_token"]


def upload(video_path, plan, thumbnail=None):
    """Returns the YouTube video id."""
    token = access_token()
    video_path = Path(video_path)
    meta = {
        "snippet": {"title": plan["title"], "description": plan["description"], "tags": plan.get("tags", []),
                    "categoryId": config.yt_category, "defaultAudioLanguage": config.narration_lang},
        "status": {"privacyStatus": config.yt_privacy, "selfDeclaredMadeForKids": False,
                   # synthetic voice: be transparent (YouTube's altered/synthetic content flag)
                   "containsSyntheticMedia": True},
    }
    init = requests.post(UPLOAD_URL, timeout=60, params={"uploadType": "resumable", "part": "snippet,status"},
                         headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                                  "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(video_path.stat().st_size)},
                         data=json.dumps(meta))
    if not init.ok:
        raise RuntimeError(f"YouTube upload init failed: {init.status_code} {init.text[:300]}")
    with open(video_path, "rb") as f:
        put = requests.put(init.headers["Location"], data=f, timeout=1800,
                           headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"})
    if not put.ok:
        raise RuntimeError(f"YouTube upload failed: {put.status_code} {put.text[:300]}")
    vid = put.json()["id"]
    if thumbnail:
        try:
            with open(thumbnail, "rb") as f:
                requests.post(THUMB_URL, params={"videoId": vid}, data=f, timeout=120,
                              headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"}).raise_for_status()
        except Exception:
            pass  # custom thumbnails need a phone-verified channel; not fatal
    return vid
