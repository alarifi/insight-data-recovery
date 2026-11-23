"""
Insight Data Recovery - Video Repair Engine
Repairs corrupted MP4, MOV, MKV, and AVI videos using container atom reconstruction (moov atom recovery),
sample video parameter transplantation, and bundled offline FFmpeg stream salvage.
"""
import os
import sys
import shutil
import subprocess
from typing import Tuple, Optional


def resolve_ffmpeg_path() -> Optional[str]:
    """
    Locate bundled or local offline ffmpeg.exe across all deployment modes:
    1. PyInstaller frozen bundle (sys._MEIPASS/bin/ffmpeg.exe -> InsightRecovery/bin/ffmpeg.exe)
    2. Executable directory (bin/ffmpeg.exe or InsightRecovery/bin/ffmpeg.exe)
    3. Source project directory (InsightDataRecovery/bin/ffmpeg.exe)
    4. Local developer AI Models cache
    5. System PATH
    """
    candidates = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            candidates.append(os.path.join(meipass, "bin", "ffmpeg.exe"))
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates.append(os.path.join(exe_dir, "bin", "ffmpeg.exe"))
        candidates.append(os.path.join(exe_dir, "InsightRecovery", "bin", "ffmpeg.exe"))

    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(pkg_root, "bin", "ffmpeg.exe"))
    candidates.append(r"E:\PortableApps\insight software\AI Models\15_ffmpeg_ffprobe_ffplay\35\ffmpeg.exe")
    candidates.append(r"E:\PortableApps\insight software\AI Models\15_ffmpeg_ffprobe_ffplay\ffmpeg.exe")

    for path in candidates:
        if path and os.path.isfile(path):
            return path

    found_in_path = shutil.which("ffmpeg")
    if found_in_path and os.path.isfile(found_in_path):
        return found_in_path
    return None


def _run_silent(cmd: list, timeout: int = 45) -> subprocess.CompletedProcess:
    """Run an external CLI command without flashing a Windows console window."""
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "timeout": timeout,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, **kwargs)


def find_atom(data: bytes, atom_type: bytes, start: int = 0) -> int:
    """Find location of 4-byte atom signature like b'moov' or b'mdat'."""
    return data.find(atom_type, start)


def extract_moov_atom(sample_video_path: str) -> Optional[bytes]:
    """Extract complete moov atom from a healthy sample video."""
    try:
        with open(sample_video_path, "rb") as f:
            data = f.read()

        idx = find_atom(data, b"moov")
        if idx >= 4:
            atom_len = int.from_bytes(data[idx - 4:idx], "big")
            if 8 <= atom_len <= len(data) - (idx - 4):
                return data[idx - 4:idx - 4 + atom_len]
    except Exception:
        pass
    return None


def repair_video_file(
    corrupt_file_path: str,
    output_repaired_path: str,
    sample_video_path: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Repair damaged MP4/MOV/MKV/AVI video file.
    Stage 1: Sample Video moov atom transplantation + FFmpeg faststart sanitization.
    Stage 2: Bundled FFmpeg stream demux & remux salvage (-c copy -movflags faststart).
    Stage 3: Bundled FFmpeg frame-level H.264/AAC recovery re-encode.
    """
    if not os.path.exists(corrupt_file_path):
        return False, "Corrupted video file does not exist."

    ffmpeg_path = resolve_ffmpeg_path()
    os.makedirs(os.path.dirname(os.path.abspath(output_repaired_path)), exist_ok=True)

    # Method 1: Sample Video moov atom transplantation (if sample provided)
    if sample_video_path and os.path.exists(sample_video_path):
        try:
            moov_bytes = extract_moov_atom(sample_video_path)
            if moov_bytes:
                with open(corrupt_file_path, "rb") as f:
                    corrupt_data = f.read()

                mdat_idx = find_atom(corrupt_data, b"mdat")
                if mdat_idx != -1:
                    ftyp_chunk = (
                        corrupt_data[:mdat_idx - 4]
                        if mdat_idx >= 4
                        else b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
                    )
                    mdat_chunk = corrupt_data[max(0, mdat_idx - 4):]

                    stitched_file = os.path.splitext(output_repaired_path)[0] + "_stitched.mp4"
                    with open(stitched_file, "wb") as f_out:
                        f_out.write(ftyp_chunk)
                        f_out.write(moov_bytes)
                        f_out.write(mdat_chunk)

                    if ffmpeg_path:
                        cmd = [
                            ffmpeg_path, "-y", "-err_detect", "ignore_err",
                            "-i", stitched_file, "-c", "copy", "-movflags", "faststart",
                            output_repaired_path,
                        ]
                        res = _run_silent(cmd, timeout=45)
                        if res.returncode == 0 and os.path.exists(output_repaired_path) and os.path.getsize(output_repaired_path) > 512:
                            try:
                                os.remove(stitched_file)
                            except Exception:
                                pass
                            return True, f"Video repaired via moov transplantation + FFmpeg: {output_repaired_path}"
                    else:
                        shutil.move(stitched_file, output_repaired_path)
                        return True, f"Video moov container reconstructed: {output_repaired_path}"
        except Exception:
            pass

    # Method 2: Bundled FFmpeg Stream Demux & Remux / Frame Recovery
    if ffmpeg_path:
        try:
            cmd_copy = [
                ffmpeg_path, "-y", "-err_detect", "ignore_err",
                "-i", corrupt_file_path, "-c", "copy", "-movflags", "faststart",
                output_repaired_path,
            ]
            res = _run_silent(cmd_copy, timeout=45)
            if res.returncode == 0 and os.path.exists(output_repaired_path) and os.path.getsize(output_repaired_path) > 512:
                return True, f"Video stream salvaged and remuxed (FFmpeg): {output_repaired_path}"

            # Fallback frame-level re-encode if stream copy failed
            cmd_reencode = [
                ffmpeg_path, "-y", "-err_detect", "ignore_err",
                "-i", corrupt_file_path, "-c:v", "libx264", "-preset", "ultrafast",
                "-crf", "23", "-c:a", "aac", "-movflags", "faststart",
                output_repaired_path,
            ]
            res_re = _run_silent(cmd_reencode, timeout=60)
            if res_re.returncode == 0 and os.path.exists(output_repaired_path) and os.path.getsize(output_repaired_path) > 512:
                return True, f"Video frames recovered and re-encoded (FFmpeg): {output_repaired_path}"
        except Exception as e:
            return False, f"FFmpeg processing error: {e}"

    return False, "Could not repair video structure without valid frame indices or FFmpeg engine."
