"""Facebook Page video post via Graph API (Page access token)."""
import requests

from .config import config


def enabled():
    return bool(config.fb_page_id and config.fb_page_token)


def upload(video_path, plan):
    """Returns the Facebook video id."""
    url = f"https://graph.facebook.com/{config.fb_graph_version}/{config.fb_page_id}/videos"
    text = plan.get("fb_post") or plan["description"]
    with open(video_path, "rb") as f:
        r = requests.post(url, timeout=1800,
                          data={"access_token": config.fb_page_token, "title": plan["title"], "description": text},
                          files={"source": ("video.mp4", f, "video/mp4")})
    if not r.ok:
        raise RuntimeError(f"Facebook upload failed: {r.status_code} {r.text[:300]}")
    return r.json().get("id")
