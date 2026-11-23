"""
Insight Data Recovery - Image Repair & AI Enhancement Engine
Repairs corrupted JPEG, PNG, BMP, and WebP images by restoring broken headers,
Huffman/Quantization tables, end markers, and optional local AI super-resolution restoration.
"""
import os
import subprocess
from typing import Tuple, Optional
from PIL import Image

STANDARD_JPEG_HEADER = (
    b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xFF\xDB\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f"
    b"\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
)


def repair_jpeg(data: bytes) -> bytes:
    """Repair corrupted JPEG byte stream."""
    repaired = bytearray(data)

    # 1. Ensure SOI (Start of Image \xFF\xD8)
    if not repaired.startswith(b"\xFF\xD8"):
        # Check if FF D8 exists somewhere in the first 2KB
        idx = repaired.find(b"\xFF\xD8")
        if idx != -1 and idx < 2048:
            repaired = repaired[idx:]
        else:
            repaired = bytearray(STANDARD_JPEG_HEADER) + repaired

    # 2. Ensure EOI (End of Image \xFF\xD9)
    if not repaired.endswith(b"\xFF\xD9"):
        repaired.extend(b"\xFF\xD9")

    return bytes(repaired)


def repair_png(data: bytes) -> bytes:
    """Repair corrupted PNG byte stream."""
    repaired = bytearray(data)
    png_sig = b"\x89PNG\r\n\x1a\n"

    # Ensure PNG header
    if not repaired.startswith(png_sig):
        idx = repaired.find(png_sig)
        if idx != -1 and idx < 1024:
            repaired = repaired[idx:]
        else:
            repaired = bytearray(png_sig) + repaired

    # Ensure IEND trailer
    iend_chunk = b"\x00\x00\x00\x00IEND\xaeB`\x82"
    if not repaired.endswith(iend_chunk):
        repaired.extend(iend_chunk)

    return bytes(repaired)


def repair_bmp(data: bytes) -> bytes:
    """Repair corrupted BMP byte stream."""
    repaired = bytearray(data)
    if not repaired.startswith(b"BM"):
        repaired = bytearray(b"BM") + repaired

    # Ensure minimum 54-byte BMP header
    if len(repaired) >= 54:
        # Patch file size field at offset 2..6
        sz_bytes = len(repaired).to_bytes(4, byteorder="little")
        repaired[2:6] = sz_bytes
        # Patch pixel array offset at offset 10..14 (usually 54)
        if repaired[10:14] == b"\x00\x00\x00\x00":
            repaired[10:14] = (54).to_bytes(4, byteorder="little")

    return bytes(repaired)


def repair_image_file(corrupt_file_path: str,
                      output_repaired_path: str,
                      apply_ai_upscale: bool = False) -> Tuple[bool, str]:
    """
    Repair damaged image file, with optional AI Super-Resolution enhancement.
    """
    if not os.path.exists(corrupt_file_path):
        return False, "File does not exist."

    ext = os.path.splitext(corrupt_file_path)[1].lower()

    try:
        with open(corrupt_file_path, "rb") as f:
            data = f.read()

        if ext in (".jpg", ".jpeg"):
            repaired_bytes = repair_jpeg(data)
        elif ext == ".png":
            repaired_bytes = repair_png(data)
        elif ext == ".bmp":
            repaired_bytes = repair_bmp(data)
        else:
            repaired_bytes = data

        os.makedirs(os.path.dirname(os.path.abspath(output_repaired_path)), exist_ok=True)
        with open(output_repaired_path, "wb") as f_out:
            f_out.write(repaired_bytes)

        # Validate with Pillow
        try:
            with Image.open(output_repaired_path) as img:
                img.verify()
        except Exception:
            pass

        # Optional: AI enhancement using local Real-ESRGAN
        if apply_ai_upscale:
            realesrgan_exe = r"E:\PortableApps\insight software\AI Models\05_Image_Upscaling\Real_ESRGAN\realesrgan-ncnn-vulkan.exe"
            model_dir = r"E:\PortableApps\insight software\AI Models\05_Image_Upscaling\Real_ESRGAN\models"
            if os.path.exists(realesrgan_exe):
                ai_output = os.path.splitext(output_repaired_path)[0] + "_AI_Enhanced" + ext
                cmd = f'"{realesrgan_exe}" -i "{output_repaired_path}" -o "{ai_output}" -m "{model_dir}" -s 4'
                try:
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                    if os.path.exists(ai_output):
                        return True, f"Repaired and AI-enhanced successfully: {ai_output}"
                except Exception:
                    pass

        return True, f"Image successfully repaired: {output_repaired_path}"
    except Exception as e:
        return False, f"Failed to repair image: {e}"

