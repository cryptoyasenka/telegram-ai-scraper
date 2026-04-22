import subprocess
import shutil
from pathlib import Path
from typing import Optional

import config
import db


_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _model


def _find_ffmpeg() -> Optional[str]:
    found = shutil.which("ffmpeg")
    if found:
        return found
    # WinGet installs ffmpeg outside PATH; check common locations
    import glob
    for pattern in [
        str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/*ffmpeg*/*/bin/ffmpeg.exe"),
        "C:/ffmpeg*/bin/ffmpeg.exe",
        "C:/tools/ffmpeg*/bin/ffmpeg.exe",
    ]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def _has_audio_stream(video_path: str) -> Optional[bool]:
    """True if video contains an audio stream, False if not, None if can't check."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return None
    try:
        r = subprocess.run(
            [ffmpeg, "-i", video_path, "-hide_banner"],
            capture_output=True, text=True, errors="ignore", timeout=10,
        )
        # ffmpeg -i without output exits with rc=1 but probe info lands in stderr.
        return "Audio:" in r.stderr
    except Exception:
        return None


def _extract_audio(video_path: str, output_path: str) -> bool:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        print("ffmpeg не найден. Установите ffmpeg для транскрипции видео.")
        return False
    try:
        subprocess.run(
            [ffmpeg, "-i", video_path, "-vn", "-acodec", "libopus",
             "-y", output_path],
            capture_output=True, check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def transcribe_file(file_path: str) -> Optional[str]:
    """Return transcribed text, empty string if no speech, or None on technical failure.

    Return contract:
        "text…" — whisper produced content
        ""      — attempted, nothing to transcribe (no audio track / silence / non-speech)
        None    — technical failure (file missing, ffmpeg missing, whisper crash) — safe to retry
    """
    path = Path(file_path)
    if not path.exists():
        return None

    audio_path = file_path
    temp_audio = None

    if path.suffix.lower() in (".mp4", ".mkv", ".avi", ".webm"):
        has_audio = _has_audio_stream(file_path)
        if has_audio is False:
            return ""  # video without audio stream — finalize, never retry
        temp_audio = str(path.with_suffix(".tmp.ogg"))
        if not _extract_audio(file_path, temp_audio):
            return None
        audio_path = temp_audio

    try:
        model = _get_model()
        segments, info = model.transcribe(audio_path, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments)
        return text if text.strip() else ""  # empty = no speech detected
    except Exception as e:
        print(f"Ошибка транскрипции {file_path}: {e}")
        return None
    finally:
        if temp_audio:
            Path(temp_audio).unlink(missing_ok=True)


def count_pending(channel_id: str) -> int:
    return len(db.get_messages_without_transcript(channel_id))


def transcribe_channel(channel_id: str, limit: Optional[int] = None,
                        progress_callback=None) -> int:
    pending = db.get_messages_without_transcript(channel_id)

    if limit:
        pending = pending[:limit]

    completed = 0
    for i, msg in enumerate(pending):
        transcript = transcribe_file(msg["media_path"])
        # None = technical failure, don't mark (retry on next run).
        # "" = no-speech / no-audio, persist so it leaves the pending queue.
        # "text…" = success.
        if transcript is not None:
            db.update_transcript(channel_id, msg["message_id"], transcript)
            if transcript:
                completed += 1

        if progress_callback:
            progress_callback(i + 1, len(pending))

    return completed
