from __future__ import annotations

import base64
import struct
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


def convert_raw_pcm_to_mp3(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    """
    Convert raw PCM audio data (int16) to MP3 using ffmpeg.

    Args:
        pcm_bytes: Raw PCM audio data (16-bit signed integer, mono)
        sample_rate: Sample rate in Hz (default: 24000 for Qwen)

    Returns:
        MP3 encoded audio data
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_path = Path(tmp_dir) / "input.raw"
        mp3_path = Path(tmp_dir) / "output.mp3"
        raw_path.write_bytes(pcm_bytes)

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "s16le",  # PCM signed 16-bit little-endian
                    "-ar",
                    str(sample_rate),
                    "-ac",
                    "1",
                    "-i",
                    str(raw_path),
                    "-b:a",
                    "24k",
                    str(mp3_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise AudioConversionError("ffmpeg is required for PCM->MP3 conversion") from exc
        except subprocess.CalledProcessError as exc:
            raise AudioConversionError(
                f"ffmpeg conversion failed: {exc.stderr.decode('utf-8', errors='ignore')}"
            ) from exc
        return mp3_path.read_bytes()


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


def convert_audio_to_mp3(audio_bytes: bytes, input_suffix: str = ".webm") -> bytes:
    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / f"input{input_suffix}"
        mp3_path = Path(tmp_dir) / "output.mp3"
        input_path.write_bytes(audio_bytes)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    str(input_path),
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
            raise AudioConversionError("ffmpeg is required for audio->MP3 conversion") from exc
        except subprocess.CalledProcessError as exc:
            raise AudioConversionError(
                f"ffmpeg conversion failed: {exc.stderr.decode('utf-8', errors='ignore')}"
            ) from exc
        return mp3_path.read_bytes()
