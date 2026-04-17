"""
PoC: недельный дайджест постов Кисы через free NVIDIA API.

Запуск:
    cp .env.example .env          # и вписать NVIDIA_API_KEY
    python nvidia_weekly_summary.py
    python nvidia_weekly_summary.py --days 3 --channel deployladeploy
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DB_PATH = Path(__file__).parent / "data" / "app.db"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/nemotron-3-super-120b-a12b"  # 1M context — съест всё


def fetch_posts(channel_username: str, days: int) -> tuple[str, list[dict]]:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title FROM channels WHERE username = ?", (channel_username,)
        )
        row = cur.fetchone()
        if not row:
            sys.exit(f"Канал @{channel_username} не найден в БД")
        channel_id, title = row

        cur.execute(
            """SELECT message_id, date, text, voice_transcript, views, reactions
               FROM messages
               WHERE channel_id = ? AND date >= ?
               ORDER BY date ASC""",
            (channel_id, since),
        )
        posts = [
            {
                "id": r[0],
                "date": r[1],
                "text": (r[2] or "") + ("\n[voice]: " + r[3] if r[3] else ""),
                "views": r[4],
                "reactions": r[5],
            }
            for r in cur.fetchall()
            if (r[2] or r[3])
        ]
    return title, posts


def build_context(posts: list[dict]) -> str:
    lines = []
    for p in posts:
        lines.append(f"--- msg#{p['id']} | {p['date']} | 👁{p['views']} | {p['reactions'] or ''}")
        lines.append(p["text"].strip())
    return "\n".join(lines)


def summarize(channel_title: str, context: str, days: int) -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        sys.exit("NVIDIA_API_KEY не найден. Скопируй .env.example в .env и впиши ключ.")

    client = OpenAI(api_key=api_key, base_url=NVIDIA_BASE_URL)
    system = (
        "Ты — редактор tech-дайджеста. Тебе дан лог постов из Telegram-канала. "
        "Сделай краткую выжимку в формате:\n"
        "1) ТОП-5 главных тем недели (1 строка каждая)\n"
        "2) Что нового по инструментам / AI / workflow (3-5 пунктов)\n"
        "3) Сигналы / прогнозы / спорные мнения (2-3 пункта)\n"
        "4) Ссылки и ресурсы которые автор рекомендовал (список)\n"
        "Пиши на русском, конкретно, без воды."
    )
    user = f"Канал: {channel_title}\nПериод: последние {days} дней\n\nПосты:\n{context}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=2000,
    )
    return resp.choices[0].message.content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="deployladeploy", help="username канала (без @)")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    title, posts = fetch_posts(args.channel, args.days)
    if not posts:
        sys.exit(f"Нет постов за последние {args.days} дней в @{args.channel}")

    print(f"📥 Канал: {title}  |  постов за {args.days} дн: {len(posts)}")
    print(f"🤖 Модель: {MODEL}")
    print("─" * 60)

    context = build_context(posts)
    summary = summarize(title, context, args.days)
    print(summary)


if __name__ == "__main__":
    main()
