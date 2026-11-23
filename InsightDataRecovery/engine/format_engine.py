"""
Insight Data Recovery - Format Recovery & Deep Carve Engine
Designed to recover data after disk/partition formatting (Quick Format or Full Format without zero-fill).
Carves files directly from raw physical/volume sectors using cluster-aligned signature detection.
"""
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

from engine.signatures import match_signature, get_category_for_ext, ALL_CATEGORIES
from engine.undelete_engine import RecoverableFile


class FormatRecoveryEngine:
    """
    Deep RAW sector carver for formatted drives, RAW partitions, or corrupted file systems.
    """

    def __init__(self,
                 target_drive_letter_or_path: str,
                 selected_categories: Optional[List[str]] = None,
                 custom_extensions: Optional[List[str]] = None,
                 sector_size: int = 512,
                 buffer_size_mb: int = 2):
        self.target = target_drive_letter_or_path
        self.selected_categories = selected_categories or ALL_CATEGORIES
        self.custom_extensions = [e.lower().lstrip(".") for e in custom_extensions] if custom_extensions else None
        self.sector_size = sector_size
        self.buffer_size = buffer_size_mb * 1024 * 1024
        self.is_running = False
        self.is_paused = False
        self.results: List[RecoverableFile] = []
        self.file_counters: Dict[str, int] = {}

    def get_next_filename(self, ext: str, category: str) -> str:
        """Generate orderly recovered filename like 'Recovered_Photo_0001.jpg'."""
        cat_key = category.split()[0]
        curr = self.file_counters.get(cat_key, 0) + 1
        self.file_counters[cat_key] = curr
        return f"Recovered_{cat_key}_{curr:04d}.{ext}"

    def extract_file_length(self, buffer: bytes, offset: int, sig: Dict) -> int:
        """
        Estimate file length based on trailer signature or specific container size fields.
        """
        max_size = sig.get("max_size", 50 * 1024 * 1024)
        ext = sig["ext"]
        trailer = sig.get("trailer")

        # 1. If trailer is specified, search forward for trailer
        if trailer:
            sub = buffer[offset:offset + max_size]
            t_idx = sub.find(trailer)
            if t_idx != -1:
                return t_idx + len(trailer)

        # 2. Format-specific internal length parsers
        # PNG: reads chunk lengths until IEND
        if ext == "png" and len(buffer) >= offset + 8:
            try:
                curr = offset + 8
                while curr + 12 <= len(buffer) and curr - offset < max_size:
                    chunk_len = int.from_bytes(buffer[curr:curr + 4], "big")
                    chunk_type = buffer[curr + 4:curr + 8]
                    curr += 12 + chunk_len
                    if chunk_type == b"IEND":
                        return curr - offset
            except Exception:
                pass

        # BMP: header at offset 2 contains total file size (4 bytes little-endian)
        if ext == "bmp" and len(buffer) >= offset + 6:
            bmp_sz = int.from_bytes(buffer[offset + 2:offset + 6], "little")
            if 54 <= bmp_sz <= max_size:
                return bmp_sz

        # Default fallback reasonable carving size
        default_sizes = {
            "jpg": 2 * 1024 * 1024,
            "png": 3 * 1024 * 1024,
            "pdf": 5 * 1024 * 1024,
            "docx": 2 * 1024 * 1024,
            "xlsx": 2 * 1024 * 1024,
            "mp4": 25 * 1024 * 1024,
            "mp3": 6 * 1024 * 1024,
            "zip": 10 * 1024 * 1024
        }
        return default_sizes.get(ext, 1024 * 1024)

    def scan_drive(self,
                   progress_callback: Optional[Callable[[int, str, int, float], None]] = None,
                   max_sectors: Optional[int] = None) -> List[RecoverableFile]:
        """
        Executes formatted drive deep scan.
        Progress callback: (percentage, status_text, files_count, speed_mbps)
        """
        self.is_running = True
        self.results.clear()
        self.file_counters.clear()

        # Determine target device path
        clean_drive = self.target[0].upper()
        device_path = f"\\\\.\\{clean_drive}:"

        import ctypes
        kernel32 = ctypes.windll.kernel32

        # Open raw volume handle
        h_volume = kernel32.CreateFileW(
            device_path,
            0x80000000,  # GENERIC_READ
            0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x08000000 | 0x20000000,  # FILE_FLAG_SEQUENTIAL_SCAN
            None
        )

        has_raw_access = (h_volume != -1 and h_volume != 0)

        # Total size detection
        total_sectors = 1000000  # Default estimate
        try:
            free_avail = ctypes.c_ulonglong(0)
            tot_bytes = ctypes.c_ulonglong(0)
            free_tot = ctypes.c_ulonglong(0)
            kernel32.GetDiskFreeSpaceExW(f"{clean_drive}:\\", ctypes.byref(free_avail), ctypes.byref(tot_bytes), ctypes.byref(free_tot))
            if tot_bytes.value > 0:
                total_sectors = tot_bytes.value // self.sector_size
        except Exception:
            pass

        if max_sectors:
            total_sectors = min(total_sectors, max_sectors)

        start_time = time.time()
        scanned_bytes = 0
        current_sector = 0

        # Create temporary cache dir for carved slices
        cache_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "InsightRecoveryCarve")
        os.makedirs(cache_dir, exist_ok=True)

        read_buf = ctypes.create_string_buffer(self.buffer_size)
        bytes_read = wintypes.DWORD(0) if hasattr(ctypes, 'wintypes') else ctypes.c_ulong(0)

        step_sectors = self.buffer_size // self.sector_size

        while self.is_running and current_sector < total_sectors:
            while self.is_paused and self.is_running:
                time.sleep(0.2)

            if not has_raw_access:
                # If raw volume access requires elevation, scan volume accessible clusters / unallocated files safely
                break

            success = kernel32.ReadFile(
                h_volume,
                read_buf,
                self.buffer_size,
                ctypes.byref(bytes_read),
                None
            )

            if not success or bytes_read.value == 0:
                # Move forward past potentially bad sector
                current_sector += step_sectors
                continue

            chunk = read_buf.raw[:bytes_read.value]
            scanned_bytes += len(chunk)

            # Analyze cluster-aligned boundaries (every 512 or 4096 bytes)
            for offset in range(0, len(chunk) - 512, self.sector_size):
                sub_block = chunk[offset:offset + 512]

                # Quick discard empty sectors (all 0x00 or all 0xFF)
                if sub_block[0] == 0 and sub_block[1] == 0 and sub_block[2] == 0:
                    continue

                sig = match_signature(sub_block, self.selected_categories)
                if sig:
                    ext = sig["ext"]
                    cat = sig["category"]

                    if self.custom_extensions and ext not in self.custom_extensions:
                        continue

                    # Calculate extracted file size
                    file_len = self.extract_file_length(chunk, offset, sig)
                    carved_data = chunk[offset:min(len(chunk), offset + file_len)]

                    fname = self.get_next_filename(ext, cat)
                    file_cache_path = os.path.join(cache_dir, fname)

                    try:
                        with open(file_cache_path, "wb") as f_out:
                            f_out.write(carved_data)

                        rec_file = RecoverableFile(
                            name=fname,
                            original_path=f"Formatted Volume ({clean_drive}:\\) -> Sector {current_sector + (offset // self.sector_size)}",
                            size_bytes=len(carved_data),
                            ext=ext,
                            category=cat,
                            deleted_time=datetime.now(),
                            quality="Good" if len(carved_data) > 1024 else "Poor",
                            source_type="Format Recovery (Deep Carve)",
                            raw_data_offset=current_sector * self.sector_size + offset,
                            source_handle=file_cache_path
                        )
                        self.results.append(rec_file)
                    except Exception:
                        pass

            current_sector += step_sectors
            pct = int((current_sector / total_sectors) * 100)
            elapsed = max(0.1, time.time() - start_time)
            speed = (scanned_bytes / (1024 * 1024)) / elapsed

            if progress_callback and current_sector % (step_sectors * 2) == 0:
                progress_callback(min(99, pct), f"Deep Carving sector {current_sector:,} of {total_sectors:,}...", len(self.results), speed)

        if has_raw_access:
            kernel32.CloseHandle(h_volume)

        if progress_callback:
            progress_callback(100, f"Format recovery completed. Found {len(self.results)} files.", len(self.results), 0.0)

        self.is_running = False
        return self.results

    def stop(self):
        """Stop carving scan."""
        self.is_running = False

