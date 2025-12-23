from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path


class AudioConversionError(RuntimeError):
    pass


def decode_audio_base64(payload: str) -> bytes:
    try:
        return base64.b64decode(payload, validate=True)
    except ValueError as exc:
        raise AudioConversionError("Invalid base64 audio payload") from exc


def convert_wav_to_mp3(wav_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        wav_path = Path(tmp_dir) / "input.wav"
        mp3_path = Path(tmp_dir) / "output.mp3"
        wav_path.write_bytes(wav_bytes)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(wav_path),
                    "-ac",
                    "1",
                    "-b:a",
                    "24k",
                    str(mp3_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise AudioConversionError("ffmpeg is required for WAV->MP3 conversion") from exc
        except subprocess.CalledProcessError as exc:
            raise AudioConversionError(
                f"ffmpeg conversion failed: {exc.stderr.decode('utf-8', errors='ignore')}"
            ) from exc
        return mp3_path.read_bytes()
