"""Settings from environment / .env (no extra dependency)."""
import os
import re
from pathlib import Path


def _load_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$", line)
        if m and m.group(1) not in os.environ:
            os.environ[m.group(1)] = m.group(2).strip().strip("'\"")


_load_env()


def env(key, default=""):
    return os.environ.get(key, default)


class Config:
    def __init__(self):
        # Channel
        self.channel_name = env("CHANNEL_NAME", "Road to AI Automation")
        self.niche = env("NICHE", "AI automation and cloud engineering for beginners in Pakistan")
        self.playlist_name = env("PLAYLIST_NAME", "Road to AI automation and cloud engineer")
        # ur = Urdu narration (Urdu script for the voice), en = English, hi = Hindi
        self.narration_lang = env("NARRATION_LANG", "ur")
        self.voice = env("VOICE", {"ur": "ur-PK-AsadNeural", "en": "en-US-AndrewNeural", "hi": "hi-IN-MadhurNeural"}.get(self.narration_lang, "en-US-AndrewNeural"))
        self.voice_rate = env("VOICE_RATE", "+0%")
        self.tts_provider = env("TTS_PROVIDER", "edge")  # edge | silent (tests)
        self.video_format = env("VIDEO_FORMAT", "landscape")  # landscape | vertical
        self.target_minutes = float(env("TARGET_MINUTES", "4"))
        self.accent = env("ACCENT_COLOR", "#2D6CDF")

        # AI (Gemini via OpenAI-compatible endpoint; free tier is fine for public content)
        self.ai_base_url = env("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
        self.ai_api_key = env("AI_API_KEY")
        self.ai_model = env("AI_MODEL", "gemini-2.5-flash")

        # YouTube (OAuth refresh token from scripts/youtube_auth.py)
        self.yt_client_id = env("YT_CLIENT_ID")
        self.yt_client_secret = env("YT_CLIENT_SECRET")
        self.yt_refresh_token = env("YT_REFRESH_TOKEN")
        self.yt_privacy = env("YT_PRIVACY", "private")  # unverified API projects are forced to private anyway
        self.yt_category = env("YT_CATEGORY_ID", "27")  # 27 = Education

        # Facebook Page
        self.fb_page_id = env("FB_PAGE_ID")
        self.fb_page_token = env("FB_PAGE_TOKEN")
        self.fb_graph_version = env("FB_GRAPH_VERSION", "v23.0")
        # false = Facebook post only after you run `approve <id>`
        self.fb_auto_publish = env("FB_AUTO_PUBLISH", "false").lower() == "true"

        # Schedule: make + upload one video on these days at this hour (Pakistan time)
        self.schedule_days = [d.strip().lower() for d in env("SCHEDULE_DAYS", "mon,wed,fri").split(",") if d.strip()]
        self.schedule_hour_pkt = int(env("SCHEDULE_HOUR_PKT", "18"))

        # Telegram (optional)
        self.telegram_token = env("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = env("TELEGRAM_CHAT_ID")

        self.data_dir = Path(env("DATA_DIR", "./data"))
        self.output_dir = Path(env("OUTPUT_DIR", str(self.data_dir / "videos")))

    @property
    def size(self):
        return (1080, 1920) if self.video_format == "vertical" else (1920, 1080)


config = Config()
