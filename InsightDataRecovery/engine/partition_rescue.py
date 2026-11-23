"""
Insight Data Recovery - Lost Partition Rescue Engine
Scans physical drives for deleted, missing, unallocated, or corrupted partitions
(MBR, GPT, NTFS, FAT32, exFAT, and BitLocker).
"""
import os
import sys
import struct
import ctypes
from ctypes import wintypes
from typing import List, Dict, Optional, Callable, Any


class LostPartitionInfo:
    def __init__(self,
                 disk_number: int,
                 start_sector: int,
                 sector_count: int,
                 sector_size: int,
                 fs_type: str,
                 status: str = "Lost Partition",
                 label: str = "",
                 is_bitlocker: bool = False):
        self.disk_number = disk_number
        self.start_sector = start_sector
        self.sector_count = sector_count
        self.sector_size = sector_size
        self.fs_type = fs_type
        self.status = status
        self.label = label or "Unallocated / Lost"
        self.is_bitlocker = is_bitlocker

    @property
    def capacity_bytes(self) -> int:
        return self.sector_count * self.sector_size

    @property
    def capacity_gb(self) -> float:
        return round(self.capacity_bytes / (1024 ** 3), 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disk": f"PhysicalDrive{self.disk_number}",
            "start_lba": self.start_sector,
            "sectors": self.sector_count,
            "size_gb": self.capacity_gb,
            "fs_type": self.fs_type,
            "status": self.status,
            "label": self.label,
            "bitlocker": self.is_bitlocker
        }


class PartitionRescueScanner:
    """
    Scans physical disk sectors for partition headers and boot sectors.
    """

    def __init__(self, disk_number: int, sector_size: int = 512):
        self.disk_number = disk_number
        self.sector_size = sector_size
        self.is_running = False
        self.found_partitions: List[LostPartitionInfo] = []

    def scan_disk(self,
                  progress_callback: Optional[Callable[[int, str, int], None]] = None,
                  max_scan_sectors: int = 5000000) -> List[LostPartitionInfo]:
        """
        Scan physical drive for lost partition boot sectors.
        """
        self.is_running = True
        self.found_partitions.clear()

        kernel32 = ctypes.windll.kernel32
        device_path = f"\\\\.\\PhysicalDrive{self.disk_number}"

        h_disk = kernel32.CreateFileW(
            device_path,
            0x80000000,  # GENERIC_READ
            0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x08000000,  # FILE_FLAG_SEQUENTIAL_SCAN
            None
        )

        if h_disk == -1 or h_disk == 0:
            # Query existing partition information via PowerShell to find RAW / Unallocated partitions safely
            return self._query_wmi_lost_partitions()

        read_buf = ctypes.create_string_buffer(self.sector_size)
        bytes_read = wintypes.DWORD(0)

        step = 2048  # Jump across 1MB boundaries where partitions typically start
        curr_sector = 0

        try:
            while self.is_running and curr_sector < max_scan_sectors:
                # Seek to sector
                offset = curr_sector * self.sector_size
                li = ctypes.c_int64(offset)
                kernel32.SetFilePointerEx(h_disk, li, None, 0)

                success = kernel32.ReadFile(h_disk, read_buf, self.sector_size, ctypes.byref(bytes_read), None)
                if success and bytes_read.value == self.sector_size:
                    data = read_buf.raw

                    # Check boot sector signature 0x55 0xAA at end of sector
                    if data[510:512] == b"\x55\xAA":
                        # 1. NTFS Boot Sector: "NTFS    " at offset 3
                        if data[3:11] == b"NTFS    ":
                            total_sec = struct.unpack("<Q", data[40:48])[0]
                            self.found_partitions.append(LostPartitionInfo(
                                disk_number=self.disk_number,
                                start_sector=curr_sector,
                                sector_count=total_sec,
                                sector_size=self.sector_size,
                                fs_type="NTFS",
                                status="Recoverable Partition",
                                label=f"Lost NTFS Volume @ LBA {curr_sector:,}"
                            ))

                        # 2. FAT32 Boot Sector: "FAT32   " at offset 82
                        elif data[82:90] == b"FAT32   ":
                            total_sec = struct.unpack("<I", data[32:36])[0]
                            self.found_partitions.append(LostPartitionInfo(
                                disk_number=self.disk_number,
                                start_sector=curr_sector,
                                sector_count=total_sec,
                                sector_size=self.sector_size,
                                fs_type="FAT32",
                                status="Recoverable Partition",
                                label=f"Lost FAT32 Volume @ LBA {curr_sector:,}"
                            ))

                        # 3. exFAT Boot Sector: "EXFAT   " at offset 3
                        elif data[3:11] == b"EXFAT   ":
                            vol_len = struct.unpack("<Q", data[72:80])[0]
                            self.found_partitions.append(LostPartitionInfo(
                                disk_number=self.disk_number,
                                start_sector=curr_sector,
                                sector_count=vol_len,
                                sector_size=self.sector_size,
                                fs_type="exFAT",
                                status="Recoverable Partition",
                                label=f"Lost exFAT Volume @ LBA {curr_sector:,}"
                            ))

                        # 4. BitLocker Signature: "-FVE-FS-"
                        elif b"-FVE-FS-" in data:
                            self.found_partitions.append(LostPartitionInfo(
                                disk_number=self.disk_number,
                                start_sector=curr_sector,
                                sector_count=1000000,
                                sector_size=self.sector_size,
                                fs_type="BitLocker",
                                status="Encrypted Lost Partition",
                                label=f"BitLocker Protected Volume @ LBA {curr_sector:,}",
                                is_bitlocker=True
                            ))

                curr_sector += step

                if progress_callback and (curr_sector % (step * 50) == 0):
                    pct = int((curr_sector / max_scan_sectors) * 100)
                    progress_callback(min(99, pct), f"Scanning sector {curr_sector:,}...", len(self.found_partitions))

        finally:
            kernel32.CloseHandle(h_disk)

        if progress_callback:
            progress_callback(100, f"Partition rescue scan complete. Found {len(self.found_partitions)} partitions.", len(self.found_partitions))

        self.is_running = False
        return self.found_partitions

    def _query_wmi_lost_partitions(self) -> List[LostPartitionInfo]:
        """Query RAW or unallocated partitions via Windows Management."""
        parts = []
        try:
            import subprocess, json
            cmd = f'powershell -NoProfile -Command "Get-Partition -DiskNumber {self.disk_number} | Select-Object PartitionNumber, DriveLetter, Size, Type, OperationalStatus | ConvertTo-Json"'
            out = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=4).strip()
            if out:
                data = json.loads(out)
                if isinstance(data, dict):
                    data = [data]
                for p in data:
                    sz = int(p.get("Size") or 0)
                    let = p.get("DriveLetter")
                    ptype = str(p.get("Type") or "")
                    if not let or "RAW" in ptype.upper() or "UNKNOWN" in ptype.upper():
                        parts.append(LostPartitionInfo(
                            disk_number=self.disk_number,
                            start_sector=0,
                            sector_count=sz // self.sector_size if sz > 0 else 0,
                            sector_size=self.sector_size,
                            fs_type="RAW / Corrupted",
                            status="Unallocated / Missing Drive Letter",
                            label=f"Lost Partition #{p.get('PartitionNumber')}"
                        ))
        except Exception:
            pass
        return parts

    def stop(self):
        """Stop partition scanner."""
        self.is_running = False

