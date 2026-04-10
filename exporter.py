import json
from pathlib import Path
from typing import Optional

import config
import db


def _format_message_md(msg: dict, links: list[dict]) -> Optional[str]:
    parts = []

    date = msg.get("date", "")[:10]
    parts.append(f"### {date}")

    media_type = msg.get("media_type")
    if media_type == "voice":
        parts.append("[Голосовое]")
    elif media_type == "video_note":
        parts.append("[Видеокружочек]")
    elif media_type == "video":
        parts.append("[Видео]")
    elif media_type == "photo":
        parts.append("[Фото]")
    elif media_type == "document":
        parts.append("[Файл]")

    text = msg.get("text", "")
    if text:
        parts.append(text)

    transcript = msg.get("voice_transcript")
    if transcript:
        parts.append(f"\n> Транскрипция: {transcript}")

    msg_links = [l for l in links if l["message_id"] == msg["message_id"]]
    if msg_links:
        link_strs = [f"[{l['domain']}]({l['url']})" for l in msg_links]
        parts.append("Links: " + " | ".join(link_strs))

    meta = []
    if msg.get("views"):
        meta.append(f"views:{msg['views']}")
    if msg.get("reactions"):
        meta.append(msg["reactions"])
    if meta:
        parts.append(f"[{' | '.join(meta)}]")

    return "\n".join(parts)


def export_channel_md(channel_id: str, min_length: int = 0,
                       has_links: bool = False, min_views: Optional[int] = None,
                       search: Optional[str] = None) -> str:
    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found")

    messages = db.get_messages_for_export(
        channel_id, min_length=min_length, has_links=has_links,
        min_views=min_views, search=search,
    )
    all_links = db.get_links_for_channel(channel_id)
    total = db.get_connection().execute(
        "SELECT COUNT(*) as c FROM messages WHERE channel_id = ?", (channel_id,)
    ).fetchone()["c"]

    lines = [
        f"# {ch['title']} (@{ch['username']})",
        f"Экспортировано: {len(messages)} постов из {total}",
        "",
        "---",
        "",
    ]

    current_date = ""
    for msg in messages:
        formatted = _format_message_md(msg, all_links)
        if formatted:
            msg_date = msg.get("date", "")[:10]
            if msg_date != current_date:
                current_date = msg_date
                lines.append(f"\n## {current_date}\n")
            lines.append(formatted)
            lines.append("")

    return "\n".join(lines)


def export_channel_json(channel_id: str, min_length: int = 0,
                         has_links: bool = False, min_views: Optional[int] = None,
                         search: Optional[str] = None) -> str:
    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found")

    messages = db.get_messages_for_export(
        channel_id, min_length=min_length, has_links=has_links,
        min_views=min_views, search=search,
    )
    all_links = db.get_links_for_channel(channel_id)

    export_data = {
        "channel": {
            "id": ch["id"],
            "title": ch["title"],
            "username": ch["username"],
        },
        "total_exported": len(messages),
        "messages": [],
    }

    for msg in messages:
        msg_links = [l for l in all_links if l["message_id"] == msg["message_id"]]
        entry = {
            "date": msg["date"],
            "text": msg["text"],
            "media_type": msg["media_type"],
            "voice_transcript": msg["voice_transcript"],
            "links": [{"url": l["url"], "domain": l["domain"]} for l in msg_links],
            "views": msg["views"],
            "reactions": msg["reactions"],
        }
        export_data["messages"].append(entry)

    return json.dumps(export_data, ensure_ascii=False, indent=2)


def save_export(channel_id: str, **kwargs):
    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found")

    channel_dir = config.DATA_DIR / (ch["username"] or channel_id)
    channel_dir.mkdir(parents=True, exist_ok=True)

    md_content = export_channel_md(channel_id, **kwargs)
    md_path = channel_dir / "export.md"
    md_path.write_text(md_content, encoding="utf-8")

    json_content = export_channel_json(channel_id, **kwargs)
    json_path = channel_dir / "export.json"
    json_path.write_text(json_content, encoding="utf-8")

    return str(md_path), str(json_path)


def save_merged_export(min_length: int = 0, **kwargs):
    channels = db.get_all_channels()
    if not channels:
        return None

    all_lines = ["# Все каналы — merged export\n"]
    for ch in channels:
        try:
            md = export_channel_md(ch["id"], min_length=min_length, **kwargs)
            all_lines.append(md)
            all_lines.append("\n---\n")
        except Exception as e:
            all_lines.append(f"# {ch['title']} — ошибка: {e}\n")

    merged_path = config.DATA_DIR / "all_channels_merged.md"
    merged_path.write_text("\n".join(all_lines), encoding="utf-8")
    return str(merged_path)
