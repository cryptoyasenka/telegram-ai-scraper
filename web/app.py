"""FastAPI web UI for tg-parser.

Flow:
  1. Add channel -> auto scan (metadata-only scrape, media_types=empty)
  2. Show media breakdown with checkboxes + live ETA
  3. Download selected media types
"""
import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Make the parent dir importable so we can reuse db/scraper/exporter modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import db  # noqa: E402
import scraper  # noqa: E402
import exporter  # noqa: E402
from web import jobs  # noqa: E402
from web.i18n import t, get_type_label, get_type_label_single, LANGUAGES, DEFAULT_LANG  # noqa: E402


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@asynccontextmanager
async def lifespan(application):
    db.init_db()
    yield

app = FastAPI(title="TG Parser", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def _get_lang(request: Request) -> str:
    return request.cookies.get("lang", DEFAULT_LANG)


def _ctx(request: Request, **kwargs) -> dict:
    """Base template context with i18n."""
    lang = _get_lang(request)
    return {
        "request": request,
        "t": lambda key, **kw: t(key, lang, **kw),
        "lang": lang,
        "languages": LANGUAGES,
        "get_type_label": lambda key: get_type_label(key, lang),
        "get_type_label_single": lambda key: get_type_label_single(key, lang),
        **kwargs,
    }


@app.get("/set-lang/{lang}")
async def set_lang(lang: str, request: Request):
    if lang not in LANGUAGES:
        lang = DEFAULT_LANG
    referer = request.headers.get("referer", "/")
    response = RedirectResponse(url=referer, status_code=303)
    response.set_cookie("lang", lang, max_age=365 * 86400)
    return response


# Moving-average download rate (bytes/sec), seeded with a reasonable Telegram default.
_rate_state = {"bytes_per_sec": 800_000.0}


def _update_rate(bytes_done: int, elapsed: float) -> None:
    if elapsed <= 0 or bytes_done <= 0:
        return
    observed = bytes_done / elapsed
    # Simple EMA, alpha 0.4
    _rate_state["bytes_per_sec"] = 0.6 * _rate_state["bytes_per_sec"] + 0.4 * observed


def _format_size(b: int) -> str:
    if b is None or b == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    v = float(b)
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.1f} {units[i]}"


def _format_eta(seconds: Optional[float], lang: str = "ru") -> str:
    if seconds is None:
        return "—"
    seconds = int(max(seconds, 0))
    s_label = t("js_s", lang)
    m_label = t("js_m", lang)
    h_label = t("js_h", lang)
    if seconds < 60:
        return f"{seconds} {s_label}"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}{m_label} {s}{s_label}"
    h, m = divmod(m, 60)
    return f"{h}{h_label} {m}{m_label}"


# --- Background job helpers ---------------------------------------------------


async def _load_client_or_fail():
    creds_file = config.DATA_DIR / "api_credentials.json"
    if not creds_file.exists():
        raise HTTPException(status_code=400, detail="Сначала выполни: tgp auth")
    creds = json.loads(creds_file.read_text())
    client = await scraper.create_client(creds["api_id"], creds["api_hash"])
    if not await client.is_user_authorized():
        await client.disconnect()
        raise HTTPException(status_code=400, detail="Сессия истекла. tgp auth")
    return client


async def _run_scan(job_id: str, channel_id: str, username: str):
    client = None
    try:
        client = await _load_client_or_fail()
        ch = db.get_channel(channel_id)

        async def on_progress(current, total):
            await jobs.update(job_id, current=current, total=total)

        def sync_progress(current, total):
            asyncio.get_event_loop().create_task(on_progress(current, total))

        # Step 1: pull new messages (metadata only, no downloads)
        await scraper.scrape_channel(
            client,
            channel_id,
            offset_id=ch["last_message_id"],
            media_types=set(),
            progress_callback=sync_progress,
        )
        # Step 2: backfill media_size for rows where it's still missing
        missing = db.get_messages_missing_size(channel_id)
        if missing:
            await jobs.update(job_id, label=f"{ch['title']} — размеры ({len(missing)})")
            await scraper.backfill_media_sizes(
                client, channel_id, progress_callback=sync_progress
            )
        await jobs.finish(job_id, result={"username": username})
    except Exception as e:
        await jobs.finish(job_id, error=str(e))
    finally:
        if client:
            await client.disconnect()


async def _run_backfill(job_id: str, channel_id: str):
    client = None
    try:
        client = await _load_client_or_fail()

        async def on_progress(current, total):
            await jobs.update(job_id, current=current, total=total)

        def sync_progress(current, total):
            asyncio.get_event_loop().create_task(on_progress(current, total))

        updated = await scraper.backfill_media_sizes(
            client, channel_id, progress_callback=sync_progress
        )
        await jobs.finish(job_id, result={"updated": updated})
    except Exception as e:
        await jobs.finish(job_id, error=str(e))
    finally:
        if client:
            await client.disconnect()


async def _run_download(job_id: str, channel_id: str, media_types: set[str],
                        bytes_total: int):
    client = None
    import time
    try:
        client = await _load_client_or_fail()
        await jobs.update(job_id, bytes_total=bytes_total)
        start = time.time()
        # We track count-based progress from scraper; bytes are estimated.
        async def on_progress(current, total):
            # Approximate bytes done proportionally
            fraction = current / total if total else 0
            bdone = int(fraction * bytes_total)
            await jobs.update(
                job_id, current=current, total=total, bytes_done=bdone
            )

        def sync_progress(current, total):
            asyncio.get_event_loop().create_task(on_progress(current, total))

        done = await scraper.download_pending_media(
            client, channel_id, media_types,
            progress_callback=sync_progress,
        )
        elapsed = max(time.time() - start, 0.001)
        _update_rate(bytes_total, elapsed)
        await jobs.finish(job_id, result={"downloaded": done})
    except Exception as e:
        await jobs.finish(job_id, error=str(e))
    finally:
        if client:
            await client.disconnect()


async def _run_transcribe(job_id: str, channel_id: str,
                          media_types: list[str] = None):
    """Run transcription in a thread (whisper is CPU-bound and synchronous)."""
    import concurrent.futures
    import time
    try:
        import transcriber
        pending = db.get_messages_without_transcript(channel_id, media_types=media_types)
        if not pending:
            await jobs.finish(job_id, result={"transcribed": 0})
            return

        total = len(pending)
        await jobs.update(job_id, total=total)

        loop = asyncio.get_event_loop()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        done = 0
        start = time.time()

        for i, msg in enumerate(pending):
            transcript = await loop.run_in_executor(
                executor, transcriber.transcribe_file, msg["media_path"]
            )
            if transcript:
                db.update_transcript(channel_id, msg["message_id"], transcript)
                done += 1

            await jobs.update(job_id, current=i + 1, total=total)

        executor.shutdown(wait=False)
        await jobs.finish(job_id, result={"transcribed": done})
    except Exception as e:
        await jobs.finish(job_id, error=str(e))


# --- Routes -------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    channels = db.get_all_channels()
    enriched = []
    for ch in channels:
        breakdown = db.get_media_breakdown(ch["id"])
        enriched.append({**ch, "breakdown": breakdown})
    return templates.TemplateResponse(
        "index.html",
        _ctx(request, channels=enriched, active_jobs=jobs.list_active()),
    )


@app.post("/channels/add")
async def channels_add(request: Request, channel: str = Form(...)):
    client = await _load_client_or_fail()
    try:
        info = await scraper.resolve_channel(client, channel)
        if not info:
            raise HTTPException(status_code=404, detail=f"Канал '{channel}' не найден")
        db.add_channel(info["id"], info["username"], info["title"])
    finally:
        await client.disconnect()

    # Auto-scan after adding
    job_id = await jobs.create("scan", info["id"], label=info["title"])
    asyncio.create_task(_run_scan(job_id, info["id"], info["username"]))
    return RedirectResponse(url=f"/channels/{info['username']}?job={job_id}", status_code=303)


@app.post("/channels/{username}/scan")
async def channels_scan(username: str):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    job_id = await jobs.create("scan", ch["id"], label=ch["title"])
    asyncio.create_task(_run_scan(job_id, ch["id"], username))
    return RedirectResponse(url=f"/channels/{username}?job={job_id}", status_code=303)


@app.post("/channels/{username}/backfill-sizes")
async def channels_backfill(username: str):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    job_id = await jobs.create("backfill", ch["id"], label=ch["title"])
    asyncio.create_task(_run_backfill(job_id, ch["id"]))
    return RedirectResponse(url=f"/channels/{username}?job={job_id}", status_code=303)


@app.post("/channels/{username}/transcribe")
async def channels_transcribe(username: str, request: Request):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    form = await request.form()
    selected = list(form.getlist("tr_types"))
    if not selected:
        selected = None  # all types
    pending = db.get_messages_without_transcript(ch["id"], media_types=selected)
    if not pending:
        return RedirectResponse(url=f"/channels/{username}", status_code=303)
    job_id = await jobs.create("transcribe", ch["id"], label=ch["title"])
    asyncio.create_task(_run_transcribe(job_id, ch["id"], media_types=selected))
    return RedirectResponse(url=f"/channels/{username}?job={job_id}", status_code=303)


@app.get("/channels/{username}", response_class=HTMLResponse)
async def channel_detail(request: Request, username: str, job: Optional[str] = None):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")

    breakdown = db.get_media_breakdown(ch["id"])
    total_posts = sum(v["count"] for v in breakdown.values())
    total_bytes = sum(v["bytes"] for v in breakdown.values())
    missing_sizes = len(db.get_messages_missing_size(ch["id"]))
    transcript_breakdown = db.get_transcript_breakdown(ch["id"])
    pending_transcripts = sum(v["pending"] for v in transcript_breakdown.values())

    # Build type cards in a stable order
    order = ["text", "voice", "audio", "video_note", "photo", "video", "document", "other"]
    lang = _get_lang(request)
    cards = []
    for key in order:
        if key in breakdown:
            v = breakdown[key]
            cards.append({
                "key": key,
                "label": get_type_label(key, lang),
                "count": v["count"],
                "bytes": v["bytes"],
                "bytes_human": _format_size(v["bytes"]),
                "downloaded": v["downloaded"],
                "pending_bytes": v["pending_bytes"],
                "pending_bytes_human": _format_size(v["pending_bytes"]),
            })

    channel_dir = db.get_channel_dir(ch)
    default_dir = str(config.DATA_DIR / (ch["username"] or ch["id"]))

    return templates.TemplateResponse(
        "channel.html",
        _ctx(request,
            channel=ch,
            cards=cards,
            total_posts=total_posts,
            total_bytes_human=_format_size(total_bytes),
            rate_bytes_per_sec=_rate_state["bytes_per_sec"],
            rate_human=f"{_format_size(int(_rate_state['bytes_per_sec']))}/{t('js_s', lang)}",
            current_job_id=job,
            missing_sizes=missing_sizes,
            pending_transcripts=pending_transcripts,
            transcript_breakdown=transcript_breakdown,
            channel_dir=str(channel_dir),
            default_dir=default_dir,
            is_custom_dir=ch.get("download_dir") is not None,
        ),
    )


@app.get("/api/browse-dirs")
async def browse_dirs(path: str = ""):
    """List subdirectories at the given path for the folder picker."""
    import string
    if not path:
        # Return drive roots on Windows, / on Unix
        if sys.platform == "win32":
            drives = []
            for letter in string.ascii_uppercase:
                p = Path(f"{letter}:\\")
                if p.exists():
                    drives.append({"name": f"{letter}:\\", "path": str(p)})
            return {"dirs": drives, "parent": None, "current": ""}
        else:
            path = "/"

    target = Path(path)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Путь не найден")

    dirs = []
    try:
        for entry in sorted(target.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                dirs.append({"name": entry.name, "path": str(entry)})
    except PermissionError:
        pass

    parent = str(target.parent) if target.parent != target else None
    return {"dirs": dirs, "parent": parent, "current": str(target)}


@app.post("/api/create-dir")
async def create_dir(request: Request):
    """Create a new directory."""
    data = await request.json()
    path = data.get("path", "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="Путь не указан")
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "path": path}


@app.post("/channels/{username}/set-download-dir")
async def channels_set_download_dir(username: str, request: Request):
    import shutil
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")
    form = await request.form()
    raw = form.get("download_dir", "").strip()

    old_dir = str(db.get_channel_dir(ch))
    new_raw = raw if raw else None
    # Compute what new dir will be
    if new_raw:
        new_dir = new_raw
    else:
        new_dir = str(config.DATA_DIR / (ch["username"] or ch["id"]))

    # Move files if the directory actually changed and old one exists
    if new_dir != old_dir and Path(old_dir).exists():
        Path(new_dir).mkdir(parents=True, exist_ok=True)
        # Move contents (not the dir itself, to handle merging)
        for item in Path(old_dir).iterdir():
            dest = Path(new_dir) / item.name
            if not dest.exists():
                shutil.move(str(item), str(dest))
        # Rewrite media_path in DB
        db.rewrite_media_paths(ch["id"], old_dir, new_dir)
        # Clean up old dir if empty
        try:
            Path(old_dir).rmdir()
        except OSError:
            pass  # not empty, leave it

    db.update_download_dir(ch["id"], new_raw)
    return RedirectResponse(url=f"/channels/{username}", status_code=303)


@app.post("/channels/{username}/download")
async def channels_download(username: str, request: Request):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")

    form = await request.form()
    # Checkbox values come as multiple 'types' entries
    selected = set(form.getlist("types"))
    # Expand meta-aliases if they arrive
    media_types = set()
    for t in selected:
        if t in scraper.MEDIA_ALIASES:
            media_types |= scraper.MEDIA_ALIASES[t]
        else:
            media_types.add(t)

    if not media_types:
        return RedirectResponse(url=f"/channels/{username}", status_code=303)

    breakdown = db.get_media_breakdown(ch["id"])
    bytes_total = sum(
        breakdown.get(t, {}).get("pending_bytes", 0) for t in media_types
    )

    job_id = await jobs.create("download", ch["id"], label=ch["title"])
    asyncio.create_task(_run_download(job_id, ch["id"], media_types, bytes_total))
    return RedirectResponse(url=f"/channels/{username}?job={job_id}", status_code=303)


@app.get("/jobs/{job_id}")
async def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    eta_sec = jobs.compute_eta(job)
    return JSONResponse({
        "id": job["id"],
        "type": job["type"],
        "label": job["label"],
        "status": job["status"],
        "current": job["current"],
        "total": job["total"],
        "bytes_done": job["bytes_done"],
        "bytes_total": job["bytes_total"],
        "bytes_done_human": _format_size(job["bytes_done"]),
        "bytes_total_human": _format_size(job["bytes_total"]),
        "eta_seconds": eta_sec,
        "eta_human": _format_eta(eta_sec, "ru"),
        "error": job["error"],
        "result": job["result"],
    })


@app.get("/channels/{username}/messages", response_class=HTMLResponse)
async def channel_messages(request: Request, username: str,
                           q: Optional[str] = None, type: Optional[str] = None,
                           page: int = 1):
    ch = db.get_channel_by_username(username)
    if not ch:
        raise HTTPException(status_code=404, detail="Канал не найден")

    per_page = 50
    offset = (page - 1) * per_page

    conn = db.get_connection()
    where = ["channel_id = ?"]
    params: list = [ch["id"]]

    if q:
        where.append("(text LIKE ? OR voice_transcript LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if type:
        if type == "text":
            where.append("media_type IS NULL")
        else:
            where.append("media_type = ?")
            params.append(type)

    where_sql = " AND ".join(where)
    total = conn.execute(f"SELECT COUNT(*) as c FROM messages WHERE {where_sql}", params).fetchone()["c"]
    rows = conn.execute(
        f"SELECT * FROM messages WHERE {where_sql} ORDER BY date DESC LIMIT ? OFFSET ?",
        params + [per_page, offset],
    ).fetchall()
    conn.close()

    import math
    total_pages = max(1, math.ceil(total / per_page))

    return templates.TemplateResponse(
        "messages.html",
        _ctx(request,
            channel=ch,
            messages=[dict(r) for r in rows],
            total=total,
            page=page,
            limit=per_page,
            total_pages=total_pages,
            search=q,
            filter_type=type,
        ),
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: Optional[str] = None):
    results = []
    if q:
        results = db.search_all(q)
    return templates.TemplateResponse(
        "search.html",
        _ctx(request, query=q, results=results),
    )


@app.get("/api/rate")
async def get_rate(request: Request):
    lang = _get_lang(request)
    return {
        "bytes_per_sec": _rate_state["bytes_per_sec"],
        "human": f"{_format_size(int(_rate_state['bytes_per_sec']))}/{t('js_s', lang)}",
    }
