import requests

from .config import config


def telegram(text):
    if not (config.telegram_token and config.telegram_chat_id):
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{config.telegram_token}/sendMessage", timeout=20,
                          json={"chat_id": config.telegram_chat_id, "text": text, "disable_web_page_preview": True})
        return r.ok
    except Exception:
        return False
