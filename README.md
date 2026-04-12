# TG Parser

Telegram channel parser that scrapes messages, downloads media, transcribes voice/video via Whisper, and exports everything in AI-friendly formats (Markdown + JSON).

Includes a full web UI and a CLI.

## One-Click Launch

**Windows** — double-click `start.bat`
**macOS/Linux** — run `./start.sh`

On first run, the script creates a virtual environment and installs everything automatically. Then run `tgp auth` once to connect your Telegram account — and you're done.

## Features

- **Scrape channels** — pull all messages, metadata, reactions, links
- **Download media** — voice, audio, video notes, photos, videos, documents (selective by type)
- **Transcribe** — speech-to-text via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (runs on CPU)
- **Export** — Markdown and JSON exports optimized for feeding into AI agents
- **Web UI** — full management interface at `http://localhost:8765`
  - Add/update channels
  - Download media with per-type selection and live ETA
  - Transcribe with per-type selection and progress tracking
  - Browse messages with search and filters
  - Global search across all channels
  - Custom download directory per channel with folder browser
  - 3 languages: English, Russian, Ukrainian
- **CLI** — `tgp` command with all operations
- **Link extraction** — collects URLs from messages with domain and context

## Requirements

- Python 3.11+
- ffmpeg (for video transcription — optional, only needed for video files)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)

## Manual Installation

If you prefer to set things up manually instead of using the launch scripts:

```bash
git clone https://github.com/cryptoyasenka/tg-parser.git
cd tg-parser
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
```bash
winget install ffmpeg
```

The transcriber auto-detects ffmpeg in PATH and common WinGet install locations.

## Quick Start

### 1. Authenticate

```bash
tgp auth
```

Enter your Telegram API ID, API Hash, phone number, and verification code.

### 2. Add a channel

```bash
tgp add @channel_name
# or
tgp add https://t.me/channel_name
# or interactively:
tgp add
```

### 3. Scrape

```bash
tgp scrape              # all channels
tgp scrape @channel     # specific channel
```

### 4. Download media

```bash
tgp download @channel --media voice        # voice + audio + video notes
tgp download @channel --media photos       # photos only
tgp download @channel --media all          # everything
```

### 5. Transcribe

```bash
tgp transcribe            # all channels
tgp transcribe @channel   # specific channel
tgp transcribe --limit 10 # test with 10 files
```

### 6. Export

```bash
tgp export                          # all channels → MD + JSON
tgp export @channel --links-only    # only posts with links
tgp export --merge                  # all channels in one file
tgp export --search "keyword"       # filtered export
```

### 7. Web UI

```bash
tgp serve                    # http://localhost:8765
tgp serve --port 3000        # custom port
```

## Web UI

The web interface provides full management:

| Page | Description |
|------|-------------|
| `/` | Channel list — add channels, see overview |
| `/channels/{name}` | Channel detail — download, transcribe, manage |
| `/channels/{name}/messages` | Message browser with search and type filters |
| `/search` | Global search across all channels |

All operations run as background jobs with progress bars and live ETA.

## CLI Commands

| Command | Description |
|---------|-------------|
| `tgp auth` | Authenticate with Telegram API |
| `tgp add` | Add channel (interactive or by @username/URL) |
| `tgp scrape` | Pull messages from channels |
| `tgp update` | Alias for scrape (pull new posts) |
| `tgp download` | Download media by type |
| `tgp transcribe` | Transcribe voice/video to text |
| `tgp export` | Export to Markdown + JSON |
| `tgp search` | Search messages or links |
| `tgp status` | Show stats for all channels |
| `tgp channels` | List your Telegram channels/groups |
| `tgp serve` | Start web UI |

## Project Structure

```
tg-parser/
├── start.bat        # One-click launch (Windows)
├── start.sh         # One-click launch (macOS/Linux)
├── cli.py           # CLI entry point (click)
├── config.py        # Configuration constants
├── db.py            # SQLite database operations
├── scraper.py       # Telegram API scraping + downloads
├── transcriber.py   # Whisper transcription
├── exporter.py      # MD/JSON export
├── links.py         # URL extraction
├── setup.py         # Package setup
├── requirements.txt # Pinned dependencies
└── web/
    ├── app.py       # FastAPI application
    ├── jobs.py      # Background job registry
    ├── i18n.py      # Translations (EN/RU/UK)
    ├── templates/   # Jinja2 HTML templates
    └── static/      # CSS
```

## Export Format

Exports are designed for AI consumption:

**Markdown** — human-readable, includes transcriptions, links, reactions:
```markdown
# Channel Name (@username)
Exported: 150 posts of 300

## 2026-04-10

[Voice]
> Transcription: ...
Links: [example.com](https://example.com)
[views:1234 | 👍12 ❤️5]
```

**JSON** — structured data for programmatic access:
```json
{
  "channel": {"id": "...", "title": "...", "username": "..."},
  "total_exported": 150,
  "messages": [
    {
      "date": "2026-04-10 12:00:00",
      "text": "...",
      "voice_transcript": "...",
      "links": [{"url": "...", "domain": "..."}],
      "views": 1234,
      "reactions": "👍12 ❤️5"
    }
  ]
}
```

## Tech Stack

- **Telegram API**: [Telethon](https://github.com/LonamiWebs/Telethon)
- **Transcription**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (base model, CPU)
- **Web**: [FastAPI](https://fastapi.tiangolo.com/) + Jinja2 + vanilla JS
- **Database**: SQLite with WAL mode
- **CLI**: [Click](https://click.palletsprojects.com/) + [Rich](https://rich.readthedocs.io/)

## Notes

- Only channels you're subscribed to can be scraped (Telegram API limitation)
- Transcription on CPU takes ~1-3 seconds per file (base model). GPU speeds it up significantly.
- Session file is stored in `data/` — do not share it
- API credentials are stored in `data/api_credentials.json` — keep private

## License

MIT
