# %% imports
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

_log = logging.getLogger(__name__)


# %% _parse_audio_filename
def _parse_audio_filename(filename: str) -> tuple[str, str] | None:
    """Extract (timestamp_raw, full_name) from audio filename.

    Format: YYYYMMDD_HHMMSS-firstname_lastname.mp3
    """
    m = re.match(r"^(\d{8}_\d{6})-(.+)\.mp3$", filename)
    if not m:
        return None
    ts_raw = m.group(1)
    name_part = m.group(2).replace("_", " ").strip()
    return ts_raw, name_part


# %% _get_whisper_model
_model = None

def _get_whisper_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _log.info("Loading Whisper model (base)...")
        _model = WhisperModel("base", compute_type="int8")
    return _model


# %% transcribe_audio_files
def transcribe_audio_files(dir_path: str) -> dict[str, list[dict]]:
    """Transcribe all MP3 files in dir_path/audio/ using local faster-whisper.

    Returns dict keyed by lowercase full name → list of {timestamp, text}.
    Caches results to audio_transcripts.json to avoid re-transcription.
    No-op when audio/ directory doesn't exist (backward compatible).
    """
    audio_dir = Path(dir_path) / "audio"
    if not audio_dir.is_dir():
        return {}

    cache_path = audio_dir / "audio_transcripts.json"
    mp3_files = sorted(audio_dir.glob("*.mp3"))

    if not mp3_files:
        return {}

    # Load cache
    cached: dict[str, str] = {}
    if cache_path.exists():
        with open(cache_path) as f:
            cached = json.load(f)

    # Check which files need transcription
    to_transcribe = [f for f in mp3_files if f.name not in cached]

    if to_transcribe:
        _log.info(f"Transcribing {len(to_transcribe)} audio files ({len(cached)} cached)")
        model = _get_whisper_model()

        for mp3 in to_transcribe:
            try:
                segments, _info = model.transcribe(str(mp3), language="en")
                text = " ".join(seg.text.strip() for seg in segments)
                cached[mp3.name] = text
                _log.info(f"  Transcribed: {mp3.name} ({len(text)} chars)")
            except Exception as e:
                _log.warning(f"  Failed to transcribe {mp3.name}: {e}")
                cached[mp3.name] = ""

        with open(cache_path, "w") as f:
            json.dump(cached, f, indent=2, ensure_ascii=False)

    return _build_result(cached, mp3_files)


# %% _build_result
def _build_result(cached: dict[str, str], mp3_files: list[Path]) -> dict[str, list[dict]]:
    """Group transcripts by speaker name."""
    by_name: dict[str, list[dict]] = {}
    for mp3 in mp3_files:
        parsed = _parse_audio_filename(mp3.name)
        if not parsed:
            continue
        ts_raw, full_name = parsed
        text = cached.get(mp3.name, "")
        if not text:
            continue
        key = full_name.lower()
        by_name.setdefault(key, []).append({
            "timestamp": ts_raw,
            "text": text,
            "file": mp3.name,
        })
    return by_name
