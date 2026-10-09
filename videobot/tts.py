"""Text-to-speech. Default: Microsoft Edge neural voices via the free `edge-tts` package
(unofficial, no key; works well for Urdu ur-PK and English). `silent` is for tests."""
import asyncio
import json
import subprocess

from .config import config


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


async def _edge(text, path):
    import edge_tts
    await edge_tts.Communicate(text, config.voice, rate=config.voice_rate).save(str(path))


def speak(text, path):
    """Writes an mp3 for `text` to `path` and returns its length in seconds."""
    if config.tts_provider == "silent":
        secs = max(1.5, len(text.split()) / 2.3)  # ~ speaking pace
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                        "-t", f"{secs:.2f}", "-q:a", "9", str(path)], check=True)
    else:
        for attempt in range(3):
            try:
                asyncio.run(_edge(text, path))
                break
            except Exception:
                if attempt == 2:
                    raise
    return duration(path)
