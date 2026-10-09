"""Writes the video plan (script) with Gemini through its OpenAI-compatible API."""
import json
import re
import time

import requests

from .config import config

LANG_NAME = {"ur": "Urdu (in Urdu script, natural spoken Pakistani Urdu; keep English technical terms in English letters)",
             "en": "simple English", "hi": "Hindi (Devanagari script)"}


def chat(messages, temperature=0.7, retries=3):
    if not config.ai_api_key:
        raise RuntimeError("AI_API_KEY missing in .env")
    url = config.ai_base_url.rstrip("/") + "/chat/completions"
    last = None
    for attempt in range(retries):
        r = requests.post(url, timeout=120, headers={"Authorization": f"Bearer {config.ai_api_key}"},
                          json={"model": config.ai_model, "messages": messages, "temperature": temperature,
                                "response_format": {"type": "json_object"}})
        if r.status_code in (429, 500, 502, 503):
            last = f"AI HTTP {r.status_code}: {r.text[:200]}"
            time.sleep(5 * (attempt + 1))
            continue
        if not r.ok:
            raise RuntimeError(f"AI HTTP {r.status_code}: {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError(last or "AI failed")


def parse_json(text):
    t = re.sub(r"^```(?:json)?\s*|```\s*$", "", text.strip())
    return json.loads(t[t.find("{"): t.rfind("}") + 1])


def validate_plan(p):
    for k in ("title", "description", "slides"):
        if not p.get(k):
            raise ValueError(f"plan missing {k}")
    if not (3 <= len(p["slides"]) <= 20):
        raise ValueError("plan needs 3-20 slides")
    for s in p["slides"]:
        if not s.get("heading") or not s.get("narration"):
            raise ValueError("each slide needs heading and narration")
        s.setdefault("bullets", [])
        s["bullets"] = [str(b) for b in s["bullets"]][:5]
        s.setdefault("code", "")
    p["tags"] = [str(t) for t in p.get("tags", [])][:15]
    p["title"] = p["title"][:95]
    p.setdefault("thumbnail_text", p["title"][:40])
    p.setdefault("fb_post", p["description"][:400])
    return p


def make_plan(topic, previous_titles=()):
    words = int(config.target_minutes * 130)
    prompt = f"""You are the scriptwriter for the YouTube channel "{config.channel_name}" ({config.niche}).
Playlist: "{config.playlist_name}". Already published: {json.dumps(list(previous_titles)[-20:])}

Make ONE educational video about: "{topic}"

Requirements:
- Teach something concrete and correct that a beginner can do today (commands, steps, real examples). No hype, no fake numbers, no "guaranteed income" claims.
- 6-12 slides. Each slide: a short English heading, 2-4 short English bullets (max 8 words each), optional "code" (max 8 lines, real working commands/code), and "narration" spoken in {LANG_NAME.get(config.narration_lang, 'English')}.
- Total narration about {words} words. First slide = hook + what they will learn. Last slide = recap + ask them to subscribe for the next part.
- Narration must explain the slide in a friendly teacher voice; never read code symbol by symbol.

Return ONLY JSON:
{{"title": "YouTube title, max 90 chars, may mix Urdu/English",
 "description": "YouTube description, 3-6 lines, include what they learn",
 "tags": ["..."],
 "thumbnail_text": "3-5 punchy English words",
 "fb_post": "Facebook post text (2-4 lines) for this video",
 "slides": [{{"heading": "", "bullets": [""], "code": "", "narration": ""}}]}}"""
    text = chat([{"role": "user", "content": prompt}])
    return validate_plan(parse_json(text))


def suggest_topics(n, existing):
    prompt = f"""Channel: "{config.channel_name}" — {config.niche}. Playlist: "{config.playlist_name}".
Existing/queued topics: {json.dumps(list(existing)[-50:])}
Suggest {n} NEW video topics that continue a beginner-to-job-ready learning path (ordered, each builds on the last), each specific and practical.
Return ONLY JSON: {{"topics": ["..."]}}"""
    data = parse_json(chat([{"role": "user", "content": prompt}], temperature=0.8))
    return [t.strip() for t in data.get("topics", []) if t and t.strip()][:n]
