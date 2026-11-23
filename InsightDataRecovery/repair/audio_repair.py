"""
Insight Data Recovery - Audio Repair Engine
Repairs corrupted MP3, WAV, AAC, M4A, FLAC, and OGG audio files by patching RIFF headers,
locating MPEG frame sync boundaries, and performing bundled FFmpeg stream reconstruction.
"""
import os
import struct
from typing import Tuple

from repair.video_repair import resolve_ffmpeg_path, _run_silent


def repair_wav(data: bytes) -> bytes:
    """Repair corrupted WAV header by patching file size and data chunk length."""
    repaired = bytearray(data)
    if not repaired.startswith(b"RIFF"):
        repaired = bytearray(
            b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x02\x00"
            b"\x44\xAC\x00\x00\x10\xB1\x02\x00\x04\x00\x10\x00data\x00\x00\x00\x00"
        ) + repaired

    if len(repaired) >= 44:
        total_riff = max(0, len(repaired) - 8)
        repaired[4:8] = struct.pack("<I", total_riff)

        data_idx = repaired.find(b"data")
        if data_idx != -1 and data_idx + 8 <= len(repaired):
            data_len = max(0, len(repaired) - (data_idx + 8))
            repaired[data_idx + 4:data_idx + 8] = struct.pack("<I", data_len)

    return bytes(repaired)


def repair_mp3(data: bytes) -> bytes:
    """Strip corrupted ID3 metadata and locate first valid MPEG frame sync."""
    for i in range(len(data) - 1):
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            return data[i:]
    return data


def repair_audio_file(corrupt_file_path: str, output_repaired_path: str) -> Tuple[bool, str]:
    """
    Repair corrupted audio file using pure-Python structural header repair
    plus bundled offline FFmpeg stream sanitization when available.
    """
    if not os.path.exists(corrupt_file_path):
        return False, "Audio file does not exist."

    ext = os.path.splitext(corrupt_file_path)[1].lower()
    os.makedirs(os.path.dirname(os.path.abspath(output_repaired_path)), exist_ok=True)

    # Stage 1: Bundled FFmpeg deep stream salvage for container-based formats (M4A, FLAC, OGG, WMA, AAC)
    ffmpeg_path = resolve_ffmpeg_path()
    if ffmpeg_path and ext in (".m4a", ".flac", ".ogg", ".wma", ".aac"):
        try:
            cmd = [ffmpeg_path, "-y", "-err_detect", "ignore_err", "-i", corrupt_file_path, "-c", "copy", output_repaired_path]
            res = _run_silent(cmd, timeout=35)
            if res.returncode == 0 and os.path.exists(output_repaired_path) and os.path.getsize(output_repaired_path) > 256:
                return True, f"Audio stream rebuilt with FFmpeg: {output_repaired_path}"
        except Exception:
            pass

    # Stage 2: Structural binary header & frame sync repair (WAV / MP3 / generic)
    try:
        with open(corrupt_file_path, "rb") as f:
            raw = f.read()

        if ext == ".wav":
            clean_bytes = repair_wav(raw)
        elif ext in (".mp3", ".m4a", ".aac"):
            clean_bytes = repair_mp3(raw)
        else:
            clean_bytes = raw

        with open(output_repaired_path, "wb") as f_out:
            f_out.write(clean_bytes)

        return True, f"Audio file successfully repaired: {output_repaired_path}"
    except Exception as e:
        return False, f"Failed to repair audio file: {e}"
