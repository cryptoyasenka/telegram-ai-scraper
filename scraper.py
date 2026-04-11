import asyncio
from datetime import datetime
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaWebPage,
    User,
    Channel,
    Chat,
    PeerChannel,
    DocumentAttributeAudio,
    DocumentAttributeVideo,
)
from telethon.errors import FloodWaitError, SessionPasswordNeededError

import config
import db
from links import extract_links


SESSION_PATH = str(config.DATA_DIR / "session")

DEFAULT_MEDIA_TYPES = {"voice", "audio", "video_note"}
ALL_MEDIA_TYPES = {"voice", "audio", "video_note", "photo", "video", "document"}

MEDIA_ALIASES = {
    "text": set(),
    "none": set(),
    "voice": {"voice", "audio", "video_note"},
    "photos": {"photo"},
    "videos": {"video"},
    "docs": {"document"},
    "all": ALL_MEDIA_TYPES,
}

DOWNLOAD_CONCURRENCY = 5
BATCH_SIZE = 100


def parse_media_selection(spec: Optional[str]) -> set[str]:
    """Parse comma-separated media selection: text, voice, photos, videos, docs, all."""
    if spec is None or spec == "":
        return set(DEFAULT_MEDIA_TYPES)

    result: set[str] = set()
    for part in spec.split(","):
        key = part.strip().lower()
        if not key:
            continue
        if key not in MEDIA_ALIASES:
            valid = ", ".join(MEDIA_ALIASES.keys())
            raise ValueError(f"Неизвестный тип медиа '{key}'. Допустимо: {valid}")
        result |= MEDIA_ALIASES[key]
    return result


def _get_media_type(message) -> Optional[str]:
    if not message.media:
        return None
    if isinstance(message.media, MessageMediaWebPage):
        return None
    if isinstance(message.media, MessageMediaPhoto):
        return "photo"
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if doc:
            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeAudio):
                    if attr.voice:
                        return "voice"
                    return "audio"
                if isinstance(attr, DocumentAttributeVideo):
                    if attr.round_message:
                        return "video_note"
                    return "video"
            mime = doc.mime_type or ""
            if mime.startswith("image/"):
                return "photo"
            if mime.startswith("video/"):
                return "video"
        return "document"
    return "other"


def _get_file_ext(media_type: str) -> str:
    return {
        "voice": ".ogg",
        "video_note": ".mp4",
        "video": ".mp4",
        "audio": ".mp3",
        "photo": ".jpg",
        "document": ".bin",
    }.get(media_type, ".bin")


def _get_sender_name(message, channel_title: str) -> str:
    post_author = getattr(message, "post_author", None)
    if post_author:
        return post_author
    cached = message.sender
    if isinstance(cached, User):
        return " ".join(filter(None, [cached.first_name, cached.last_name]))
    if cached is not None:
        return getattr(cached, "title", "") or channel_title
    return channel_title


def _format_reactions(message) -> Optional[str]:
    if not message.reactions or not message.reactions.results:
        return None
    parts = []
    for r in message.reactions.results:
        emoji = getattr(r.reaction, "emoticon", "")
        if emoji:
            parts.append(f"{emoji}{r.count}")
    return " ".join(parts) if parts else None


async def create_client(api_id: int, api_hash: str) -> TelegramClient:
    client = TelegramClient(SESSION_PATH, api_id, api_hash)
    await client.connect()
    return client


async def authenticate(client: TelegramClient):
    if await client.is_user_authorized():
        return True

    phone = input("Номер телефона (с кодом страны): ")
    await client.send_code_request(phone)
    code = input("Код из Telegram: ")

    try:
        await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        password = input("Пароль двухфакторной аутентификации: ")
        await client.sign_in(password=password)

    return True


async def resolve_channel(client: TelegramClient, channel_input: str):
    channel_input = channel_input.lstrip("@")

    if "t.me/" in channel_input:
        channel_input = channel_input.split("t.me/")[1].split("/")[0].lstrip("+")

    try:
        entity = await client.get_entity(channel_input)
    except Exception as e:
        print(f"[debug] get_entity('{channel_input}'): {e}")
        try:
            entity = await client.get_entity(PeerChannel(int(channel_input)))
        except Exception as e2:
            print(f"[debug] PeerChannel fallback: {e2}")
            return None

    channel_id = str(entity.id)
    username = getattr(entity, "username", None) or ""
    title = getattr(entity, "title", None) or username or channel_id

    return {
        "entity": entity,
        "id": channel_id,
        "username": username,
        "title": title,
    }


async def _download_one(message, media_type: str, media_dir, sem: asyncio.Semaphore) -> Optional[str]:
    ext = _get_file_ext(media_type)
    filename = f"{message.id}_{media_type}{ext}"
    file_path = media_dir / filename

    if file_path.exists():
        return str(file_path)

    async with sem:
        try:
            downloaded = await message.download_media(file=str(file_path))
            return str(file_path) if downloaded else None
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            try:
                downloaded = await message.download_media(file=str(file_path))
                return str(file_path) if downloaded else None
            except Exception:
                return None
        except Exception:
            return None


async def _flush_batch(buffer, channel_id, channel_title, media_dir, media_types, sem):
    download_coros = []
    indices = []
    for idx, (message, media_type) in enumerate(buffer):
        if media_type and media_type != "other" and media_type in media_types:
            download_coros.append(_download_one(message, media_type, media_dir, sem))
            indices.append(idx)

    paths_by_idx = {}
    if download_coros:
        results = await asyncio.gather(*download_coros, return_exceptions=True)
        for idx, res in zip(indices, results):
            if isinstance(res, Exception):
                paths_by_idx[idx] = None
            else:
                paths_by_idx[idx] = res

    msg_rows = []
    link_rows = []
    for idx, (message, media_type) in enumerate(buffer):
        text = message.message or ""
        date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else ""
        msg_rows.append({
            "channel_id": channel_id,
            "message_id": message.id,
            "date": date_str,
            "sender_name": _get_sender_name(message, channel_title),
            "text": text,
            "media_type": media_type,
            "media_path": paths_by_idx.get(idx),
            "views": message.views,
            "forwards": message.forwards,
            "reactions": _format_reactions(message),
            "reply_to": message.reply_to_msg_id if message.reply_to else None,
            "content_length": len(text),
        })
        for link in extract_links(text):
            link_rows.append({
                "channel_id": channel_id,
                "message_id": message.id,
                "url": link["url"],
                "domain": link["domain"],
                "context_text": link["context_text"],
                "date": date_str,
            })

    db.insert_messages_batch(msg_rows)
    db.insert_links_batch(link_rows)


async def scrape_channel(client: TelegramClient, channel_id: str,
                          offset_id: int = 0, progress_callback=None,
                          media_types: Optional[set[str]] = None):
    if media_types is None:
        media_types = set(DEFAULT_MEDIA_TYPES)

    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found in DB")

    try:
        entity = await client.get_entity(PeerChannel(int(channel_id)))
    except Exception:
        entity = await client.get_entity(ch["username"])

    total = (await client.get_messages(entity, limit=0)).total
    if total == 0:
        return 0

    channel_dir = config.DATA_DIR / (ch["username"] or channel_id)
    media_dir = channel_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    buffer = []
    processed = 0
    last_id = offset_id

    async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True):
        try:
            media_type = _get_media_type(message)
            buffer.append((message, media_type))
            last_id = message.id
            processed += 1

            if len(buffer) >= BATCH_SIZE:
                await _flush_batch(buffer, channel_id, ch["title"], media_dir, media_types, sem)
                buffer.clear()

            if progress_callback:
                progress_callback(processed, total)
        except Exception as e:
            print(f"\nОшибка в сообщении {getattr(message, 'id', '?')}: {e}")

    if buffer:
        await _flush_batch(buffer, channel_id, ch["title"], media_dir, media_types, sem)

    db.update_channel(
        channel_id,
        last_message_id=last_id,
        total_posts=processed if offset_id == 0 else ch["total_posts"] + processed,
        last_scraped=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    return processed


async def download_pending_media(client: TelegramClient, channel_id: str,
                                  media_types: set[str], limit: Optional[int] = None,
                                  progress_callback=None) -> int:
    """Fetch media for already-scraped messages that still have media_path = NULL."""
    if not media_types:
        return 0

    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found in DB")

    pending = db.get_messages_needing_media(channel_id, sorted(media_types))
    if limit:
        pending = pending[:limit]
    if not pending:
        return 0

    try:
        entity = await client.get_entity(PeerChannel(int(channel_id)))
    except Exception:
        entity = await client.get_entity(ch["username"])

    channel_dir = config.DATA_DIR / (ch["username"] or channel_id)
    media_dir = channel_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    ids = [r["message_id"] for r in pending]
    total = len(ids)
    done = 0

    for i in range(0, total, BATCH_SIZE):
        chunk_ids = ids[i:i + BATCH_SIZE]
        messages = await client.get_messages(entity, ids=chunk_ids)

        async def _fetch(msg):
            if msg is None:
                return None
            mt = _get_media_type(msg)
            if mt not in media_types:
                return None
            path = await _download_one(msg, mt, media_dir, sem)
            if path:
                db.update_media_path(channel_id, msg.id, path)
                return path
            return None

        results = await asyncio.gather(*[_fetch(m) for m in messages], return_exceptions=True)
        for r in results:
            if isinstance(r, str):
                done += 1

        if progress_callback:
            progress_callback(min(i + len(chunk_ids), total), total)

    return done


async def list_user_channels(client: TelegramClient) -> list[dict]:
    result = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            ch_type = "channel" if isinstance(entity, Channel) and entity.broadcast else "group"
            result.append({
                "id": str(dialog.id),
                "title": dialog.title,
                "username": getattr(entity, "username", None) or "",
                "type": ch_type,
            })
    return result
