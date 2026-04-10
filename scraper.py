import asyncio
import sys
from pathlib import Path
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


async def scrape_channel(client: TelegramClient, channel_id: str,
                          offset_id: int = 0, progress_callback=None):
    ch = db.get_channel(channel_id)
    if not ch:
        raise ValueError(f"Channel {channel_id} not found in DB")

    try:
        entity = await client.get_entity(PeerChannel(int(channel_id)))
    except Exception:
        entity = await client.get_entity(ch["username"])

    result = await client.get_messages(entity, limit=0)
    total = result.total

    if total == 0:
        return 0

    channel_dir = config.DATA_DIR / ch["username"] or channel_id
    media_dir = channel_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    message_batch = []
    links_batch = []
    processed = 0
    last_id = offset_id
    batch_size = 100

    async for message in client.iter_messages(entity, offset_id=offset_id, reverse=True):
        try:
            media_type = _get_media_type(message)
            media_path = None

            if media_type and media_type != "other":
                ext = _get_file_ext(media_type)
                filename = f"{message.id}_{media_type}{ext}"
                file_path = media_dir / filename

                if not file_path.exists():
                    try:
                        downloaded = await message.download_media(file=str(file_path))
                        if downloaded:
                            media_path = str(file_path)
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds)
                        try:
                            downloaded = await message.download_media(file=str(file_path))
                            if downloaded:
                                media_path = str(file_path)
                        except Exception:
                            pass
                    except Exception:
                        pass
                else:
                    media_path = str(file_path)

            text = message.message or ""

            sender = await message.get_sender()
            if isinstance(sender, User):
                sender_name = " ".join(
                    filter(None, [sender.first_name, sender.last_name])
                )
            else:
                sender_name = getattr(sender, "title", "") if sender else ""

            reactions_str = None
            if message.reactions and message.reactions.results:
                parts = []
                for r in message.reactions.results:
                    emoji = getattr(r.reaction, "emoticon", "")
                    if emoji:
                        parts.append(f"{emoji}{r.count}")
                if parts:
                    reactions_str = " ".join(parts)

            msg_data = {
                "channel_id": channel_id,
                "message_id": message.id,
                "date": message.date.strftime("%Y-%m-%d %H:%M:%S") if message.date else "",
                "sender_name": sender_name,
                "text": text,
                "media_type": media_type,
                "media_path": media_path,
                "views": message.views,
                "forwards": message.forwards,
                "reactions": reactions_str,
                "reply_to": message.reply_to_msg_id if message.reply_to else None,
                "content_length": len(text),
            }
            message_batch.append(msg_data)

            extracted_links = extract_links(text)
            for link in extracted_links:
                links_batch.append({
                    "channel_id": channel_id,
                    "message_id": message.id,
                    "url": link["url"],
                    "domain": link["domain"],
                    "context_text": link["context_text"],
                    "date": msg_data["date"],
                })

            last_id = message.id
            processed += 1

            if len(message_batch) >= batch_size:
                db.insert_messages_batch(message_batch)
                db.insert_links_batch(links_batch)
                message_batch.clear()
                links_batch.clear()

            if progress_callback:
                progress_callback(processed, total)

        except Exception as e:
            print(f"\nОшибка в сообщении {message.id}: {e}")

    if message_batch:
        db.insert_messages_batch(message_batch)
        db.insert_links_batch(links_batch)

    db.update_channel(
        channel_id,
        last_message_id=last_id,
        total_posts=processed if offset_id == 0 else ch["total_posts"] + processed,
        last_scraped=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    return processed


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
