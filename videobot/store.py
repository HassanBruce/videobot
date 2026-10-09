"""SQLite queue: topics → videos."""
import sqlite3

from .config import config

_conn = None


def db():
    global _conn
    if _conn is None:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(config.data_dir / "videobot.sqlite")
        _conn.row_factory = sqlite3.Row
        _conn.executescript("""
        CREATE TABLE IF NOT EXISTS topics (
          id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL DEFAULT 'queued',        -- queued | done | failed
          created_at TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS videos (
          id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER, title TEXT, folder TEXT, video TEXT,
          seconds REAL, yt_id TEXT, fb_id TEXT,
          status TEXT NOT NULL DEFAULT 'made',          -- made | uploaded | approved | failed
          error TEXT, created_at TEXT NOT NULL DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
        """)
    return _conn


def reset():
    global _conn
    if _conn:
        _conn.close()
    _conn = None


def add_topics(topics):
    n = 0
    for t in topics:
        cur = db().execute("INSERT OR IGNORE INTO topics (topic) VALUES (?)", (t.strip(),))
        n += cur.rowcount
    db().commit()
    return n


def next_topic():
    return db().execute("SELECT * FROM topics WHERE status='queued' ORDER BY id LIMIT 1").fetchone()


def all_topics():
    return [r["topic"] for r in db().execute("SELECT topic FROM topics ORDER BY id")]


def titles():
    return [r["title"] for r in db().execute("SELECT title FROM videos WHERE title IS NOT NULL ORDER BY id")]


def set_topic(tid, status):
    db().execute("UPDATE topics SET status=? WHERE id=?", (status, tid))
    db().commit()


def add_video(**v):
    cols = ",".join(v)
    cur = db().execute(f"INSERT INTO videos ({cols}) VALUES ({','.join('?' * len(v))})", tuple(v.values()))
    db().commit()
    return cur.lastrowid


def update_video(vid, **v):
    db().execute(f"UPDATE videos SET {', '.join(f'{k}=?' for k in v)} WHERE id=?", (*v.values(), vid))
    db().commit()


def video(vid):
    return db().execute("SELECT * FROM videos WHERE id=?", (vid,)).fetchone()


def videos(limit=50):
    return db().execute("SELECT * FROM videos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def kv_get(k, d=None):
    r = db().execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return r["v"] if r else d


def kv_set(k, v):
    db().execute("INSERT INTO kv (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, str(v)))
    db().commit()
