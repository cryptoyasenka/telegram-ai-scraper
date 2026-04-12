import sqlite3
import json
from pathlib import Path
from typing import Optional
import config
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS channels (
            id TEXT PRIMARY KEY,
            username TEXT,
            title TEXT,
            total_posts INTEGER DEFAULT 0,
            last_message_id INTEGER DEFAULT 0,
            last_scraped TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            date TEXT,
            sender_name TEXT,
            text TEXT,
            media_type TEXT,
            media_path TEXT,
            media_size INTEGER,
            voice_transcript TEXT,
            views INTEGER,
            forwards INTEGER,
            reactions TEXT,
            reply_to INTEGER,
            content_length INTEGER DEFAULT 0,
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            UNIQUE(channel_id, message_id)
        );

        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            domain TEXT,
            context_text TEXT,
            date TEXT,
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            UNIQUE(channel_id, message_id, url)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel_id);
        CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
        CREATE INDEX IF NOT EXISTS idx_messages_media ON messages(media_type);
        CREATE INDEX IF NOT EXISTS idx_links_channel ON links(channel_id);
        CREATE INDEX IF NOT EXISTS idx_links_domain ON links(domain);
        CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);
    """)
    # Idempotent migrations for existing DBs
    existing_cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
    if "media_size" not in existing_cols:
        conn.execute("ALTER TABLE messages ADD COLUMN media_size INTEGER")

    ch_cols = {r[1] for r in conn.execute("PRAGMA table_info(channels)").fetchall()}
    if "download_dir" not in ch_cols:
        conn.execute("ALTER TABLE channels ADD COLUMN download_dir TEXT")

    conn.commit()
    conn.close()


def get_channel_dir(channel: dict) -> Path:
    """Return the channel's storage directory (custom or default)."""
    if channel.get("download_dir"):
        return Path(channel["download_dir"])
    return config.DATA_DIR / (channel["username"] or channel["id"])


def update_download_dir(channel_id: str, download_dir: str):
    conn = get_connection()
    conn.execute(
        "UPDATE channels SET download_dir = ? WHERE id = ?",
        (download_dir or None, channel_id),
    )
    conn.commit()
    conn.close()


def add_channel(channel_id: str, username: str, title: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO channels (id, username, title) VALUES (?, ?, ?)",
        (channel_id, username, title),
    )
    conn.commit()
    conn.close()


def get_channel(channel_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_channel_by_username(username: str) -> Optional[dict]:
    username = username.lstrip("@")
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM channels WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_channels() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM channels ORDER BY title").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_channel(channel_id: str, **kwargs):
    conn = get_connection()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [channel_id]
    conn.execute(f"UPDATE channels SET {sets} WHERE id = ?", values)
    conn.commit()
    conn.close()


def insert_message(channel_id: str, message_id: int, date: str,
                   sender_name: str, text: str, media_type: Optional[str],
                   media_path: Optional[str], views: Optional[int],
                   forwards: Optional[int], reactions: Optional[str],
                   reply_to: Optional[int]):
    conn = get_connection()
    content_length = len(text) if text else 0
    conn.execute(
        """INSERT OR IGNORE INTO messages
           (channel_id, message_id, date, sender_name, text, media_type,
            media_path, views, forwards, reactions, reply_to, content_length)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (channel_id, message_id, date, sender_name, text, media_type,
         media_path, views, forwards, reactions, reply_to, content_length),
    )
    conn.commit()
    conn.close()


def insert_messages_batch(messages: list[dict]):
    if not messages:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT OR IGNORE INTO messages
           (channel_id, message_id, date, sender_name, text, media_type,
            media_path, media_size, views, forwards, reactions, reply_to, content_length)
           VALUES (:channel_id, :message_id, :date, :sender_name, :text, :media_type,
                   :media_path, :media_size, :views, :forwards, :reactions, :reply_to, :content_length)""",
        messages,
    )
    conn.commit()
    conn.close()


def insert_links_batch(links: list[dict]):
    if not links:
        return
    conn = get_connection()
    conn.executemany(
        """INSERT OR IGNORE INTO links
           (channel_id, message_id, url, domain, context_text, date)
           VALUES (:channel_id, :message_id, :url, :domain, :context_text, :date)""",
        links,
    )
    conn.commit()
    conn.close()


def update_transcript(channel_id: str, message_id: int, transcript: str):
    conn = get_connection()
    conn.execute(
        "UPDATE messages SET voice_transcript = ? WHERE channel_id = ? AND message_id = ?",
        (transcript, channel_id, message_id),
    )
    conn.commit()
    conn.close()


def get_messages_needing_media(channel_id: str, media_types: list[str]) -> list[dict]:
    if not media_types:
        return []
    placeholders = ",".join("?" * len(media_types))
    conn = get_connection()
    rows = conn.execute(
        f"""SELECT message_id, media_type FROM messages
            WHERE channel_id = ?
            AND media_type IN ({placeholders})
            AND media_path IS NULL
            ORDER BY message_id""",
        [channel_id, *media_types],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages_missing_size(channel_id: str) -> list[int]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT message_id FROM messages
           WHERE channel_id = ?
           AND media_type IS NOT NULL
           AND media_type NOT IN ('other')
           AND media_size IS NULL
           ORDER BY message_id""",
        (channel_id,),
    ).fetchall()
    conn.close()
    return [r["message_id"] for r in rows]


def update_media_sizes_batch(channel_id: str, items: list[tuple[int, int]]):
    if not items:
        return
    conn = get_connection()
    conn.executemany(
        "UPDATE messages SET media_size = ? WHERE channel_id = ? AND message_id = ?",
        [(size, channel_id, mid) for mid, size in items],
    )
    conn.commit()
    conn.close()


def update_media_path(channel_id: str, message_id: int, path: str):
    conn = get_connection()
    conn.execute(
        "UPDATE messages SET media_path = ? WHERE channel_id = ? AND message_id = ?",
        (path, channel_id, message_id),
    )
    conn.commit()
    conn.close()


def get_media_breakdown(channel_id: str) -> dict:
    """Return per-type breakdown: {media_type: {count, bytes, downloaded, pending_bytes}}."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT
               COALESCE(media_type, 'text') AS mt,
               COUNT(*) AS count,
               COALESCE(SUM(media_size), 0) AS bytes,
               SUM(CASE WHEN media_path IS NOT NULL THEN 1 ELSE 0 END) AS downloaded,
               COALESCE(SUM(CASE WHEN media_path IS NULL THEN media_size ELSE 0 END), 0) AS pending_bytes
           FROM messages
           WHERE channel_id = ?
           GROUP BY COALESCE(media_type, 'text')""",
        (channel_id,),
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        result[r["mt"]] = {
            "count": r["count"],
            "bytes": r["bytes"] or 0,
            "downloaded": r["downloaded"] or 0,
            "pending_bytes": r["pending_bytes"] or 0,
        }
    return result


def get_messages_without_transcript(channel_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM messages
           WHERE channel_id = ?
           AND media_type IN ('voice', 'video_note', 'video')
           AND voice_transcript IS NULL
           AND media_path IS NOT NULL
           ORDER BY date""",
        (channel_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages_for_export(channel_id: str, min_length: int = 0,
                            has_links: bool = False,
                            min_views: Optional[int] = None,
                            search: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM messages WHERE channel_id = ?"
    params: list = [channel_id]

    if min_length > 0:
        query += " AND content_length >= ?"
        params.append(min_length)

    if min_views is not None:
        query += " AND views >= ?"
        params.append(min_views)

    if search:
        query += " AND (text LIKE ? OR voice_transcript LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY date"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = [dict(r) for r in rows]

    if has_links:
        link_conn = get_connection()
        msg_ids_with_links = set()
        link_rows = link_conn.execute(
            "SELECT DISTINCT message_id FROM links WHERE channel_id = ?",
            (channel_id,),
        ).fetchall()
        link_conn.close()
        msg_ids_with_links = {r["message_id"] for r in link_rows}
        results = [m for m in results if m["message_id"] in msg_ids_with_links]

    return results


def get_links_for_channel(channel_id: str, search: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    if search:
        rows = conn.execute(
            """SELECT * FROM links WHERE channel_id = ?
               AND (url LIKE ? OR domain LIKE ? OR context_text LIKE ?)
               ORDER BY date""",
            (channel_id, f"%{search}%", f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM links WHERE channel_id = ? ORDER BY date",
            (channel_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_all(query: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT m.*, c.title as channel_title, c.username as channel_username
           FROM messages m
           JOIN channels c ON m.channel_id = c.id
           WHERE m.text LIKE ? OR m.voice_transcript LIKE ?
           ORDER BY m.date DESC
           LIMIT 50""",
        (f"%{query}%", f"%{query}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_links(query: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT l.*, c.title as channel_title
           FROM links l
           JOIN channels c ON l.channel_id = c.id
           WHERE l.url LIKE ? OR l.domain LIKE ? OR l.context_text LIKE ?
           ORDER BY l.date DESC
           LIMIT 50""",
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = get_connection()
    channels = conn.execute("SELECT COUNT(*) as c FROM channels").fetchone()["c"]
    messages = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
    links = conn.execute("SELECT COUNT(*) as c FROM links").fetchone()["c"]
    voice = conn.execute(
        "SELECT COUNT(*) as c FROM messages WHERE media_type IN ('voice', 'video_note')"
    ).fetchone()["c"]
    transcribed = conn.execute(
        "SELECT COUNT(*) as c FROM messages WHERE voice_transcript IS NOT NULL"
    ).fetchone()["c"]
    conn.close()
    return {
        "channels": channels,
        "messages": messages,
        "links": links,
        "voice_video": voice,
        "transcribed": transcribed,
    }
