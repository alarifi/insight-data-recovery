r"""
Insight Data Recovery Studio Pro - Forensic NTFS $MFT & USN Change Journal Engine
Direct low-level Windows NTFS volume scanner (equivalent to EaseUS NTFSSearchDLL.dll):
1. Opens raw NTFS volume (\\.\X:) via Win32 CreateFileW (Administrator mode).
2. Parses NTFS Volume Boot Record (VBR) + Record #0 ($MFT) fragmented Data Runs.
3. Streams ALL 1024-byte MFT FILE records in 4 MB chunks with USA fixup restoration.
4. Discovers:
   - Permanently Deleted files & folders (Shift+Delete, Emptied Recycle Bin, Cut to another drive) via IN_USE == 0.
   - Cut / Moved files & folders within the SAME drive via NTFS USN Change Journal ($UsnJrnl RENAME_OLD_NAME / FILE_DELETE).
   - Existing files & full partition directory tree reconstructed from Parent MFT Reference Numbers.
   - Lost / Orphaned files whose parent directory record was overwritten.
5. Decodes resident $DATA bytes & non-resident $DATA Data Runs for true byte-level cluster recovery.
6. Supports instantaneous Pause / Resume / Stop and live progressive streaming callbacks.
"""
import os
import sys
import time
import struct
import ctypes
from ctypes import wintypes
from datetime import datetime
from typing import List, Dict, Optional, Callable, Tuple, Set

from engine.signatures import get_category_for_ext, ALL_CATEGORIES

# Win32 Constants
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
FILE_BEGIN = 0

FSCTL_GET_NTFS_VOLUME_DATA = 0x00090064
FSCTL_QUERY_USN_JOURNAL = 0x000900F4
FSCTL_READ_USN_JOURNAL = 0x000900BB

USN_REASON_FILE_DELETE = 0x00000200
USN_REASON_RENAME_OLD_NAME = 0x00001000
USN_REASON_RENAME_NEW_NAME = 0x00002000

kernel32 = ctypes.windll.kernel32
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
]
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.SetFilePointerEx.argtypes = [
    wintypes.HANDLE, ctypes.c_longlong, ctypes.POINTER(ctypes.c_longlong), wintypes.DWORD
]
kernel32.SetFilePointerEx.restype = wintypes.BOOL
kernel32.ReadFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
kernel32.ReadFile.restype = wintypes.BOOL
kernel32.DeviceIoControl.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
kernel32.DeviceIoControl.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


def is_admin() -> bool:
    """Check if the current process has Windows Administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def filetime_to_datetime(ft: int) -> datetime:
    """Convert 64-bit Windows FILETIME to Python datetime safely."""
    if not ft or ft < 116444736000000000:
        return datetime.now()
    try:
        ts = (ft - 116444736000000000) / 10000000.0
        if 0 < ts < 4102444800:  # Between 1970 and 2100
            return datetime.fromtimestamp(ts)
    except Exception:
        pass
    return datetime.now()


def decode_data_runs(run_bytes: bytes) -> List[Tuple[int, int]]:
    """
    Decode NTFS non-resident attribute Data Runs into [(start_lcn, cluster_count), ...].
    Sparse runs are represented with start_lcn = -1.
    """
    runs: List[Tuple[int, int]] = []
    idx = 0
    n = len(run_bytes)
    current_lcn = 0

    while idx < n:
        header = run_bytes[idx]
        if header == 0:
            break
        len_sz = header & 0x0F
        off_sz = (header >> 4) & 0x0F
        idx += 1
        if len_sz == 0 or idx + len_sz + off_sz > n:
            break

        cluster_count = int.from_bytes(run_bytes[idx:idx + len_sz], "little", signed=False)
        idx += len_sz

        if off_sz > 0:
            lcn_delta = int.from_bytes(run_bytes[idx:idx + off_sz], "little", signed=True)
            idx += off_sz
            current_lcn += lcn_delta
            if current_lcn >= 0 and cluster_count > 0:
                runs.append((current_lcn, cluster_count))
        else:
            if cluster_count > 0:
                runs.append((-1, cluster_count))

    return runs


def apply_usa_fixup(record: bytearray, bytes_per_sector: int = 512) -> bool:
    """Restore NTFS Update Sequence Array (USA) sector end bytes in-place."""
    if len(record) < 48 or record[0:4] != b"FILE":
        return False
    usa_off, usa_cnt = struct.unpack_from("<HH", record, 4)
    if usa_off < 42 or usa_cnt < 2 or usa_off + usa_cnt * 2 > len(record):
        return False

    usn0 = record[usa_off]
    usn1 = record[usa_off + 1]
    for s in range(1, usa_cnt):
        sec_end = s * bytes_per_sector - 2
        if sec_end + 2 > len(record):
            break
        if record[sec_end] == usn0 and record[sec_end + 1] == usn1:
            fix_off = usa_off + s * 2
            record[sec_end] = record[fix_off]
            record[sec_end + 1] = record[fix_off + 1]
    return True


def open_raw_volume(drive_letter: str):
    """Open raw NTFS volume handle (e.g. \\\\.\\C:) via Win32 CreateFileW."""
    clean = drive_letter[0].upper()
    vol_path = f"\\\\.\\{clean}:"
    handle = kernel32.CreateFileW(
        vol_path,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None,
        OPEN_EXISTING,
        FILE_FLAG_SEQUENTIAL_SCAN,
        None
    )
    if handle == INVALID_HANDLE_VALUE or handle == 0 or handle == -1:
        return None
    return handle


def read_volume_at(handle, byte_offset: int, length: int) -> bytes:
    """Seek and read exact aligned bytes from a raw Windows volume handle."""
    new_pos = ctypes.c_longlong(0)
    if not kernel32.SetFilePointerEx(handle, byte_offset, ctypes.byref(new_pos), FILE_BEGIN):
        return b""
    buf = ctypes.create_string_buffer(length)
    bytes_read = wintypes.DWORD(0)
    if not kernel32.ReadFile(handle, buf, length, ctypes.byref(bytes_read), None):
        return b""
    return buf.raw[:bytes_read.value]


def parse_ntfs_boot_sector(handle) -> Optional[Dict[str, int]]:
    """Parse 512-byte NTFS Volume Boot Record (VBR) to get cluster & MFT geometry."""
    vbr = read_volume_at(handle, 0, 512)
    if len(vbr) < 84 or vbr[3:11] != b"NTFS    ":
        return None

    bytes_per_sector = struct.unpack_from("<H", vbr, 0x0B)[0] or 512
    sectors_per_cluster = vbr[0x0D] or 8
    bytes_per_cluster = bytes_per_sector * sectors_per_cluster
    total_sectors = struct.unpack_from("<Q", vbr, 0x28)[0]
    mft_start_lcn = struct.unpack_from("<Q", vbr, 0x30)[0]
    mft_mirr_lcn = struct.unpack_from("<Q", vbr, 0x38)[0]
    c_per_rec = struct.unpack_from("<b", vbr, 0x40)[0]

    if c_per_rec < 0:
        record_size = 1 << (-c_per_rec)
    else:
        record_size = c_per_rec * bytes_per_cluster

    if record_size not in (512, 1024, 2048, 4096):
        record_size = 1024

    return {
        "bytes_per_sector": bytes_per_sector,
        "sectors_per_cluster": sectors_per_cluster,
        "bytes_per_cluster": bytes_per_cluster,
        "total_sectors": total_sectors,
        "mft_start_lcn": mft_start_lcn,
        "mft_mirr_lcn": mft_mirr_lcn,
        "record_size": record_size,
    }


def parse_mft_record_minimal(rec_bytes: bytes, record_size: int, bytes_per_sector: int, seq_index: int) -> Optional[Dict]:
    """
    Fast forensic parser for a single 1024-byte NTFS MFT record.
    Extracts: record_num, flags, is_in_use, is_dir, filename, parent_ref, mtime,
              file_size, resident_data, data_runs.
    """
    if len(rec_bytes) < 56 or rec_bytes[0:4] != b"FILE":
        return None

    rec = bytearray(rec_bytes)
    apply_usa_fixup(rec, bytes_per_sector)

    first_attr_off, flags = struct.unpack_from("<HH", rec, 0x14)
    is_in_use = bool(flags & 0x0001)
    is_dir = bool(flags & 0x0002)

    rec_num = struct.unpack_from("<I", rec, 0x2C)[0]
    if rec_num == 0 and seq_index > 0:
        rec_num = seq_index

    pos = first_attr_off
    best_name = ""
    best_ns = -1
    parent_ref = 5
    mtime_ft = 0
    fn_size_hint = 0
    data_size = -1
    resident_data: Optional[bytes] = None
    data_runs: Optional[List[Tuple[int, int]]] = None

    while 48 <= pos <= record_size - 16:
        attr_type, attr_len = struct.unpack_from("<II", rec, pos)
        if attr_type == 0xFFFFFFFF or attr_len < 16 or pos + attr_len > record_size:
            break

        non_res = rec[pos + 8]
        name_len = rec[pos + 9]

        # 0x10: $STANDARD_INFORMATION
        if attr_type == 0x10 and non_res == 0:
            c_size, c_off = struct.unpack_from("<IH", rec, pos + 16)
            c_start = pos + c_off
            if c_size >= 32 and c_start + 32 <= pos + attr_len:
                mtime_ft = struct.unpack_from("<Q", rec, c_start + 8)[0]

        # 0x30: $FILE_NAME
        elif attr_type == 0x30 and non_res == 0:
            c_size, c_off = struct.unpack_from("<IH", rec, pos + 16)
            c_start = pos + c_off
            if c_size >= 68 and c_start + 66 <= pos + attr_len:
                p_ref = struct.unpack_from("<Q", rec, c_start)[0] & 0x0000FFFFFFFFFFFF
                fn_mtime = struct.unpack_from("<Q", rec, c_start + 16)[0]
                fn_real_sz = struct.unpack_from("<Q", rec, c_start + 48)[0]
                fn_len = rec[c_start + 64]
                ns = rec[c_start + 65]
                fn_end = c_start + 66 + fn_len * 2
                if fn_len > 0 and fn_end <= pos + attr_len:
                    # Prefer Win32 (1) or Win32&DOS (3) over DOS 8.3 (2)
                    if best_ns == -1 or (best_ns == 2 and ns != 2) or (ns in (1, 3) and best_ns not in (1, 3)):
                        best_name = bytes(rec[c_start + 66:fn_end]).decode("utf-16le", errors="ignore")
                        best_ns = ns
                        parent_ref = p_ref
                        fn_size_hint = fn_real_sz
                        if not mtime_ft:
                            mtime_ft = fn_mtime

        # 0x80: $DATA (primary unnamed stream)
        elif attr_type == 0x80 and name_len == 0:
            if non_res == 0:
                c_size, c_off = struct.unpack_from("<IH", rec, pos + 16)
                c_start = pos + c_off
                if c_start + c_size <= pos + attr_len:
                    data_size = c_size
                    if not is_in_use and c_size <= 1024:
                        resident_data = bytes(rec[c_start:c_start + c_size])
            else:
                if pos + 56 <= pos + attr_len:
                    run_off = struct.unpack_from("<H", rec, pos + 32)[0]
                    real_sz = struct.unpack_from("<Q", rec, pos + 48)[0]
                    data_size = real_sz
                    # Always decode data runs for deleted files (or Record #0 $MFT!)
                    if (not is_in_use or rec_num == 0) and pos + run_off < pos + attr_len:
                        data_runs = decode_data_runs(bytes(rec[pos + run_off:pos + attr_len]))

        pos += attr_len

    if not best_name:
        return None

    final_size = data_size if data_size >= 0 else fn_size_hint
    return {
        "rec_num": rec_num,
        "is_in_use": is_in_use,
        "is_dir": is_dir,
        "name": best_name,
        "parent_ref": parent_ref,
        "mtime_ft": mtime_ft,
        "size": final_size,
        "resident_data": resident_data,
        "data_runs": data_runs,
    }


def query_usn_journal_deleted_and_moved(handle, max_records: int = 120000) -> Dict[int, Dict]:
    """
    Query Windows NTFS USN Change Journal ($UsnJrnl) for recent FILE_DELETE and RENAME_OLD_NAME events.
    This specifically catches files & folders that were CUT (Ctrl+X -> Ctrl+V) to another folder on the SAME drive!
    Returns mapping: file_mft_ref -> {name, parent_ref, timestamp, reason, is_dir}.
    """
    discovered: Dict[int, Dict] = {}
    try:
        # 1. FSCTL_QUERY_USN_JOURNAL -> USN_JOURNAL_DATA_V0 (56 bytes)
        out_buf = ctypes.create_string_buffer(64)
        bytes_ret = wintypes.DWORD(0)
        ok = kernel32.DeviceIoControl(
            handle, FSCTL_QUERY_USN_JOURNAL,
            None, 0,
            out_buf, 64,
            ctypes.byref(bytes_ret), None
        )
        if not ok or bytes_ret.value < 56:
            return discovered

        journal_id, first_usn, next_usn = struct.unpack_from("<Qqq", out_buf.raw, 0)
        # Scan the most recent ~32 MB of journal activity for blazing speed
        start_usn = max(first_usn, next_usn - (32 * 1024 * 1024))

        # READ_USN_JOURNAL_DATA_V0 (40 bytes):
        # StartUsn(q), ReasonMask(I), ReturnOnlyOnClose(I), Timeout(Q), BytesToWaitFor(Q), UsnJournalID(Q)
        reason_mask = USN_REASON_FILE_DELETE | USN_REASON_RENAME_OLD_NAME
        read_buf = ctypes.create_string_buffer(65536)
        curr_usn = start_usn
        seen = 0

        while curr_usn < next_usn and seen < max_records:
            in_data = struct.pack("<qIIQQQ", curr_usn, reason_mask, 0, 0, 0, journal_id)
            b_ret = wintypes.DWORD(0)
            ok_r = kernel32.DeviceIoControl(
                handle, FSCTL_READ_USN_JOURNAL,
                in_data, len(in_data),
                read_buf, 65536,
                ctypes.byref(b_ret), None
            )
            if not ok_r or b_ret.value <= 8:
                break

            raw = read_buf.raw[:b_ret.value]
            next_chunk_usn = struct.unpack_from("<q", raw, 0)[0]
            if next_chunk_usn <= curr_usn:
                break
            curr_usn = next_chunk_usn

            off = 8
            while off + 60 <= len(raw):
                rec_len = struct.unpack_from("<I", raw, off)[0]
                if rec_len < 60 or off + rec_len > len(raw):
                    break
                major_ver = struct.unpack_from("<H", raw, off + 4)[0]
                if major_ver == 2:
                    f_ref = struct.unpack_from("<Q", raw, off + 8)[0] & 0x0000FFFFFFFFFFFF
                    p_ref = struct.unpack_from("<Q", raw, off + 16)[0] & 0x0000FFFFFFFFFFFF
                    ts_ft = struct.unpack_from("<Q", raw, off + 32)[0]
                    reason = struct.unpack_from("<I", raw, off + 40)[0]
                    file_attrs = struct.unpack_from("<I", raw, off + 52)[0]
                    fn_len, fn_off = struct.unpack_from("<HH", raw, off + 56)
                    if fn_len > 0 and off + fn_off + fn_len <= off + rec_len:
                        fname = raw[off + fn_off:off + fn_off + fn_len].decode("utf-16le", errors="ignore")
                        if fname and not fname.startswith("$"):
                            discovered[f_ref] = {
                                "name": fname,
                                "parent_ref": p_ref,
                                "mtime_ft": ts_ft,
                                "reason": reason,
                                "is_dir": bool(file_attrs & 0x10),
                            }
                            seen += 1
                off += rec_len
    except Exception:
        pass
    return discovered


def recover_from_ntfs_runs(drive_letter: str,
                           data_runs: List[Tuple[int, int]],
                           bytes_per_cluster: int,
                           real_size: int,
                           dest_path: str) -> Tuple[bool, str]:
    """
    Forensically extract a deleted file directly from raw NTFS clusters using its Data Runs!
    """
    handle = open_raw_volume(drive_letter)
    if not handle:
        return False, "Administrator privileges required to read raw NTFS clusters."

    try:
        remaining = real_size if real_size > 0 else sum(cnt * bytes_per_cluster for _, cnt in data_runs)
        max_chunk = 1024 * 1024  # 1 MB aligned chunks

        with open(dest_path, "wb") as f_out:
            for lcn, cluster_count in data_runs:
                if remaining <= 0:
                    break
                run_bytes = cluster_count * bytes_per_cluster
                to_process = min(remaining, run_bytes)

                if lcn == -1:
                    # Sparse zero run
                    while to_process > 0:
                        step = min(to_process, max_chunk)
                        f_out.write(b"\x00" * step)
                        to_process -= step
                        remaining -= step
                    continue

                byte_off = lcn * bytes_per_cluster
                while to_process > 0:
                    # Must read sector/cluster-aligned length from raw volume
                    step = min(to_process, max_chunk)
                    aligned_step = ((step + bytes_per_cluster - 1) // bytes_per_cluster) * bytes_per_cluster
                    chunk = read_volume_at(handle, byte_off, aligned_step)
                    if not chunk:
                        break
                    f_out.write(chunk[:step])
                    byte_off += aligned_step
                    to_process -= step
                    remaining -= step

        return True, dest_path
    except Exception as e:
        return False, f"NTFS cluster extraction error: {e}"
    finally:
        kernel32.CloseHandle(handle)


def read_bytes_from_ntfs_runs(drive_letter: str,
                              data_runs: List[Tuple[int, int]],
                              bytes_per_cluster: int,
                              real_size: int,
                              max_bytes: int = 12 * 1024 * 1024) -> bytes:
    """
    Read up to max_bytes directly into memory from raw NTFS Data Runs
    for instant zero-write Live Preview and Hex Inspection of deleted files!
    """
    if not data_runs:
        return b""
    handle = open_raw_volume(drive_letter)
    if not handle:
        return b""

    out = bytearray()
    try:
        total_target = real_size if real_size > 0 else sum(cnt * bytes_per_cluster for _, cnt in data_runs)
        remaining = min(total_target, max_bytes)
        max_chunk = 512 * 1024

        for lcn, cluster_count in data_runs:
            if remaining <= 0:
                break
            run_bytes = cluster_count * bytes_per_cluster
            to_process = min(remaining, run_bytes)

            if lcn == -1:
                out.extend(b"\x00" * to_process)
                remaining -= to_process
                continue

            byte_off = lcn * bytes_per_cluster
            while to_process > 0:
                step = min(to_process, max_chunk)
                aligned_step = ((step + bytes_per_cluster - 1) // bytes_per_cluster) * bytes_per_cluster
                chunk = read_volume_at(handle, byte_off, aligned_step)
                if not chunk:
                    break
                out.extend(chunk[:step])
                byte_off += aligned_step
                to_process -= step
                remaining -= step
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(handle)
    return bytes(out)


class NTFSMFTScanner:
    """
    Full-speed EaseUS-grade NTFS Master File Table ($MFT) + USN Journal Scanner.
    Reconstructs Deleted, Cut/Moved, Existing, and Orphaned directory hierarchies across the entire NTFS volume!
    """

    def __init__(self,
                 target_path: str,
                 selected_categories: Optional[List[str]] = None):
        self.target_path = os.path.normpath(target_path)
        self.drive_letter = os.path.splitdrive(os.path.abspath(self.target_path))[0].upper() or "C:"
        self.drive_root = self.drive_letter + "\\"
        self.selected_categories = set(selected_categories) if selected_categories else set(ALL_CATEGORIES)
        self.is_running = False
        self.is_paused = False
        self.bytes_per_cluster = 4096

    def stop(self):
        self.is_running = False
        self.is_paused = False

    def _wait_if_paused(self):
        while self.is_paused and self.is_running:
            time.sleep(0.08)

    def scan(self,
             progress_callback: Optional[Callable[[int, str, int, float], None]] = None,
             live_batch_callback: Optional[Callable[[List], None]] = None) -> Tuple[bool, List]:
        """
        Execute direct NTFS $MFT + USN Journal forensic scan.
        Returns (succeeded_raw_mft: bool, List[RecoverableFile]).
        If Administrator privileges are missing, returns (False, []) so caller falls back cleanly.
        """
        from engine.undelete_engine import RecoverableFile

        self.is_running = True
        self.is_paused = False

        handle = open_raw_volume(self.drive_letter)
        if not handle:
            self.is_running = False
            return False, []

        try:
            geom = parse_ntfs_boot_sector(handle)
            if not geom:
                self.is_running = False
                return False, []

            bpc = geom["bytes_per_cluster"]
            bps = geom["bytes_per_sector"]
            rec_sz = geom["record_size"]
            mft_start_byte = geom["mft_start_lcn"] * bpc
            self.bytes_per_cluster = bpc

            if progress_callback:
                progress_callback(2, f"Reading NTFS $MFT geometry ({self.drive_letter})...", 0, 0.0)

            # 1. Read Record #0 ($MFT) to discover ALL fragmented $MFT cluster runs!
            rec0_bytes = read_volume_at(handle, mft_start_byte, rec_sz)
            rec0 = parse_mft_record_minimal(rec0_bytes, rec_sz, bps, 0)
            if not rec0 or not rec0["data_runs"]:
                # Fallback single contiguous extent estimate
                mft_runs = [(geom["mft_start_lcn"], 4096)]
                total_mft_bytes = 4096 * bpc
            else:
                mft_runs = rec0["data_runs"]
                total_mft_bytes = rec0["size"] if rec0["size"] > 0 else sum(c * bpc for _, c in mft_runs)

            total_records_est = max(1, total_mft_bytes // rec_sz)

            # 2. Query USN Change Journal for Cut/Moved-on-same-drive folders & recently deleted items!
            if progress_callback:
                progress_callback(4, f"Analyzing NTFS $UsnJrnl (Detecting Cut/Moved & Deleted folders)...", 0, 0.0)
            usn_events = query_usn_journal_deleted_and_moved(handle)

            # 3. Stream entire $MFT in 4 MB chunks
            dir_map: Dict[int, Tuple[str, int, bool]] = {5: ("", 5, True)}
            raw_files: List[Dict] = []

            chunk_bytes = 4 * 1024 * 1024  # 4 MB per Win32 ReadFile call
            # Align chunk_bytes to multiple of both bpc and rec_sz
            chunk_bytes = (chunk_bytes // bpc) * bpc

            bytes_scanned = 0
            rec_index = 0
            t_start = time.time()
            last_report_t = t_start

            for run_lcn, run_clusters in mft_runs:
                if not self.is_running:
                    break
                if run_lcn < 0:
                    rec_index += (run_clusters * bpc) // rec_sz
                    continue

                run_total_bytes = run_clusters * bpc
                run_off = 0

                while run_off < run_total_bytes and self.is_running:
                    self._wait_if_paused()
                    if not self.is_running:
                        break

                    to_read = min(chunk_bytes, run_total_bytes - run_off)
                    disk_off = run_lcn * bpc + run_off
                    buf = read_volume_at(handle, disk_off, to_read)
                    if not buf:
                        break

                    n_recs = len(buf) // rec_sz
                    for i in range(n_recs):
                        if (i & 0x3FF) == 0:  # Check pause/stop every 1024 records
                            self._wait_if_paused()
                            if not self.is_running:
                                break

                        r_start = i * rec_sz
                        if buf[r_start:r_start + 4] != b"FILE":
                            rec_index += 1
                            continue

                        parsed = parse_mft_record_minimal(buf[r_start:r_start + rec_sz], rec_sz, bps, rec_index)
                        rec_index += 1
                        if not parsed:
                            continue

                        fname = parsed["name"]
                        if fname.startswith("$") or fname in (".", ".."):
                            continue

                        if parsed["is_dir"]:
                            dir_map[parsed["rec_num"]] = (fname, parsed["parent_ref"], parsed["is_in_use"])
                        else:
                            raw_files.append(parsed)

                    run_off += len(buf)
                    bytes_scanned += len(buf)

                    now = time.time()
                    if progress_callback and (now - last_report_t >= 0.25):
                        elapsed = max(0.05, now - t_start)
                        speed_mb = (bytes_scanned / (1024 * 1024)) / elapsed
                        pct = min(82, 5 + int((rec_index / total_records_est) * 77))
                        sample_name = raw_files[-1]["name"] if raw_files else f"MFT Record #{rec_index:,}"
                        progress_callback(pct, f"$MFT [{rec_index:,}/{total_records_est:,}] — {sample_name}", len(raw_files), speed_mb)
                        last_report_t = now

            if not self.is_running and not raw_files:
                return True, []

            # 4. Also merge USN-deleted directory names into dir_map if their MFT dir record was overwritten!
            for u_ref, u_info in usn_events.items():
                if u_info["is_dir"] and u_ref not in dir_map:
                    dir_map[u_ref] = (u_info["name"], u_info["parent_ref"], False)

            # 5. Resolve directory full paths with memoization (blazing fast O(1) amortized!)
            if progress_callback:
                progress_callback(85, "Reconstructing full NTFS directory hierarchy...", len(raw_files), 0.0)

            path_cache: Dict[int, Tuple[str, bool]] = {5: (self.drive_root.rstrip("\\"), True)}

            def resolve_dir_path(d_ref: int) -> Tuple[str, bool]:
                """Returns (full_dir_path, is_complete_chain_to_root)."""
                if d_ref in path_cache:
                    return path_cache[d_ref]
                chain = []
                visited = set()
                curr = d_ref
                complete = False
                while curr not in path_cache:
                    if curr in visited or len(chain) > 48:
                        break
                    visited.add(curr)
                    entry = dir_map.get(curr)
                    if not entry:
                        break
                    d_name, p_ref, _ = entry
                    chain.append((curr, d_name))
                    if p_ref == curr:
                        break
                    curr = p_ref

                if curr in path_cache:
                    base_path, base_ok = path_cache[curr]
                    complete = base_ok
                else:
                    base_path = ""
                    complete = False

                acc = base_path
                for c_ref, c_name in reversed(chain):
                    acc = (acc + "\\" + c_name) if acc else c_name
                    path_cache[c_ref] = (acc, complete)

                return path_cache.get(d_ref, ("", False))

            # Identify target folder MFT record number if user scanned a specific folder (like Desktop!)
            norm_target_low = self.target_path.rstrip("\\").lower()
            is_full_drive_scan = (len(norm_target_low) <= 2 and norm_target_low.endswith(":"))

            # Pre-resolve directories & identify folders that were CUT/MOVED OUT of target_path via USN Journal!
            moved_dir_refs: Set[int] = set()
            moved_file_refs: Dict[int, str] = {}
            if not is_full_drive_scan:
                for u_ref, u_info in usn_events.items():
                    if u_info["reason"] & (USN_REASON_RENAME_OLD_NAME | USN_REASON_FILE_DELETE):
                        p_path, p_ok = resolve_dir_path(u_info["parent_ref"])
                        if p_ok and p_path.lower().startswith(norm_target_low):
                            old_full = p_path + "\\" + u_info["name"]
                            if u_info["is_dir"]:
                                moved_dir_refs.add(u_ref)
                            else:
                                moved_file_refs[u_ref] = old_full

            # Check if a dir descends from any moved_dir_refs
            def is_inside_moved_dir(d_ref: int) -> Optional[str]:
                if not moved_dir_refs:
                    return None
                curr = d_ref
                depth = 0
                sub_parts = []
                while curr != 5 and depth < 32:
                    if curr in moved_dir_refs:
                        u_dir = usn_events.get(curr)
                        orig_parent, _ = resolve_dir_path(u_dir["parent_ref"])
                        base_old = orig_parent + "\\" + u_dir["name"]
                        if sub_parts:
                            return base_old + "\\" + "\\".join(reversed(sub_parts))
                        return base_old
                    ent = dir_map.get(curr)
                    if not ent:
                        break
                    sub_parts.append(ent[0])
                    if ent[1] == curr:
                        break
                    curr = ent[1]
                    depth += 1
                return None

            # 6. Build RecoverableFile objects grouped in standard commercial recovery buckets!
            results: List[RecoverableFile] = []
            # Categorization buckets (EaseUS / Disk Drill standard):
            # - Target Folder Deleted / Cut / Existing (prioritized at top!)
            # - Deleted Files (volume-wide)
            # - Existing Files (Windows 11 C:)
            # - Lost / Orphaned Files
            target_items: List[RecoverableFile] = []
            deleted_items: List[RecoverableFile] = []
            orphaned_items: List[RecoverableFile] = []
            existing_items: List[RecoverableFile] = []

            for idx_f, rf in enumerate(raw_files):
                if (idx_f & 0xFFF) == 0:
                    self._wait_if_paused()
                    if not self.is_running:
                        break

                fname = rf["name"]
                ext = os.path.splitext(fname)[1].lower().lstrip(".")
                cat = get_category_for_ext(ext)
                if self.selected_categories and cat not in self.selected_categories and cat != "Other":
                    continue

                p_path, chain_ok = resolve_dir_path(rf["parent_ref"])
                is_in_use = rf["is_in_use"]
                rec_num = rf["rec_num"]
                sz = rf["size"]
                dt = filetime_to_datetime(rf["mtime_ft"])

                # Detect if this file was CUT/MOVED from the target folder (e.g. Desktop!)
                moved_orig_path = moved_file_refs.get(rec_num)
                if not moved_orig_path and moved_dir_refs:
                    moved_dir_old = is_inside_moved_dir(rf["parent_ref"])
                    if moved_dir_old:
                        moved_orig_path = moved_dir_old + "\\" + fname

                if chain_ok and p_path:
                    full_path = p_path + "\\" + fname
                elif p_path:
                    full_path = self.drive_root + "Orphaned\\" + p_path + "\\" + fname
                else:
                    full_path = self.drive_root + "Orphaned\\" + fname

                # Determine recovery source handle & quality
                src_handle = None
                if is_in_use and chain_ok:
                    src_handle = full_path
                    qual = "Excellent"
                elif rf["resident_data"] is not None:
                    qual = "Excellent"
                elif rf["data_runs"]:
                    src_handle = f"\\\\.\\{self.drive_letter}"
                    qual = "Good" if sz > 0 else "Poor"
                else:
                    qual = "Poor"

                # Classify into standard commercial recovery root bucket!
                if moved_orig_path:
                    # Cut/Moved out of Target Folder (Desktop) -> show clearly under Target Deleted/Cut!
                    rel_after_target = os.path.relpath(os.path.dirname(moved_orig_path), self.target_path)
                    rel_clean = "" if rel_after_target == "." else rel_after_target
                    bucket_rel = os.path.join("Deleted & Cut Files", os.path.basename(self.target_path) or "Target", rel_clean).rstrip("\\")
                    item = RecoverableFile(
                        name=fname,
                        original_path=moved_orig_path,
                        size_bytes=sz,
                        ext=ext,
                        category=cat,
                        deleted_time=dt,
                        quality="Excellent",
                        source_type="Cut / Moved (USN Journal)",
                        source_handle=full_path if is_in_use else src_handle,
                    )
                    item.folder_rel = bucket_rel.lower()
                    item.display_folder_rel = bucket_rel
                    item.is_deleted = True
                    item.ntfs_data_runs = rf["data_runs"]
                    item.ntfs_bpc = bpc
                    item.raw_data_bytes = rf["resident_data"]
                    target_items.append(item)
                elif not is_in_use:
                    # Truly DELETED MFT record (Shift+Delete, Recycle Bin, Cut to another drive!)
                    if not is_full_drive_scan and chain_ok and full_path.lower().startswith(norm_target_low + "\\"):
                        rel_after = os.path.relpath(os.path.dirname(full_path), self.target_path)
                        rel_clean = "" if rel_after == "." else rel_after
                        bucket_rel = os.path.join("Deleted & Cut Files", os.path.basename(self.target_path) or "Target", rel_clean).rstrip("\\")
                        dest_list = target_items
                    elif chain_ok:
                        rel_vol = os.path.dirname(full_path)[len(self.drive_root):]
                        bucket_rel = os.path.join("Deleted Files (" + self.drive_letter + ")", rel_vol).rstrip("\\")
                        dest_list = deleted_items
                    else:
                        bucket_rel = os.path.join("Lost & Orphaned Files", cat)
                        dest_list = orphaned_items

                    item = RecoverableFile(
                        name=fname,
                        original_path=full_path,
                        size_bytes=sz,
                        ext=ext,
                        category=cat,
                        deleted_time=dt,
                        quality=qual,
                        source_type="Deleted ($MFT)",
                        source_handle=src_handle,
                    )
                    item.folder_rel = bucket_rel.lower()
                    item.display_folder_rel = bucket_rel
                    item.is_deleted = True
                    item.ntfs_data_runs = rf["data_runs"]
                    item.ntfs_bpc = bpc
                    item.raw_data_bytes = rf["resident_data"]
                    dest_list.append(item)
                else:
                    # Existing active file on the partition
                    if not is_full_drive_scan and chain_ok and full_path.lower().startswith(norm_target_low + "\\"):
                        rel_after = os.path.relpath(os.path.dirname(full_path), self.target_path)
                        rel_clean = "" if rel_after == "." else rel_after
                        bucket_rel = os.path.join(os.path.basename(self.target_path) or "Target", rel_clean).rstrip("\\")
                        item = RecoverableFile(
                            name=fname,
                            original_path=full_path,
                            size_bytes=sz,
                            ext=ext,
                            category=cat,
                            deleted_time=dt,
                            quality="Excellent",
                            source_type="Existing",
                            source_handle=full_path,
                        )
                        item.folder_rel = bucket_rel.lower()
                        item.display_folder_rel = bucket_rel
                        item.is_deleted = False
                        target_items.append(item)
                    elif chain_ok:
                        # Include partition existing files (capped cleanly for instant GUI responsiveness while showing full partition!)
                        rel_vol = os.path.dirname(full_path)[len(self.drive_root):]
                        bucket_rel = os.path.join(f"Partition ({self.drive_letter})", rel_vol).rstrip("\\")
                        item = RecoverableFile(
                            name=fname,
                            original_path=full_path,
                            size_bytes=sz,
                            ext=ext,
                            category=cat,
                            deleted_time=dt,
                            quality="Excellent",
                            source_type="Partition Existing",
                            source_handle=full_path,
                        )
                        item.folder_rel = bucket_rel.lower()
                        item.display_folder_rel = bucket_rel
                        item.is_deleted = False
                        existing_items.append(item)

            # Order results so Deleted/Cut & Target items ALWAYS appear first (instant visibility!)
            results = target_items + deleted_items + orphaned_items + existing_items

            if progress_callback:
                elapsed = max(0.05, time.time() - t_start)
                speed_mb = (bytes_scanned / (1024 * 1024)) / elapsed
                progress_callback(100, f"NTFS $MFT Scan Complete: {len(results):,} files ({len(deleted_items) + len(orphaned_items):,} deleted/lost).", len(results), speed_mb)

            self.is_running = False
            return True, results

        except Exception as e:
            print(f"[NTFSMFTScanner] Error: {e}")
            self.is_running = False
            return False, []
        finally:
            kernel32.CloseHandle(handle)
