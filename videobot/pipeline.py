"""make → upload → (approve) → Facebook."""
import shutil
import time
from datetime import datetime, timedelta, timezone

from . import ai, facebook, notify, store, video, youtube
from .config import config

PKT = timezone(timedelta(hours=5))
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def log(msg):
    print(f"[{datetime.now(PKT):%Y-%m-%d %H:%M}] {msg}", flush=True)


def ensure_topics(min_queued=3):
    queued = store.db().execute("SELECT COUNT(*) FROM topics WHERE status='queued'").fetchone()[0]
    if queued >= min_queued:
        return 0
    new = ai.suggest_topics(10, store.all_topics())
    n = store.add_topics(new)
    log(f"Added {n} topic ideas to the queue.")
    return n


def make_one(topic_row=None):
    """Creates the next video from the queue. Returns the video id."""
    t = topic_row or store.next_topic()
    if not t:
        ensure_topics()
        t = store.next_topic()
    if not t:
        raise RuntimeError("No topics in queue. Add some: python -m videobot add \"topic\"")
    log(f"Writing script: {t['topic']}")
    plan = ai.make_plan(t["topic"], store.titles())
    folder = config.output_dir / f"{datetime.now(PKT):%Y%m%d-%H%M}-{video.slugify(plan['title'])}"
    try:
        out = video.build(plan, folder)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        store.set_topic(t["id"], "failed")
        raise
    store.set_topic(t["id"], "done")
    vid = store.add_video(topic_id=t["id"], title=plan["title"], folder=str(folder), video=str(out["video"]), seconds=out["seconds"])
    log(f"Video #{vid} ready ({out['seconds']:.0f}s): {out['video']}")
    return vid


def _plan(v):
    import json
    from pathlib import Path
    return json.loads((Path(v["folder"]) / "plan.json").read_text(encoding="utf-8"))


def upload(vid):
    v = store.video(vid)
    plan = _plan(v)
    msg = [f"🎬 Video #{vid} ready: {plan['title']} ({v['seconds']:.0f}s)"]
    if youtube.enabled():
        from pathlib import Path
        yt = youtube.upload(v["video"], plan, Path(v["folder"]) / "thumbnail.jpg")
        store.update_video(vid, yt_id=yt, status="uploaded")
        msg.append(f"YouTube ({config.yt_privacy}): https://youtu.be/{yt}\nDekh lo, theek ho to YouTube Studio mein Public kar do.")
    else:
        msg.append(f"YouTube keys nahi lagi. File: {v['video']}")
    if config.fb_auto_publish:
        approve(vid, notify_user=False)
        msg.append("Facebook: posted.")
    else:
        msg.append(f"Facebook pe dalne ke liye: python -m videobot approve {vid}")
    notify.telegram("\n".join(msg))
    log(" | ".join(msg))


def approve(vid, notify_user=True):
    v = store.video(vid)
    if not v:
        raise RuntimeError(f"No video #{vid}")
    if facebook.enabled() and not v["fb_id"]:
        fb = facebook.upload(v["video"], _plan(v))
        store.update_video(vid, fb_id=fb)
    store.update_video(vid, status="approved")
    if notify_user:
        notify.telegram(f"✅ Video #{vid} approved{' and posted on Facebook' if facebook.enabled() else ''}.")
    log(f"Video #{vid} approved.")


def run_once():
    """Make + upload one video; errors are reported, not raised."""
    try:
        ensure_topics()
        vid = make_one()
        upload(vid)
        return vid
    except Exception as e:
        store.db().execute("INSERT INTO videos (title, status, error) VALUES (?,?,?)", ("(failed)", "failed", str(e)[:500]))
        store.db().commit()
        notify.telegram(f"⚠️ Video bot error: {str(e)[:300]}")
        log(f"ERROR: {e}")
        return None


def due(now=None):
    """True once per scheduled day, at/after the scheduled hour (Pakistan time)."""
    now = now or datetime.now(PKT)
    day = DAYS[now.weekday()]
    key = now.strftime("%Y-%m-%d")
    return day in config.schedule_days and now.hour >= config.schedule_hour_pkt and store.kv_get("last_run_day") != key


def scheduler(poll_seconds=300):
    log(f"Scheduler: {','.join(config.schedule_days)} at {config.schedule_hour_pkt}:00 PKT")
    while True:
        now = datetime.now(PKT)
        if due(now):
            store.kv_set("last_run_day", now.strftime("%Y-%m-%d"))
            run_once()
        time.sleep(poll_seconds)
