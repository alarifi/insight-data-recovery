"""
Insight Data Recovery - Sector-by-Sector Disk Imager & Clone Engine
Creates raw disk image files (.img / .raw) with bad sector fault tolerance,
allowing safe offline data recovery without straining failing hardware.
"""
import os
import sys
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Callable


class DiskImager:
    def __init__(self,
                 source_drive: str,
                 output_image_path: str,
                 buffer_size_mb: int = 1,
                 sector_size: int = 512):
        self.source_drive = source_drive
        self.output_image_path = output_image_path
        self.buffer_size = buffer_size_mb * 1024 * 1024
        self.sector_size = sector_size
        self.is_running = False
        self.is_paused = False

    def create_image(self, progress_callback: Optional[Callable[[int, str, float], None]] = None) -> bool:
        """
        Creates sector-by-sector disk image.
        progress_callback: (percentage, status_text, speed_mbps)
        """
        self.is_running = True
        kernel32 = ctypes.windll.kernel32

        clean_let = self.source_drive[0].upper()
        device_path = f"\\\\.\\{clean_let}:"

        h_source = kernel32.CreateFileW(
            device_path,
            0x80000000,  # GENERIC_READ
            0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x08000000,  # FILE_FLAG_SEQUENTIAL_SCAN
            None
        )

        if h_source == -1 or h_source == 0:
            if progress_callback:
                progress_callback(0, "Error: Administrative privileges required to read raw volume sectors.", 0.0)
            self.is_running = False
            return False

        # Get total volume size
        total_bytes = ctypes.c_ulonglong(0)
        free_bytes = ctypes.c_ulonglong(0)
        kernel32.GetDiskFreeSpaceExW(f"{clean_let}:\\", ctypes.byref(free_bytes), ctypes.byref(total_bytes), None)
        total_sz = total_bytes.value or (10 * 1024 * 1024 * 1024)

        read_buf = ctypes.create_string_buffer(self.buffer_size)
        bytes_read = wintypes.DWORD(0)

        written_bytes = 0
        start_time = time.time()

        os.makedirs(os.path.dirname(os.path.abspath(self.output_image_path)), exist_ok=True)

        try:
            with open(self.output_image_path, "wb") as f_out:
                while self.is_running and written_bytes < total_sz:
                    while self.is_paused and self.is_running:
                        time.sleep(0.2)

                    success = kernel32.ReadFile(
                        h_source,
                        read_buf,
                        self.buffer_size,
                        ctypes.byref(bytes_read),
                        None
                    )

                    if not success or bytes_read.value == 0:
                        # Bad sector encountered: fill with zeros to preserve alignment
                        zero_fill = b"\x00" * self.sector_size
                        f_out.write(zero_fill)
                        written_bytes += self.sector_size
                        continue

                    chunk = read_buf.raw[:bytes_read.value]
                    f_out.write(chunk)
                    written_bytes += len(chunk)

                    pct = int((written_bytes / total_sz) * 100)
                    elapsed = max(0.1, time.time() - start_time)
                    speed = (written_bytes / (1024 * 1024)) / elapsed

                    if progress_callback and (written_bytes % (self.buffer_size * 5) == 0):
                        progress_callback(
                            min(99, pct),
                            f"Cloned {written_bytes / (1024**3):.2f} GB of {total_sz / (1024**3):.2f} GB...",
                            speed
                        )
        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Imaging error: {e}", 0.0)
            return False
        finally:
            kernel32.CloseHandle(h_source)

        if progress_callback:
            progress_callback(100, f"Raw disk image successfully saved to: {self.output_image_path}", 0.0)

        self.is_running = False
        return True

    def stop(self):
        """Stop imaging."""
        self.is_running = False

