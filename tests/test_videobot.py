import json, os, shutil, tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

TMP = tempfile.mkdtemp()
os.environ.update(DATA_DIR=TMP, TTS_PROVIDER="silent", AI_API_KEY="k", YT_CLIENT_ID="cid", YT_CLIENT_SECRET="cs",
                  YT_REFRESH_TOKEN="rt", FB_PAGE_ID="123", FB_PAGE_TOKEN="pt", TELEGRAM_BOT_TOKEN="t", TELEGRAM_CHAT_ID="1",
                  SCHEDULE_DAYS="mon,wed,fri", SCHEDULE_HOUR_PKT="18")

from videobot import ai, pipeline, store, video  # noqa: E402
from videobot.config import config  # noqa: E402

PLAN = {"title": "Docker kya hai? Pehla container", "description": "Is video mein seekhein...", "tags": ["docker", "devops"],
        "thumbnail_text": "Docker Basics", "fb_post": "Naya video!",
        "slides": [{"heading": "Docker kya hai?", "bullets": ["Apps ko box mein pack karo"], "narration": "ڈوکر ایک ٹول ہے جو ایپس کو پیک کرتا ہے"},
                   {"heading": "Pehla command", "bullets": ["Install", "Run"], "code": "docker run hello-world", "narration": "اب ہم پہلا کمانڈ چلائیں گے"},
                   {"heading": "Recap", "bullets": ["Image vs container"], "narration": "سبسکرائب ضرور کریں"}]}


class Resp:
    def __init__(self, status=200, body=None, headers=None, text=""):
        self.status_code, self._body, self.headers, self.text = status, body, headers or {}, text or json.dumps(body)
    ok = property(lambda s: s.status_code < 400)
    def json(self): return self._body
    def raise_for_status(self):
        if not self.ok: raise RuntimeError(self.status_code)


calls = []
ai_reply = {"value": PLAN}


def fake_post(url, *a, **kw):
    calls.append(("POST", url, kw))
    if "chat/completions" in url:
        if ai_reply["value"] == "fail":
            return Resp(400, {"e": 1})
        content = json.dumps(ai_reply["value"], ensure_ascii=False)
        return Resp(200, {"choices": [{"message": {"content": "```json\n" + content + "\n```"}}]})
    if "oauth2.googleapis.com/token" in url:
        return Resp(200, {"access_token": "AT"})
    if "upload/youtube/v3/videos" in url:
        assert kw["headers"]["Authorization"] == "Bearer AT"
        meta = json.loads(kw["data"])
        assert meta["status"]["privacyStatus"] == "private"
        return Resp(200, {}, {"Location": "https://upload.example/session"})
    if "thumbnails/set" in url:
        return Resp(200, {})
    if "graph.facebook.com" in url:
        assert kw["data"]["access_token"] == "pt"
        return Resp(200, {"id": "fb999"})
    if "api.telegram.org" in url:
        return Resp(200, {"ok": True})
    raise AssertionError("unexpected " + url)


def fake_put(url, *a, **kw):
    calls.append(("PUT", url, kw))
    return Resp(200, {"id": "yt123"})


@mock.patch("requests.post", side_effect=fake_post)
@mock.patch("requests.put", side_effect=fake_put)
class VideoBotTest(unittest.TestCase):
    def setUp(self):
        calls.clear()
        ai_reply["value"] = PLAN

    def test_1_plan_parsing_and_validation(self, *_):
        p = ai.make_plan("Docker basics")
        self.assertEqual(len(p["slides"]), 3)
        self.assertEqual(p["slides"][0]["code"], "")
        with self.assertRaises(ValueError):
            ai.validate_plan({"title": "x", "description": "y", "slides": [{"heading": "a", "narration": "b"}]})

    def test_2_full_run_makes_video_uploads_private_and_waits_for_fb_approval(self, *_):
        store.add_topics(["Docker basics", "Dockerfile likhna", "Docker compose"])
        vid = pipeline.run_once()
        self.assertIsNotNone(vid)
        v = store.video(vid)
        self.assertEqual(v["yt_id"], "yt123")
        self.assertEqual(v["status"], "uploaded")
        self.assertIsNone(v["fb_id"])
        self.assertTrue(Path(v["video"]).exists())
        self.assertTrue((Path(v["folder"]) / "thumbnail.jpg").exists())
        # real video: has video+audio, about the narration length
        import subprocess
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", v["video"]],
                             capture_output=True, text=True).stdout.split()
        self.assertEqual(sorted(out), ["audio", "video"])
        tg = [c for c in calls if "telegram" in c[1]]
        self.assertTrue(any("youtu.be/yt123" in c[2]["json"]["text"] for c in tg))
        # approve → Facebook
        pipeline.approve(vid)
        self.assertEqual(store.video(vid)["fb_id"], "fb999")
        self.assertEqual(store.video(vid)["status"], "approved")
        # approving twice doesn't double-post
        n_fb = len([c for c in calls if "graph.facebook.com" in c[1]])
        pipeline.approve(vid)
        self.assertEqual(len([c for c in calls if "graph.facebook.com" in c[1]]), n_fb)

    def test_3_ai_failure_is_reported_not_crashing(self, *_):
        ai_reply["value"] = "fail"
        self.assertIsNone(pipeline.run_once())
        self.assertTrue(any("error" in c[2]["json"]["text"].lower() for c in calls if "telegram" in c[1]))
        failed = store.db().execute("SELECT COUNT(*) FROM topics WHERE status='queued'").fetchone()[0]
        self.assertGreaterEqual(failed, 1)  # topic stays queued (script failed before render)

    def test_4_schedule_runs_once_per_scheduled_day(self, *_):
        from videobot.pipeline import PKT
        wed_evening = datetime(2026, 10, 14, 19, tzinfo=PKT)
        tue_evening = datetime(2026, 10, 13, 19, tzinfo=PKT)
        wed_morning = datetime(2026, 10, 14, 9, tzinfo=PKT)
        self.assertTrue(pipeline.due(wed_evening))
        self.assertFalse(pipeline.due(tue_evening))
        self.assertFalse(pipeline.due(wed_morning))
        store.kv_set("last_run_day", "2026-10-14")
        self.assertFalse(pipeline.due(wed_evening))

    def test_5_vertical_format(self, *_):
        config.video_format = "vertical"
        try:
            out = video.build(PLAN, Path(TMP) / "vert")
            import subprocess
            wh = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height",
                                 "-of", "csv=p=0", str(out["video"])], capture_output=True, text=True).stdout.strip()
            self.assertEqual(wh, "1080,1920")
        finally:
            config.video_format = "landscape"


if __name__ == "__main__":
    unittest.main(verbosity=2)
