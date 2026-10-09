"""Builds the final mp4: one segment per slide (image + its narration), then concatenated."""
import json
import re
import subprocess
from pathlib import Path

from . import slides, tts
from .config import config


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60] or "video"


def _run(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def build(plan, workdir):
    """Returns dict(video=Path, thumbnail=Path, seconds=float)."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    W, H = config.size
    segments, total = [], 0.0
    n = len(plan["slides"])
    for i, s in enumerate(plan["slides"]):
        png = slides.render_slide(s, i, n, workdir / f"slide_{i:02d}.png")
        mp3 = workdir / f"voice_{i:02d}.mp3"
        secs = tts.speak(s["narration"], mp3) + 0.6  # small breath between slides
        seg = workdir / f"seg_{i:02d}.mp4"
        _run(["-loop", "1", "-framerate", "30", "-i", str(png), "-i", str(mp3),
              "-af", "apad=pad_dur=0.6", "-t", f"{secs:.2f}",
              "-vf", f"scale={W}:{H},format=yuv420p,fade=t=in:st=0:d=0.25",
              "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-crf", "23",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2", "-shortest", str(seg)])
        segments.append(seg)
        total += secs

    listfile = workdir / "segments.txt"
    listfile.write_text("".join(f"file '{p.name}'\n" for p in segments), encoding="utf-8")
    out = workdir / f"{slugify(plan['title'])}.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", "-movflags", "+faststart", str(out)])
    thumb = slides.render_thumbnail(plan.get("thumbnail_text") or plan["title"], workdir / "thumbnail.jpg")
    for p in segments:
        p.unlink(missing_ok=True)
    return {"video": out, "thumbnail": thumb, "seconds": round(total, 1)}
