"""
Insight Data Recovery Studio Pro - Commercial Undelete Engine v6.0
Multi-Tier Forensic Recovery Architecture (Matches & Surpasses EaseUS NTFSSearchDLL):
1) Direct NTFS $MFT + USN Change Journal ($UsnJrnl) Scanner (Administrator mode):
   - Discovers permanently deleted files/folders (Shift+Delete, Emptied Recycle Bin, Cut to another drive).
   - Discovers Cut & Moved folders within the SAME drive via $UsnJrnl RENAME_OLD_NAME records!
   - Reconstructs full original directory paths + Deleted, Target, Partition, and Lost/Orphaned buckets.
2) Recycle Bin ($Recycle.Bin $I/$R) parser with full metadata decoding.
3) Targeted folder fallback traversal when running without Administrator privileges.
4) Instantaneous Pause / Resume / Stop support across all tiers.
5) Byte-accurate cluster recovery from NTFS Data Runs, Resident MFT bytes, or live handles.
"""
import os
import sys
import time
import struct
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any, Tuple

from engine.signatures import get_category_for_ext, match_signature, ALL_CATEGORIES
from engine.ntfs_mft_scanner import NTFSMFTScanner, recover_from_ntfs_runs, read_bytes_from_ntfs_runs, is_admin


class RecoverableFile:
    def __init__(self,
                 name: str,
                 original_path: str,
                 size_bytes: int,
                 ext: str,
                 category: str,
                 deleted_time: Optional[datetime] = None,
                 quality: str = "Excellent",
                 source_type: str = "Deleted Record",
                 raw_data_offset: int = 0,
                 source_handle: Optional[str] = None):
        self.name = name
        self.original_path = original_path
        self.size_bytes = size_bytes
        self.ext = ext.lower().lstrip(".")
        self.category = category
        self.deleted_time = deleted_time or datetime.now()
        self.quality = quality
        self.source_type = source_type
        self.raw_data_offset = raw_data_offset
        self.source_handle = source_handle
        self.selected = True
        self.is_deleted = False
        self.folder_rel = ""
        self.display_folder_rel = ""
        self.raw_data_bytes: Optional[bytes] = None
        self.ntfs_data_runs: Optional[List[Tuple[int, int]]] = None
        self.ntfs_bpc: int = 4096

    @property
    def size_display(self) -> str:
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.2f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @property
    def deleted_time_str(self) -> str:
        return self.deleted_time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.original_path,
            "size": self.size_display,
            "size_bytes": self.size_bytes,
            "ext": self.ext,
            "category": self.category,
            "date": self.deleted_time_str,
            "quality": self.quality,
            "source": self.source_type
        }


class UndeleteScanner:
    """
    Commercial Undelete & Forensic NTFS Recovery Engine.
    Automatically leverages direct NTFS $MFT + $UsnJrnl when elevated, with instant Pause/Resume/Stop.
    """

    def __init__(self,
                 target_path: str,
                 selected_categories: Optional[List[str]] = None,
                 custom_extensions: Optional[List[str]] = None):
        self.target_path = os.path.normpath(os.path.abspath(target_path))
        self.selected_categories = selected_categories or ALL_CATEGORIES
        self.custom_extensions = [e.lower().lstrip(".") for e in custom_extensions] if custom_extensions else None
        self.is_running = False
        self._is_paused = False
        self.used_raw_mft = False
        self.mft_scanner: Optional[NTFSMFTScanner] = None
        self.results: List[RecoverableFile] = []

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @is_paused.setter
    def is_paused(self, val: bool):
        self._is_paused = bool(val)
        if self.mft_scanner:
            self.mft_scanner.is_paused = self._is_paused

    def stop(self):
        self.is_running = False
        self._is_paused = False
        if self.mft_scanner:
            self.mft_scanner.stop()

    def _wait_if_paused(self):
        while self._is_paused and self.is_running:
            time.sleep(0.08)

    def should_include_file(self, ext: str, category: str) -> bool:
        clean_ext = ext.lower().lstrip(".")
        if self.custom_extensions and clean_ext not in self.custom_extensions:
            return False
        if self.selected_categories and category not in self.selected_categories:
            return False
        return True

    def evaluate_file_integrity(self, file_path: str, ext: str) -> str:
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
            if not header or len(header) < 4:
                return "Damaged"
            if match_signature(header):
                return "Excellent"
            return "Good"
        except Exception:
            return "Good"

    def scan_recycle_bin(self, drive_root: str, progress_callback: Optional[Callable] = None) -> List[RecoverableFile]:
        """Scan $Recycle.Bin ($I/$R metadata & deleted files) with pause/stop support."""
        found: List[RecoverableFile] = []
        recycle_dir = os.path.join(drive_root, "$Recycle.Bin")
        if not os.path.exists(recycle_dir):
            return found

        try:
            recycle_count = 0
            for root, dirs, files in os.walk(recycle_dir, topdown=True, onerror=lambda e: None):
                self._wait_if_paused()
                if not self.is_running or recycle_count >= 2000:
                    break

                for fname in files:
                    self._wait_if_paused()
                    if not self.is_running:
                        break
                    if fname.startswith("$I") and len(fname) >= 4:
                        recycle_count += 1
                        meta_path = os.path.join(root, fname)
                        data_fname = "$R" + fname[2:]
                        data_path = os.path.join(root, data_fname)

                        try:
                            with open(meta_path, "rb") as f:
                                meta_data = f.read()

                            orig_name = ""
                            orig_size = 0
                            del_time = datetime.now()

                            if len(meta_data) >= 28 and meta_data[:4] == b"\x02\x00\x00\x00":
                                orig_size = struct.unpack("<Q", meta_data[8:16])[0]
                                ft = struct.unpack("<Q", meta_data[16:24])[0]
                                try:
                                    del_time = datetime.fromtimestamp((ft - 116444736000000000) / 10000000)
                                except Exception:
                                    pass
                                name_len = struct.unpack("<I", meta_data[24:28])[0]
                                orig_name = meta_data[28:28 + name_len * 2].decode("utf-16le", errors="ignore").rstrip("\x00")
                            elif len(meta_data) >= 24:
                                orig_size = struct.unpack("<Q", meta_data[8:16])[0]
                                ft = struct.unpack("<Q", meta_data[16:24])[0]
                                try:
                                    del_time = datetime.fromtimestamp((ft - 116444736000000000) / 10000000)
                                except Exception:
                                    pass
                                orig_name = meta_data[24:].decode("utf-16le", errors="ignore").rstrip("\x00")

                            if not orig_name:
                                orig_name = data_fname

                            # Handle deleted FOLDERS inside Recycle Bin ($Rxxxx is a directory!)
                            if os.path.isdir(data_path):
                                for r_sub, _, r_files in os.walk(data_path, onerror=lambda e: None):
                                    self._wait_if_paused()
                                    if not self.is_running:
                                        break
                                    for rf in r_files:
                                        sub_full = os.path.join(r_sub, rf)
                                        rel_inside = os.path.relpath(sub_full, data_path)
                                        reconstructed = os.path.join(orig_name, rel_inside)
                                        ext = os.path.splitext(rf)[1].lower().lstrip(".")
                                        cat = get_category_for_ext(ext)
                                        if self.should_include_file(ext, cat):
                                            sz = os.path.getsize(sub_full) if os.path.exists(sub_full) else 0
                                            rec = RecoverableFile(
                                                name=rf,
                                                original_path=reconstructed,
                                                size_bytes=sz,
                                                ext=ext,
                                                category=cat,
                                                deleted_time=del_time,
                                                quality="Excellent",
                                                source_type="Recycle Bin (Deleted Folder)",
                                                source_handle=sub_full
                                            )
                                            rec.is_deleted = True
                                            b_rel = os.path.join("Deleted & Cut Files", "Recycle Bin", os.path.basename(orig_name), os.path.dirname(rel_inside)).rstrip("\\")
                                            rec.folder_rel = b_rel.lower()
                                            rec.display_folder_rel = b_rel
                                            found.append(rec)
                            else:
                                base_name = os.path.basename(orig_name)
                                ext = os.path.splitext(base_name)[1].lower().lstrip(".")
                                cat = get_category_for_ext(ext)
                                if self.should_include_file(ext, cat):
                                    has_data = os.path.exists(data_path)
                                    # Skip orphan $I metadata stubs whose $R payload was already permanently purged
                                    # (if its raw clusters still exist on disk, the NTFS $MFT scanner recovers them directly!)
                                    if not has_data:
                                        continue
                                    actual_sz = os.path.getsize(data_path)
                                    rec = RecoverableFile(
                                        name=base_name,
                                        original_path=orig_name,
                                        size_bytes=actual_sz,
                                        ext=ext,
                                        category=cat,
                                        deleted_time=del_time,
                                        quality="Excellent",
                                        source_type="Recycle Bin",
                                        source_handle=data_path
                                    )
                                    rec.is_deleted = True
                                    b_rel = os.path.join("Deleted & Cut Files", "Recycle Bin")
                                    rec.folder_rel = b_rel.lower()
                                    rec.display_folder_rel = b_rel
                                    found.append(rec)
                        except Exception:
                            continue
        except Exception:
            pass
        return found

    def scan_targeted_folder(self, progress_callback: Optional[Callable] = None, force_fast_folder_only: bool = False) -> List[RecoverableFile]:
        """
        Comprehensive Commercial Scan:
        - Tier 1 (Admin NTFS $MFT + $UsnJrnl): Reads raw NTFS volume to uncover permanently deleted
          files, Cut/Moved folders (Ctrl+X), full partition hierarchy, and orphaned records (just like EaseUS!).
        - Tier 2 (Recycle Bin $I/$R): Recovers deleted folders & files from $Recycle.Bin.
        - Tier 3 (Fallback Directory Walk): Used cleanly if running without Admin privileges.
        """
        self.is_running = True
        self._is_paused = False
        self.results.clear()
        self.used_raw_mft = False

        drive_root = os.path.splitdrive(self.target_path)[0] + "\\"
        if not drive_root or drive_root == "\\":
            drive_root = "C:\\"

        def emit_prog(pct: int, msg: str, cnt: int, spd: float = 0.0):
            if not progress_callback:
                return
            try:
                progress_callback(pct, msg, cnt, spd)
            except TypeError:
                progress_callback(pct, msg, cnt)

        # Tier 1: Direct Raw NTFS $MFT + USN Change Journal Scan (when Admin & not forced folder-only!)
        if not force_fast_folder_only and is_admin():
            emit_prog(2, f"Opening Raw NTFS Volume ({drive_root}) — Reading $MFT & $UsnJrnl...", 0, 0.0)
            self.mft_scanner = NTFSMFTScanner(self.target_path, selected_categories=self.selected_categories)
            self.mft_scanner.is_paused = self._is_paused
            mft_ok, mft_results = self.mft_scanner.scan(progress_callback=emit_prog)
            if mft_ok and mft_results:
                self.used_raw_mft = True
                rb_items = self.scan_recycle_bin(drive_root, progress_callback)
                self.results = rb_items + mft_results
                emit_prog(100, f"NTFS $MFT Scan Complete: {len(self.results):,} files discovered.", len(self.results), 0.0)
                self.is_running = False
                return self.results

        # Tier 2: Recycle Bin Scan (works even without raw volume access!)
        emit_prog(10, f"Scanning Recycle Bin index ({drive_root})...", 0, 0.0)
        rb_found = self.scan_recycle_bin(drive_root, progress_callback)
        norm_target_low = self.target_path.rstrip("\\").lower()
        is_full_drive = (len(norm_target_low) <= 2 and norm_target_low.endswith(":"))
        for item in rb_found:
            if is_full_drive or item.original_path.lower().startswith(norm_target_low):
                self.results.append(item)

        emit_prog(25, f"Scanning location: {self.target_path}...", len(self.results), 0.0)

        # Tier 3: Filesystem Directory Traversal (Fallback when non-Admin or fast folder test)
        if os.path.exists(self.target_path):
            total_scanned = 0
            bytes_seen = 0
            t_start = time.time()
            last_emit = t_start
            target_base = os.path.basename(self.target_path) or self.target_path.rstrip("\\")

            try:
                for root, dirs, files in os.walk(self.target_path, topdown=True, onerror=lambda e: None):
                    self._wait_if_paused()
                    if not self.is_running:
                        break

                    for fname in files:
                        self._wait_if_paused()
                        if not self.is_running:
                            break

                        total_scanned += 1
                        full_path = os.path.join(root, fname)
                        ext = os.path.splitext(fname)[1].lower().lstrip(".")
                        category = get_category_for_ext(ext)

                        if not self.should_include_file(ext, category):
                            continue

                        try:
                            st = os.stat(full_path)
                            size_b = st.st_size
                            bytes_seen += size_b
                            mtime = datetime.fromtimestamp(st.st_mtime)

                            source_type = "Existing Asset"
                            if fname.startswith("~$") or fname.endswith(".tmp") or fname.endswith(".bak"):
                                source_type = "Recovered Snapshot / Temp"
                            elif "backup" in fname.lower() or "old" in fname.lower():
                                source_type = "Historical Backup"

                            quality = self.evaluate_file_integrity(full_path, ext)
                            rec_item = RecoverableFile(
                                name=fname,
                                original_path=full_path,
                                size_bytes=size_b,
                                ext=ext,
                                category=category,
                                deleted_time=mtime,
                                quality=quality,
                                source_type=source_type,
                                source_handle=full_path
                            )
                            rel = os.path.relpath(root, self.target_path)
                            rel_clean = "" if rel == "." else rel
                            disp_rel = os.path.join(target_base, rel_clean).rstrip("\\")
                            rec_item.folder_rel = disp_rel.lower()
                            rec_item.display_folder_rel = disp_rel
                            self.results.append(rec_item)

                            now = time.time()
                            if progress_callback and (now - last_emit >= 0.2 or total_scanned % 100 == 0):
                                elapsed = max(0.05, now - t_start)
                                spd = (bytes_seen / (1024 * 1024)) / elapsed
                                pct = min(95, 25 + int((total_scanned / max(200, total_scanned + 150)) * 70))
                                emit_prog(pct, f"Inspecting: {fname}", len(self.results), spd)
                                last_emit = now
                        except Exception:
                            continue
            except Exception:
                pass

        emit_prog(100, f"Scan complete. Found {len(self.results):,} files.", len(self.results), 0.0)
        self.is_running = False
        return self.results


def read_recoverable_file_bytes(item: RecoverableFile, max_bytes: int = 12 * 1024 * 1024) -> Tuple[bytes, str]:
    """
    Universal zero-write byte reader for Live Preview & Hex Inspection across ALL recovery sources:
    1. Live file or Recycle Bin $R stream (source_handle)
    2. Live file at original_path (e.g., loaded sessions)
    3. In-memory resident NTFS $MFT data or carved bytes (raw_data_bytes)
    4. Deleted NTFS non-resident clusters (ntfs_data_runs via Win32 raw volume read)
    5. Raw volume offset carved file (Format Recovery raw_data_offset)
    Returns (bytes_data, source_label).
    """
    # 1. Live file / Recycle Bin $R handle
    sh = getattr(item, "source_handle", None)
    if sh and not str(sh).startswith("\\\\.\\") and os.path.isfile(sh):
        try:
            with open(sh, "rb") as fh:
                return fh.read(max_bytes), "Live / Recycle Stream"
        except Exception:
            pass

    # 2. Live original_path fallback (useful when loading saved sessions)
    orig = getattr(item, "original_path", None)
    if orig and not str(orig).startswith("\\\\.\\") and os.path.isfile(orig):
        try:
            with open(orig, "rb") as fh:
                return fh.read(max_bytes), "Filesystem Path"
        except Exception:
            pass

    # 3. Resident NTFS $MFT bytes or in-memory carved buffer
    raw_mem = getattr(item, "raw_data_bytes", None)
    if raw_mem:
        return bytes(raw_mem[:max_bytes]), "Resident $MFT Data"

    # 4. Deleted non-resident NTFS Data Runs directly from raw volume clusters!
    ntfs_runs = getattr(item, "ntfs_data_runs", None)
    if ntfs_runs:
        drive_let = os.path.splitdrive(item.original_path or "")[0] or "C:"
        bpc = getattr(item, "ntfs_bpc", 4096)
        data = read_bytes_from_ntfs_runs(drive_let, ntfs_runs, bpc, item.size_bytes, max_bytes=max_bytes)
        if data:
            return data, f"Raw NTFS Clusters ({drive_let})"

    # 5. Raw volume LBA offset (Format Recovery carved asset)
    if sh and str(sh).startswith("\\\\.\\") and item.size_bytes > 0 and getattr(item, "raw_data_offset", 0) > 0:
        try:
            with open(sh, "rb") as raw_dev:
                sector_aligned = (item.raw_data_offset // 512) * 512
                delta = item.raw_data_offset - sector_aligned
                raw_dev.seek(sector_aligned)
                want = min(item.size_bytes, max_bytes)
                read_len = ((delta + want + 511) // 512) * 512
                buf = raw_dev.read(read_len)
                if len(buf) > delta:
                    return buf[delta:delta + want], "Raw Sector Offset"
        except Exception:
            pass

    return b"", "Unavailable / Overwritten"


def restore_file(item: RecoverableFile, destination_dir: str) -> Tuple[bool, str]:
    """
    Commercial Multi-Tier File Restoration Engine:
    1. Preserves original subfolder structure cleanly.
    2. Restores from live filesystem / Recycle Bin $R stream, resident NTFS MFT bytes,
       non-resident NTFS Data Runs (raw cluster extraction!), or Format Recovery raw LBA offset.
    """
    try:
        rel_sub = getattr(item, "display_folder_rel", "") or getattr(item, "folder_rel", "")
        # Sanitize colons/invalid chars in Windows subfolder paths
        rel_sub_safe = rel_sub.replace(":", "").strip("\\/")
        if rel_sub_safe and not os.path.isabs(rel_sub_safe) and ".." not in rel_sub_safe:
            target_folder = os.path.join(destination_dir, rel_sub_safe)
        else:
            target_folder = destination_dir

        os.makedirs(target_folder, exist_ok=True)
        dest_path = os.path.join(target_folder, item.name)

        counter = 1
        base, ext = os.path.splitext(item.name)
        while os.path.exists(dest_path):
            dest_path = os.path.join(target_folder, f"{base}_{counter}{ext}")
            counter += 1

        # Tier 1: Direct live file or Recycle Bin $R data stream
        if item.source_handle and not str(item.source_handle).startswith("\\\\.\\") and os.path.exists(item.source_handle):
            shutil.copy2(item.source_handle, dest_path)
            return True, dest_path

        # Tier 2: In-memory resident NTFS MFT bytes or raw carved bytes
        raw_bytes = getattr(item, "raw_data_bytes", None)
        if raw_bytes is not None:
            with open(dest_path, "wb") as f_out:
                f_out.write(raw_bytes)
            return True, dest_path

        # Tier 3: Non-resident NTFS $MFT Data Runs direct cluster extraction!
        ntfs_runs = getattr(item, "ntfs_data_runs", None)
        if ntfs_runs:
            drive_let = os.path.splitdrive(item.original_path)[0] or "C:"
            bpc = getattr(item, "ntfs_bpc", 4096)
            return recover_from_ntfs_runs(drive_let, ntfs_runs, bpc, item.size_bytes, dest_path)

        # Tier 4: Raw volume device offset extraction (Format Recovery)
        if item.source_handle and str(item.source_handle).startswith("\\\\.\\") and item.size_bytes > 0:
            try:
                with open(item.source_handle, "rb") as raw_dev:
                    sector_aligned = (item.raw_data_offset // 512) * 512
                    delta = item.raw_data_offset - sector_aligned
                    raw_dev.seek(sector_aligned)
                    read_len = ((delta + item.size_bytes + 511) // 512) * 512
                    buf = raw_dev.read(min(read_len, 64 * 1024 * 1024))
                    if len(buf) > delta:
                        with open(dest_path, "wb") as f_out:
                            f_out.write(buf[delta:delta + item.size_bytes])
                        return True, dest_path
            except Exception as raw_err:
                return False, f"Raw volume read requires Administrator privileges: {raw_err}"

        return False, "File data stream was already permanently overwritten or purged."
    except Exception as e:
        return False, str(e)
