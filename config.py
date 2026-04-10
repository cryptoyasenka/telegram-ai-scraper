import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "app.db"

WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

TRANSCRIPTION_WARN_THRESHOLD = 50

SHITPOST_MIN_LENGTH = 20
EXPORT_DEFAULT_FORMAT = "md"

DATA_DIR.mkdir(exist_ok=True)
