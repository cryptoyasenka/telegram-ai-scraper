# TG Parser

**Turn any Telegram channel into a searchable, AI-ready knowledge base.**

Most Telegram scrapers just dump text. This one downloads everything — voice messages, video notes, videos, photos, documents — then **transcribes speech to text** via Whisper, extracts all links, and exports the whole thing in formats that AI agents (Claude, ChatGPT, etc.) can consume directly.

### Why this exists

Telegram channels are full of valuable content locked inside voice messages and video notes that no search engine can reach. TG Parser fixes that:

- A 2-hour podcast posted as voice messages? **Transcribed and searchable.**
- Video notes (circles) with tips? **Converted to text.**
- 500 posts with scattered links? **All URLs extracted with context.**
- Need to feed a channel to an AI agent? **One-click export to Markdown/JSON.**

### What makes it different

| Feature | Most scrapers | TG Parser |
|---------|--------------|-----------|
| Text messages | Yes | Yes |
| Voice messages | Skip | **Download + transcribe** |
| Video notes (circles) | Skip | **Download + transcribe** |
| Videos | Sometimes | **Download + transcribe audio** |
| Photos/documents | Sometimes | **Selective download by type** |
| Transcription | No | **Whisper AI, runs on CPU** |
| Pick what to download | No, all or nothing | **Checkboxes per media type** |
| Pick what to transcribe | No | **Per-type selection** |
| Live progress + ETA | Rarely | **Real-time for everything** |
| Web UI | No | **Full management interface** |
| AI-ready export | JSON maybe | **Markdown + JSON with transcripts** |
| Link extraction | No | **URLs + domains + context** |
| Multi-language UI | No | **EN / RU / UK** |

## One-Click Launch

**Windows** — double-click `start.bat`
**macOS/Linux** — run `./start.sh`

First run: creates venv, installs everything, walks you through Telegram auth. That's it.

## Requirements

- Python 3.11+
- [Telegram API credentials](https://my.telegram.org) (free, takes 2 minutes)
- ffmpeg (optional — only for video transcription)

## How It Works

```
Add channel → Scrape messages → Download media (selective) → Transcribe → Export for AI
     ↓              ↓                    ↓                       ↓            ↓
  @username    text, metadata,     voice ✓ video ✓        Whisper on CPU   Markdown
  t.me/link   reactions, links    photos ✗ docs ✗         per-type choice   + JSON
```

Everything runs through the **Web UI** (`http://localhost:8765`) or the **CLI** (`tgp`).

### Web UI

Full visual management — add channels, download with per-type checkboxes and live ETA, transcribe selectively, browse messages with search, global search across all channels.

### CLI

```bash
tgp auth                              # connect Telegram account
tgp add @channel                      # add channel (or interactively)
tgp scrape                            # pull all messages
tgp download @ch --media voice        # download only voice messages
tgp download @ch --media all          # download everything
tgp transcribe                        # transcribe all pending
tgp export                            # export to MD + JSON
tgp export --merge --links-only       # merged export, only posts with links
tgp search "keyword"                  # search across channels
tgp serve                             # start web UI
```

## Export Format

Exports are designed for AI consumption — paste into Claude, ChatGPT, or feed to any agent:

**Markdown:**
```markdown
# Channel Name (@username)
Exported: 150 posts of 300

## 2026-04-10

[Voice]
> Transcription: Today I want to talk about three tools that changed how I code...
Links: [cursor.com](https://cursor.com) | [claude.ai](https://claude.ai)
[views:1234 | 👍12 ❤️5]
```

**JSON** — structured data for programmatic access with full transcripts, links, reactions, views.

## Manual Installation

```bash
git clone https://github.com/cryptoyasenka/tg-parser.git
cd tg-parser
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
tgp auth                   # connect your Telegram
tgp serve                  # open web UI
```

### ffmpeg (optional, for video transcription)

```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
winget install ffmpeg        # Windows
```

## Tech Stack

[Telethon](https://github.com/LonamiWebs/Telethon) (Telegram API) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (transcription) · [FastAPI](https://fastapi.tiangolo.com/) + Jinja2 (web) · SQLite · [Click](https://click.palletsprojects.com/) + [Rich](https://rich.readthedocs.io/) (CLI)

## Project Structure

```
tg-parser/
├── start.bat / start.sh  # One-click launch
├── cli.py                # CLI (click)
├── scraper.py            # Telegram scraping + downloads
├── transcriber.py        # Whisper transcription
├── exporter.py           # MD/JSON export
├── db.py                 # SQLite operations
├── links.py              # URL extraction
├── config.py             # Settings
└── web/                  # FastAPI web UI
    ├── app.py            # Routes + background jobs
    ├── i18n.py           # Translations (EN/RU/UK)
    ├── templates/        # Jinja2 HTML
    └── static/           # CSS + favicon
```

## Notes

- Only channels you're subscribed to can be scraped (Telegram API limitation)
- Transcription runs on CPU (~1-3s per file). GPU speeds it up significantly
- Session and credentials are stored in `data/` — never share this folder

## License

MIT
