"""
Insight Data Recovery Studio Pro - Commercial Scan & Results View v5.0
Zero-Freeze architecture, full Light/Dark theme parity, Arabic RTL / English LTR support,
Advanced Filter Dialog, Dual-Tab Live Preview + Hex Byte Inspector, and Safe Drive Guard.
"""
import os
import io
import zipfile
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter, QTreeWidget,
    QTreeWidgetItem, QLineEdit, QFileDialog, QMessageBox, QTabWidget,
    QFrame, QAbstractItemView, QDialog, QApplication, QTextEdit,
    QComboBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QRectF, QPointF
from PyQt6.QtGui import (
    QPixmap, QColor, QFont, QImage, QIcon,
    QPainter, QPen, QBrush, QConicalGradient, QPainterPath
)

from engine.undelete_engine import RecoverableFile, restore_file, read_recoverable_file_bytes
from engine.disk_scanner import enumerate_logical_drives, get_system_drive_letter
from repair.video_repair import resolve_ffmpeg_path
from ui.theme import STRINGS, get_asset_path, get_ui_icon, get_category_icon, get_ext_icon


def load_qpixmap_from_bytes(raw: bytes) -> Optional[QPixmap]:
    """
    Robust multi-engine image decoder (Qt native + Pillow fallback with truncated-image support).
    Decodes .ico, .webp, .tif, .tiff, .bmp, .png, .jpg, .gif — even from deleted/partial NTFS clusters!
    """
    if not raw or len(raw) < 12:
        return None
    # 1. Try Pillow first for maximum format coverage (.ico, .webp, .tiff, truncated JPEGs)
    try:
        from PIL import Image, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGBA")
            w, h = im.size
            if w > 0 and h > 0:
                buf = im.tobytes("raw", "RGBA")
                qimg = QImage(buf, w, h, w * 4, QImage.Format.Format_RGBA8888)
                pix = QPixmap.fromImage(qimg.copy())
                if not pix.isNull():
                    return pix
    except Exception:
        pass

    # 2. Fallback to Qt native QPixmap.loadFromData
    try:
        pix = QPixmap()
        if pix.loadFromData(raw) and not pix.isNull():
            return pix
    except Exception:
        pass
    return None


def decode_text_bytes(raw: bytes, max_chars: int = 25000) -> str:
    """Decode raw bytes cleanly supporting UTF-8, UTF-16LE/BE BOM, and Arabic/Latin fallback."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")[:max_chars]
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", errors="ignore")[:max_chars]
    try:
        return raw.decode("utf-8")[:max_chars]
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")[:max_chars]


def parse_windows_lnk_bytes(raw: bytes) -> Optional[dict]:
    """Parse Windows Shell Link (.lnk) binary header & extract readable UTF-16/ASCII target paths."""
    if not raw or len(raw) < 76 or raw[:4] != b"\x4C\x00\x00\x00":
        return None
    import re
    import struct
    file_size = struct.unpack_from("<I", raw, 52)[0]
    # Extract UTF-16LE and ASCII drive/UNC paths cleanly from the binary LinkInfo/StringData sections
    u16_text = raw.decode("utf-16le", errors="ignore")
    asc_text = raw.decode("latin-1", errors="ignore")
    path_pat = re.compile(r"[A-Za-z]:\\[^\x00-\x1f\"<>|*?\r\n]{3,260}")
    paths = []
    for m in path_pat.findall(u16_text) + path_pat.findall(asc_text):
        clean_m = m.strip()
        if clean_m and clean_m not in paths:
            paths.append(clean_m)
    return {
        "target_paths": paths,
        "recorded_target_size": file_size,
    }


class ScanningSpinnerWidget(QWidget):
    """
    Commercial animated circular radar/spinner widget for live scanning feedback.
    - 'scanning': Smoothly rotating blue gradient ring around a crisp lightning bolt (~33 FPS).
    - 'paused':   Static amber ring with pause bars (timer stopped).
    - 'completed': Vibrant emerald green circle with white checkmark (timer stopped).
    - 'stopped':  Crisp red ring with stop square (timer stopped).
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self._angle = 0
        self._state = "scanning"
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)

    def _tick(self):
        self._angle = (self._angle + 10) % 360
        self.update()

    def start_scanning(self):
        self._state = "scanning"
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def set_paused(self, paused: bool):
        if paused:
            self._state = "paused"
            self._timer.stop()
        else:
            self._state = "scanning"
            if not self._timer.isActive():
                self._timer.start()
        self.update()

    def set_completed(self):
        self._state = "completed"
        self._timer.stop()
        self.update()

    def set_stopped(self):
        self._state = "stopped"
        self._timer.stop()
        self.update()

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_animating(self) -> bool:
        return self._timer.isActive()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        if self._state == "scanning" and not self._timer.isActive():
            self._timer.start()
        super().showEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        pad = 3.5
        ring_rect = QRectF(pad, pad, w - 2 * pad, h - 2 * pad)

        if self._state == "scanning":
            # Soft glowing inner disk
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(13, 110, 253, 24)))
            p.drawEllipse(ring_rect)

            # Subtle circular track
            track_pen = QPen(QColor(13, 110, 253, 45), 3.0)
            p.setPen(track_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(ring_rect)

            # Rotating gradient arc (270 degrees smooth sweep)
            grad = QConicalGradient(QPointF(cx, cy), -self._angle)
            grad.setColorAt(0.00, QColor(13, 110, 253, 255))
            grad.setColorAt(0.35, QColor(56, 189, 248, 220))
            grad.setColorAt(0.75, QColor(13, 110, 253, 30))
            grad.setColorAt(1.00, QColor(13, 110, 253, 0))

            arc_pen = QPen(QBrush(grad), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(arc_pen)
            # Qt drawArc uses 1/16th of a degree, counterclockwise from 3 o'clock
            start_16 = int((-self._angle) * 16)
            span_16 = int(265 * 16)
            p.drawArc(ring_rect, start_16, span_16)

            # Center lightning bolt icon
            bolt = QPainterPath()
            bolt.moveTo(cx + 1.2, cy - 7.5)
            bolt.lineTo(cx - 4.8, cy + 0.8)
            bolt.lineTo(cx - 0.3, cy + 0.8)
            bolt.lineTo(cx - 1.6, cy + 7.5)
            bolt.lineTo(cx + 4.8, cy - 1.0)
            bolt.lineTo(cx + 0.3, cy - 1.0)
            bolt.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#0D6EFD")))
            p.drawPath(bolt)

        elif self._state == "paused":
            p.setBrush(QBrush(QColor(245, 158, 11, 28)))
            p.setPen(QPen(QColor("#F59E0B"), 2.6))
            p.drawEllipse(ring_rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#D97706")))
            p.drawRoundedRect(QRectF(cx - 4.6, cy - 5.5, 3.2, 11.0), 1.2, 1.2)
            p.drawRoundedRect(QRectF(cx + 1.4, cy - 5.5, 3.2, 11.0), 1.2, 1.2)

        elif self._state == "completed":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#10B981")))
            p.drawEllipse(ring_rect)
            chk = QPainterPath()
            chk.moveTo(cx - 6.2, cy + 0.4)
            chk.lineTo(cx - 1.8, cy + 4.8)
            chk.lineTo(cx + 6.6, cy - 4.6)
            p.setPen(QPen(QColor("#FFFFFF"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(chk)

        else:  # stopped
            p.setBrush(QBrush(QColor(239, 68, 68, 28)))
            p.setPen(QPen(QColor("#EF4444"), 2.6))
            p.drawEllipse(ring_rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor("#DC2626")))
            p.drawRoundedRect(QRectF(cx - 4.5, cy - 4.5, 9.0, 9.0), 1.8, 1.8)

        p.end()


class SizeTableWidgetItem(QTableWidgetItem):
    """Custom QTableWidgetItem that sorts numerically by raw byte size."""
    def __lt__(self, other):
        v1 = self.data(Qt.ItemDataRole.UserRole)
        v2 = other.data(Qt.ItemDataRole.UserRole) if other else 0
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return v1 < v2
        return super().__lt__(other)


class AdvancedFilterDialog(QDialog):
    """Commercial EaseUS-style Advanced Filter Popover (Size, Date, Integrity)."""
    def __init__(self, lang: str, current_filters: dict, parent=None):
        super().__init__(parent)
        self.lang = lang
        self.filters = dict(current_filters)
        self.setWindowTitle("تصفية متقدمة للنتائج" if lang == "ar" else "Advanced Results Filter")
        self.setFixedSize(360, 260)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)

        l = QVBoxLayout(self)
        l.setContentsMargins(18, 16, 18, 16)
        l.setSpacing(10)

        # File Size
        l.addWidget(QLabel("حجم الملف:" if lang == "ar" else "File Size:"))
        self.cmb_size = QComboBox()
        size_opts = [
            ("all", "الكل (جميع الأحجام)" if lang == "ar" else "Any Size"),
            ("small", "صغير (< 1 MB)" if lang == "ar" else "Small (< 1 MB)"),
            ("medium", "متوسط (1 MB - 100 MB)" if lang == "ar" else "Medium (1 MB - 100 MB)"),
            ("large", "كبير (> 100 MB)" if lang == "ar" else "Large (> 100 MB)"),
        ]
        for code, txt in size_opts:
            self.cmb_size.addItem(txt, code)
        idx_s = self.cmb_size.findData(self.filters.get("size", "all"))
        if idx_s >= 0:
            self.cmb_size.setCurrentIndex(idx_s)
        l.addWidget(self.cmb_size)

        # Date Modified
        l.addWidget(QLabel("تاريخ التعديل / الحذف:" if lang == "ar" else "Date Modified:"))
        self.cmb_date = QComboBox()
        date_opts = [
            ("all", "الكل (أي تاريخ)" if lang == "ar" else "Any Date"),
            ("today", "اليوم (آخر 24 ساعة)" if lang == "ar" else "Today (Last 24h)"),
            ("week", "آخر 7 أيام" if lang == "ar" else "Last 7 Days"),
            ("month", "آخر 30 يوماً" if lang == "ar" else "Last 30 Days"),
            ("year", "آخر سنة" if lang == "ar" else "Last Year"),
        ]
        for code, txt in date_opts:
            self.cmb_date.addItem(txt, code)
        idx_d = self.cmb_date.findData(self.filters.get("date", "all"))
        if idx_d >= 0:
            self.cmb_date.setCurrentIndex(idx_d)
        l.addWidget(self.cmb_date)

        # Integrity Status
        l.addWidget(QLabel("حالة السلامة (Integrity):" if lang == "ar" else "File Integrity:"))
        self.cmb_quality = QComboBox()
        qual_opts = [
            ("all", "الكل" if lang == "ar" else "Any Integrity"),
            ("Excellent", "ممتاز (Excellent)" if lang == "ar" else "Excellent"),
            ("Good", "جيد (Good)" if lang == "ar" else "Good"),
            ("Poor", "ضعيف (Poor)" if lang == "ar" else "Poor"),
        ]
        for code, txt in qual_opts:
            self.cmb_quality.addItem(txt, code)
        idx_q = self.cmb_quality.findData(self.filters.get("quality", "all"))
        if idx_q >= 0:
            self.cmb_quality.setCurrentIndex(idx_q)
        l.addWidget(self.cmb_quality)

        l.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_reset = QPushButton("إعادة ضبط" if lang == "ar" else "Reset")
        btn_reset.setObjectName("SecondaryActionBtn")
        btn_reset.clicked.connect(self.reset_filters)
        btn_row.addWidget(btn_reset)

        btn_row.addStretch()

        btn_apply = QPushButton("تطبيق التصفية" if lang == "ar" else "Apply Filter")
        btn_apply.setObjectName("PrimaryActionBtn")
        btn_apply.clicked.connect(self.apply_and_close)
        btn_row.addWidget(btn_apply)
        l.addLayout(btn_row)

    def reset_filters(self):
        self.cmb_size.setCurrentIndex(0)
        self.cmb_date.setCurrentIndex(0)
        self.cmb_quality.setCurrentIndex(0)
        self.filters = {"size": "all", "date": "all", "quality": "all"}
        self.accept()

    def apply_and_close(self):
        self.filters = {
            "size": self.cmb_size.currentData(),
            "date": self.cmb_date.currentData(),
            "quality": self.cmb_quality.currentData(),
        }
        self.accept()


class PreviewHexDialog(QDialog):
    """
    Commercial Dual-Tab Live Content Preview + Formatted Hex Byte Inspector.
    Reads directly from live files, Recycle Bin $R streams, resident $MFT bytes,
    AND deleted raw NTFS Data Runs — supporting Images (incl. ICO/WebP/TIFF), PDF,
    DOCX, XLSX, PPTX, ZIP Archives, Video Frames (FFmpeg), and Text/Code files!
    """
    def __init__(self, f: RecoverableFile, lang: str = "en", parent=None):
        super().__init__(parent)
        self.file_obj = f
        self.lang = lang
        self.strings = STRINGS[lang]
        self.setWindowTitle(f"{self.strings['tab_preview']} — {(f.name[:48] + '...') if len(f.name) > 51 else f.name}")
        self.resize(760, 540)
        self.setMinimumSize(640, 440)
        self.setMaximumSize(960, 720)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)

        # Read real file bytes ONCE across all 5 recovery tiers (up to 16 MB for preview)
        self._raw_bytes, self._source_label = read_recoverable_file_bytes(f, max_bytes=16 * 1024 * 1024)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header meta bar (strictly bounded so long Arabic filenames never stretch dialog off-screen!)
        meta_card = QFrame()
        meta_card.setObjectName("InsetBox")
        meta_l = QHBoxLayout(meta_card)
        meta_l.setContentsMargins(12, 8, 12, 8)
        disp_name = f.name if len(f.name) <= 44 else (f.name[:41] + "...")
        src_tag = f"  •  {self._source_label}" if self._source_label else ""
        lbl_name = QLabel(f"📄 {disp_name}  •  {f.size_display}  •  .{f.ext}  •  {f.quality}{src_tag}")
        lbl_name.setToolTip(f.original_path or f.name)
        lbl_name.setObjectName("CardTitle")
        lbl_name.setWordWrap(True)
        meta_l.addWidget(lbl_name, 1)
        layout.addWidget(meta_card)

        # Tabs
        tabs = QTabWidget()

        # Tab 1: Live Preview
        tab_prev = QWidget()
        prev_l = QVBoxLayout(tab_prev)
        prev_l.setContentsMargins(10, 10, 10, 10)
        self._build_preview_content(prev_l, f, self._raw_bytes)
        tabs.addTab(tab_prev, "👁️  " + self.strings["tab_preview"])

        # Tab 2: Hex Byte Inspector
        tab_hex = QWidget()
        hex_l = QVBoxLayout(tab_hex)
        hex_l.setContentsMargins(10, 10, 10, 10)
        hex_edit = QTextEdit()
        hex_edit.setReadOnly(True)
        hex_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        hex_edit.setFont(QFont("Consolas", 10))
        hex_edit.setPlainText(self._build_hex_dump(f, self._raw_bytes, max_bytes=4096))
        hex_l.addWidget(hex_edit)
        tabs.addTab(tab_hex, "🔢  " + self.strings["tab_hex"])

        layout.addWidget(tabs, 1)

        # Bottom Close
        bot = QHBoxLayout()
        bot.addStretch()
        btn_close = QPushButton("إغلاق" if lang == "ar" else "Close")
        btn_close.setObjectName("PrimaryActionBtn")
        btn_close.clicked.connect(self.accept)
        bot.addWidget(btn_close)
        layout.addLayout(bot)

    def _build_preview_content(self, layout: QVBoxLayout, f: RecoverableFile, raw: bytes):
        ext = (f.ext or "").lower()
        has_bytes = bool(raw)

        # 1. Images (PNG, JPG, JPEG, BMP, ICO, WEBP, GIF, TIF, TIFF) — Qt + Pillow (supports deleted NTFS clusters!)
        if has_bytes and ext in {"png", "jpg", "jpeg", "bmp", "ico", "webp", "gif", "tif", "tiff"}:
            pix = load_qpixmap_from_bytes(raw)
            if pix and not pix.isNull():
                lbl = QLabel()
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setPixmap(pix.scaled(680, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                layout.addWidget(lbl, 1)
                dim = QLabel(f"Resolution: {pix.width()} × {pix.height()} px  •  Source: {self._source_label}")
                dim.setObjectName("MutedLabel")
                dim.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(dim)
                return

        # 2. PDF (renders Page 1 directly from memory — works even on deleted NTFS PDFs!)
        if has_bytes and ext == "pdf":
            try:
                import fitz
                doc = fitz.open(stream=raw, filetype="pdf")
                if doc.page_count > 0:
                    pg_cnt = doc.page_count
                    page = doc.load_page(0)
                    pm = page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25))
                    qimg = QImage(pm.samples, pm.width, pm.height, pm.stride, QImage.Format.Format_RGB888)
                    pix = QPixmap.fromImage(qimg.copy())
                    doc.close()
                    lbl = QLabel()
                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl.setPixmap(pix.scaled(680, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    layout.addWidget(lbl, 1)
                    lbl_pg = QLabel(f"PDF Document — {pg_cnt} page(s) (Showing Page 1)  •  Source: {self._source_label}")
                    lbl_pg.setObjectName("MutedLabel")
                    lbl_pg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(lbl_pg)
                    return
                doc.close()
            except Exception:
                pass

        # 3. Microsoft Word (.docx) — direct in-memory XML extraction
        if has_bytes and ext == "docx":
            try:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    if "word/document.xml" in zf.namelist():
                        root = ET.fromstring(zf.read("word/document.xml"))
                        paragraphs = []
                        for p_el in root.iter():
                            if p_el.tag.endswith("}p"):
                                p_txt = "".join(t.text for t in p_el.iter() if t.text and t.tag.endswith("}t"))
                                if p_txt.strip():
                                    paragraphs.append(p_txt)
                        txt = QTextEdit()
                        txt.setReadOnly(True)
                        txt.setPlainText("\n".join(paragraphs)[:25000] if paragraphs else "(Empty Word document)")
                        layout.addWidget(txt, 1)
                        return
            except Exception:
                pass

        # 4. Microsoft Excel (.xlsx) — direct in-memory sharedStrings + sheet1 preview
        if has_bytes and ext == "xlsx":
            try:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    names = zf.namelist()
                    shared = []
                    if "xl/sharedStrings.xml" in names:
                        s_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                        for si in s_root.iter():
                            if si.tag.endswith("}si"):
                                shared.append("".join(t.text for t in si.iter() if t.text and t.tag.endswith("}t")))
                    sheet_files = sorted([n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")])
                    lines = []
                    if sheet_files:
                        sh_root = ET.fromstring(zf.read(sheet_files[0]))
                        for row_el in sh_root.iter():
                            if row_el.tag.endswith("}row"):
                                row_vals = []
                                for c_el in row_el:
                                    if not c_el.tag.endswith("}c"):
                                        continue
                                    c_type = c_el.attrib.get("t", "")
                                    v_txt = ""
                                    for ch in c_el:
                                        if ch.tag.endswith("}v") and ch.text is not None:
                                            v_txt = ch.text
                                            break
                                    if c_type == "s" and v_txt.isdigit() and int(v_txt) < len(shared):
                                        v_txt = shared[int(v_txt)]
                                    if v_txt:
                                        row_vals.append(v_txt)
                                if row_vals:
                                    lines.append("  |  ".join(row_vals))
                                if len(lines) >= 200:
                                    break
                    if lines or shared:
                        txt = QTextEdit()
                        txt.setReadOnly(True)
                        txt.setFont(QFont("Consolas", 9))
                        header = f"=== Excel Workbook Preview ({len(sheet_files)} sheet(s)) ===\n\n"
                        txt.setPlainText(header + ("\n".join(lines) if lines else "\n".join(shared[:200])))
                        layout.addWidget(txt, 1)
                        return
            except Exception:
                pass

        # 5. Microsoft PowerPoint (.pptx) — direct in-memory slide text extraction
        if has_bytes and ext == "pptx":
            try:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    slides = sorted([n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
                    out_slides = []
                    for idx_s, s_name in enumerate(slides[:30], 1):
                        s_root = ET.fromstring(zf.read(s_name))
                        texts = [el.text for el in s_root.iter() if el.text and el.tag.endswith("}t")]
                        if texts:
                            out_slides.append(f"--- Slide {idx_s} ---\n" + " ".join(texts))
                    if out_slides:
                        txt = QTextEdit()
                        txt.setReadOnly(True)
                        txt.setPlainText("\n\n".join(out_slides)[:25000])
                        layout.addWidget(txt, 1)
                        return
            except Exception:
                pass

        # 6. ZIP / Archive Inspector (.zip, .jar, .apk, .epub)
        if has_bytes and ext in {"zip", "jar", "apk", "epub"}:
            try:
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    infos = zf.infolist()
                    lines = [f"Archive Contents ({len(infos):,} entries) — Source: {self._source_label}", "-" * 72]
                    for zi in infos[:300]:
                        sz_s = f"{zi.file_size:,} B" if zi.file_size < 1024 else f"{zi.file_size / 1024:.1f} KB"
                        lines.append(f"{sz_s:>12}   {zi.filename}")
                    if len(infos) > 300:
                        lines.append(f"\n... and {len(infos) - 300:,} more files ...")
                    txt = QTextEdit()
                    txt.setReadOnly(True)
                    txt.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                    txt.setFont(QFont("Consolas", 9))
                    txt.setPlainText("\n".join(lines))
                    layout.addWidget(txt, 1)
                    return
            except Exception:
                pass

        # 7. Video Frame Preview (MP4, MOV, MKV, AVI, WMV, FLV, WEBM) via bundled FFmpeg!
        if ext in {"mp4", "mov", "mkv", "avi", "wmv", "flv", "webm"}:
            ff_bin = resolve_ffmpeg_path()
            if ff_bin:
                tmp_vid = None
                try:
                    vid_src = None
                    if f.source_handle and not str(f.source_handle).startswith("\\\\.\\") and os.path.isfile(f.source_handle):
                        vid_src = f.source_handle
                    elif has_bytes:
                        fd, tmp_vid = tempfile.mkstemp(suffix=f".{ext}")
                        with os.fdopen(fd, "wb") as tf:
                            tf.write(raw)
                        vid_src = tmp_vid

                    if vid_src:
                        kwargs = {"stdout": subprocess.PIPE, "stderr": subprocess.DEVNULL, "timeout": 8}
                        if os.name == "nt":
                            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                        for seek_t in ("00:00:01", "00:00:00"):
                            proc = subprocess.run(
                                [ff_bin, "-ss", seek_t, "-i", vid_src, "-vframes", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                                **kwargs
                            )
                            if proc.returncode == 0 and proc.stdout and len(proc.stdout) > 128:
                                pix = load_qpixmap_from_bytes(proc.stdout)
                                if pix and not pix.isNull():
                                    lbl = QLabel()
                                    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                    lbl.setPixmap(pix.scaled(680, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                                    layout.addWidget(lbl, 1)
                                    dim = QLabel(f"🎬 Video Frame Preview ({pix.width()} × {pix.height()} px)  •  Source: {self._source_label}")
                                    dim.setObjectName("MutedLabel")
                                    dim.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                    layout.addWidget(dim)
                                    return
                except Exception:
                    pass
                finally:
                    if tmp_vid and os.path.exists(tmp_vid):
                        try:
                            os.remove(tmp_vid)
                        except Exception:
                            pass

        # 7b. Windows Shortcut (.lnk) Binary Parser
        if has_bytes and ext == "lnk":
            lnk_info = parse_windows_lnk_bytes(raw)
            if lnk_info:
                txt = QTextEdit()
                txt.setReadOnly(True)
                lines = [
                    "🔗 Windows Shortcut (.lnk) — Parsed Metadata",
                    f"Source: {self._source_label}  ({len(raw):,} bytes)",
                    "-" * 64,
                    f"Recorded Target File Size: {lnk_info['recorded_target_size']:,} bytes",
                    "",
                    "Linked Target Path(s):",
                ]
                if lnk_info["target_paths"]:
                    for tp in lnk_info["target_paths"]:
                        exists_tag = "  [Exists on Disk]" if os.path.exists(tp) else "  [Deleted / Moved]"
                        lines.append(f"  • {tp}{exists_tag}")
                else:
                    lines.append("  (Relative / Shell Namespace Shortcut)")
                lines.append("\nNote: A .lnk file is only a 1 KB Windows shortcut link, not the original document itself.")
                txt.setPlainText("\n".join(lines))
                layout.addWidget(txt, 1)
                return

        # 8. Plain Text / Source Code / Logs / Subtitles / Config (plus auto-detect printable text!)
        text_exts = {
            "txt", "py", "json", "xml", "ini", "cfg", "log", "md", "csv", "html", "htm",
            "css", "js", "ts", "java", "c", "cpp", "h", "bat", "ps1", "sql", "yaml", "yml",
            "crt", "srt", "vtt", "reg", "inf", "spec", "iss", "env", "conf", "properties", "sh"
        }
        is_printable_text = False
        if has_bytes and ext not in text_exts:
            sample = raw[:512]
            if b"\x00" not in sample:
                printable = sum(1 for b in sample if b in (9, 10, 13) or 32 <= b <= 126 or b >= 128)
                is_printable_text = (len(sample) > 0 and (printable / len(sample)) >= 0.90)

        if has_bytes and (ext in text_exts or is_printable_text):
            txt = QTextEdit()
            txt.setReadOnly(True)
            txt.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            txt.setFont(QFont("Consolas", 10))
            txt.setPlainText(decode_text_bytes(raw[:40000]))
            layout.addWidget(txt, 1)
            return

        # 9. Informative Binary / Overwritten Diagnostics
        if not has_bytes:
            diag_ar = (
                f"⚠️ تعذّر قراءة بيانات الملف (القطاعات محذوفة نهائياً أو أُعيدت الكتابة فوقها)\n\n"
                f"الاسم: {f.name}\nالحجم المسجل: {f.size_display} ({f.size_bytes:,} بايت)\n"
                f"النوع: {f.category} (.{f.ext})  •  السلامة: {f.quality}\nالمسار: {f.original_path}\n\n"
                f"ملاحظة: عندما تكون حالة السلامة (Poor) أو الملف ممسوحاً من سلة المحذوفات بدون قطاعات نشطة،\n"
                f"يكون نظام ويندوز قد أعاد استخدام مساحته على القرص."
            )
            diag_en = (
                f"⚠️ Unable to preview file content (clusters purged or overwritten by OS)\n\n"
                f"Name: {f.name}\nRecorded Size: {f.size_display} ({f.size_bytes:,} bytes)\n"
                f"Type: {f.category} (.{f.ext})  •  Integrity: {f.quality}\nPath: {f.original_path}\n\n"
                f"Note: Entries marked 'Poor' or purged without active NTFS cluster runs have no intact\n"
                f"preview stream left on disk. Try Deep Format Recovery for raw sector carving."
            )
            msg = diag_ar if self.lang == "ar" else diag_en
        else:
            # Check if deleted clusters are all zeroes (TRIM / SSD wiped)
            all_zero = all(b == 0 for b in raw[:2048])
            if all_zero:
                msg = (
                    f"⚠️ قطاعات هذا الملف المحذوف أصبحت فارغة (صفراً - SSD TRIM)\n\n"
                    f"الاسم: {f.name} ({f.size_display})\nالمصدر: {self._source_label}\n\n"
                    f"قام نظام التشغيل بمسح الكتل (TRIM) بعد الحذف، يمكنك تأكيد ذلك في تبويب Hex Inspector أعلاه."
                    if self.lang == "ar" else
                    f"⚠️ Deleted file clusters contain all zeros (SSD TRIM cleared)\n\n"
                    f"Name: {f.name} ({f.size_display})\nSource: {self._source_label}\n\n"
                    f"Windows TRIM zeroed the released SSD blocks after deletion. You can verify in the Hex Inspector tab."
                )
            else:
                msg = (
                    f"ملف ثنائي / ترويسة غير قابلة للعرض البصري المباشر\n\n"
                    f"الاسم: {f.name}\nالحجم: {f.size_display} ({f.size_bytes:,} بايت)\n"
                    f"النوع: {f.category} (.{f.ext})  •  المصدر: {self._source_label}\nالمسار: {f.original_path}\n\n"
                    f"تم قراءة {len(raw):,} بايت بنجاح — يمكنك فحص البايتات الخام في تبويب «فاحص البايتات السداسي (Hex)» أعلاه."
                    if self.lang == "ar" else
                    f"Binary File / Non-Visual Format\n\n"
                    f"Name: {f.name}\nSize: {f.size_display} ({f.size_bytes:,} bytes)\n"
                    f"Type: {f.category} (.{f.ext})  •  Source: {self._source_label}\nPath: {f.original_path}\n\n"
                    f"Successfully read {len(raw):,} bytes — switch to the 'Hex Inspector' tab above to inspect raw bytes."
                )

        info = QLabel(msg)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        info.setMaximumWidth(680)
        layout.addWidget(info, 1)

    def _build_hex_dump(self, f: RecoverableFile, raw: bytes, max_bytes: int = 4096) -> str:
        if not raw:
            return "No readable byte stream available for this entry (clusters purged or zero-length)."

        view_raw = raw[:max_bytes]
        lines = [
            f"Source: {self._source_label}  |  Showing {len(view_raw):,} of {f.size_bytes:,} bytes",
            f"Offset    00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  | ASCII",
            "-" * 78
        ]
        for offset in range(0, len(view_raw), 16):
            chunk = view_raw[offset:offset + 16]
            hex_left = " ".join(f"{b:02X}" for b in chunk[:8]).ljust(23)
            hex_right = " ".join(f"{b:02X}" for b in chunk[8:]).ljust(23)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(f"{offset:08X}  {hex_left}  {hex_right}  |{ascii_str}|")
        if f.size_bytes > max_bytes:
            lines.append(f"\n... showing first {max_bytes:,} of {f.size_bytes:,} bytes ...")
        return "\n".join(lines)


class ScanView(QWidget):
    back_to_main = pyqtSignal()
    session_requested = pyqtSignal()

    def __init__(self, lang: str = "en", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.lang = lang
        self.strings = STRINGS[lang]
        self.all_files: List[RecoverableFile] = []
        self.filtered_files: List[RecoverableFile] = []
        self.active_tree_filter_path: Optional[str] = None
        self.active_category_filter: Optional[str] = None
        self.advanced_filters = {"size": "all", "date": "all", "quality": "all"}
        self.is_paused = False
        self.is_scanning = False
        self.scanner_instance = None
        self.target_path = ""
        self.all_selected_state = True
        self._suppress_tree_check = False
        self._suppress_table_check = False
        self._last_found_count = 0
        self._last_pct = 0
        self._last_speed = 0.0

        # Search debounce timer (220ms prevents GUI freezing during rapid typing)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(220)
        self.search_timer.timeout.connect(self._apply_filters)

        self.recovery_dest_dir = self.determine_safe_default_destination("")
        self.setup_ui()

    def determine_safe_default_destination(self, source_path: str) -> str:
        """Prioritize a DIFFERENT, non-system drive (e.g., D: or F:) over OS drive C:."""
        src_drive = ""
        if source_path:
            src_drive = os.path.splitdrive(os.path.abspath(source_path))[0].upper()
        sys_drive = f"{get_system_drive_letter()}:"

        try:
            drives = enumerate_logical_drives()
            # Pass 1: Different drive AND not OS drive C:
            for d in drives:
                d_let = d.letter[:2].upper()
                if d_let != src_drive and d_let != sys_drive and d.free_bytes > 500 * 1024 * 1024:
                    return os.path.join(d.letter, "Insight_Recovered_Files")
            # Pass 2: Any different drive
            for d in drives:
                d_let = d.letter[:2].upper()
                if d_let != src_drive and d.free_bytes > 500 * 1024 * 1024:
                    return os.path.join(d.letter, "Insight_Recovered_Files")
        except Exception:
            pass

        return os.path.join(os.path.expanduser("~"), "Documents", "Insight_Recovered_Files")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 8)
        main_layout.setSpacing(6)

        # 1. Compact Top Breadcrumb, Selection & Search Bar (Zero Clipping)
        breadcrumb_bar = QFrame()
        breadcrumb_bar.setObjectName("Card")
        breadcrumb_layout = QHBoxLayout(breadcrumb_bar)
        breadcrumb_layout.setContentsMargins(8, 5, 8, 5)
        breadcrumb_layout.setSpacing(6)

        self.btn_home = QPushButton(" " + self.strings["home_btn"])
        self.btn_home.setIcon(get_ui_icon("ui_home.png"))
        self.btn_home.setIconSize(QSize(16, 16))
        self.btn_home.setObjectName("SecondaryActionBtn")
        self.btn_home.clicked.connect(self.back_to_main.emit)
        breadcrumb_layout.addWidget(self.btn_home)

        self.lbl_breadcrumb = QLabel("📁 /")
        self.lbl_breadcrumb.setObjectName("AccentLabel")
        self.lbl_breadcrumb.setMaximumWidth(260)
        breadcrumb_layout.addWidget(self.lbl_breadcrumb)

        breadcrumb_layout.addStretch()

        self.btn_sel_all = QPushButton(" " + self.strings["select_all_btn"])
        self.btn_sel_all.setIcon(get_ui_icon("ui_select_all.png"))
        self.btn_sel_all.setIconSize(QSize(16, 16))
        self.btn_sel_all.setObjectName("SecondaryActionBtn")
        self.btn_sel_all.clicked.connect(self.select_all_files)
        breadcrumb_layout.addWidget(self.btn_sel_all)

        self.btn_desel_all = QPushButton(" " + self.strings["deselect_all_btn"])
        self.btn_desel_all.setIcon(get_ui_icon("ui_deselect_all.png"))
        self.btn_desel_all.setIconSize(QSize(16, 16))
        self.btn_desel_all.setObjectName("SecondaryActionBtn")
        self.btn_desel_all.clicked.connect(self.deselect_all_files)
        breadcrumb_layout.addWidget(self.btn_desel_all)

        self.btn_filter = QPushButton("🔍 " + self.strings["filter_btn"])
        self.btn_filter.setObjectName("SecondaryActionBtn")
        self.btn_filter.clicked.connect(self.open_filter_dialog)
        breadcrumb_layout.addWidget(self.btn_filter)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText(self.strings["search_placeholder"])
        self.txt_search.setMinimumWidth(145)
        self.txt_search.setMaximumWidth(195)
        self.txt_search.textChanged.connect(lambda: self.search_timer.start())
        breadcrumb_layout.addWidget(self.txt_search)

        main_layout.addWidget(breadcrumb_bar)

        # 2. Main 3-Pane Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # 2A. Left Dual-Tab Navigation (Path / Type)
        self.left_tabs = QTabWidget()
        self.left_tabs.setMinimumWidth(190)

        self.tree_path = QTreeWidget()
        self.tree_path.setColumnCount(1)
        self.tree_path.setHeaderLabel(self.strings["tab_path"])
        self.tree_path.header().setStretchLastSection(True)
        self.tree_path.setAnimated(True)
        self.tree_path.setIndentation(16)
        self.tree_path.itemClicked.connect(self.on_path_tree_clicked)
        self.tree_path.itemChanged.connect(self.on_path_tree_check_changed)
        self.tree_path.itemExpanded.connect(self.on_path_tree_expanded)
        self.left_tabs.addTab(self.tree_path, "📁 " + self.strings["tab_path"])

        self.tree_type = QTreeWidget()
        self.tree_type.setColumnCount(1)
        self.tree_type.setHeaderLabel(self.strings["tab_type"])
        self.tree_type.header().setStretchLastSection(True)
        self.tree_type.setAnimated(True)
        self.tree_type.setIndentation(16)
        self.tree_type.itemClicked.connect(self.on_type_tree_clicked)
        self.left_tabs.addTab(self.tree_type, "🏷️ " + self.strings["tab_type"])

        self.splitter.addWidget(self.left_tabs)

        # 2B. Central File Data Table with Prominent File Name Column
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self._update_table_headers()

        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setMinimumSectionSize(55)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 118)
        self.table.setColumnWidth(3, 82)
        self.table.setColumnWidth(4, 70)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.itemClicked.connect(self.on_file_row_clicked)
        self.table.itemDoubleClicked.connect(lambda _: self.open_full_preview())
        self.table.itemChanged.connect(self.on_table_item_changed)
        hdr.sectionClicked.connect(self.on_header_section_clicked)

        center_layout.addWidget(self.table)
        self.splitter.addWidget(center_widget)

        # 2C. Right Details & Inspector Panel
        self.right_inspector = QFrame()
        self.right_inspector.setObjectName("Card")
        self.right_inspector.setMinimumWidth(205)
        self.right_inspector.setMaximumWidth(285)
        insp_layout = QVBoxLayout(self.right_inspector)
        insp_layout.setContentsMargins(10, 10, 10, 10)
        insp_layout.setSpacing(7)

        self.lbl_thumb = QLabel()
        self.lbl_thumb.setObjectName("ThumbPreview")
        self.lbl_thumb.setFixedHeight(116)
        self.lbl_thumb.setWordWrap(True)
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        insp_layout.addWidget(self.lbl_thumb)

        self.btn_preview = QPushButton("👁️ " + self.strings["preview_btn"])
        self.btn_preview.setObjectName("PrimaryActionBtn")
        self.btn_preview.clicked.connect(self.open_full_preview)
        insp_layout.addWidget(self.btn_preview)

        # File Properties
        props_layout = QVBoxLayout()
        props_layout.setContentsMargins(2, 2, 2, 2)
        props_layout.setSpacing(3)

        self.lbl_prop_name = QLabel(f"{self.strings['prop_name']} -")
        self.lbl_prop_name.setObjectName("CardTitle")
        self.lbl_prop_name.setWordWrap(True)
        self.lbl_prop_name.setMaximumHeight(34)
        props_layout.addWidget(self.lbl_prop_name)

        self.lbl_prop_size = QLabel(f"{self.strings['prop_size']} -")
        self.lbl_prop_size.setObjectName("MutedLabel")
        props_layout.addWidget(self.lbl_prop_size)

        self.lbl_prop_type = QLabel(f"{self.strings['prop_type']} -")
        self.lbl_prop_type.setObjectName("MutedLabel")
        props_layout.addWidget(self.lbl_prop_type)

        self.lbl_prop_date = QLabel(f"{self.strings['prop_date']} -")
        self.lbl_prop_date.setObjectName("MutedLabel")
        props_layout.addWidget(self.lbl_prop_date)

        self.lbl_prop_quality = QLabel(f"{self.strings['prop_status']} -")
        self.lbl_prop_quality.setStyleSheet("font-size: 11px; font-weight: 700; color: #10B981;")
        props_layout.addWidget(self.lbl_prop_quality)

        self.lbl_prop_path = QLabel(f"{self.strings['prop_path']} -")
        self.lbl_prop_path.setObjectName("MutedLabel")
        self.lbl_prop_path.setWordWrap(True)
        self.lbl_prop_path.setMaximumHeight(38)
        props_layout.addWidget(self.lbl_prop_path)

        insp_layout.addLayout(props_layout)
        insp_layout.addStretch()

        # Safe Recovery Destination Box
        dest_box = QFrame()
        dest_box.setObjectName("InsetBox")
        dest_layout = QVBoxLayout(dest_box)
        dest_layout.setContentsMargins(8, 7, 8, 7)
        dest_layout.setSpacing(4)

        self.lbl_dest_t = QLabel(self.strings["recovery_path_lbl"])
        self.lbl_dest_t.setObjectName("SectionHeader")
        dest_layout.addWidget(self.lbl_dest_t)

        dest_row = QHBoxLayout()
        dest_row.setSpacing(4)
        self.txt_dest = QLineEdit(self.recovery_dest_dir)
        self.txt_dest.setStyleSheet("font-size: 10px; padding: 4px 6px;")
        dest_row.addWidget(self.txt_dest)

        self.btn_browse_dest = QPushButton("...")
        self.btn_browse_dest.setObjectName("SecondaryActionBtn")
        self.btn_browse_dest.setFixedSize(28, 25)
        self.btn_browse_dest.setStyleSheet("padding: 0px; font-weight: 700;")
        self.btn_browse_dest.setToolTip("Browse and choose a safe target drive")
        self.btn_browse_dest.clicked.connect(self.browse_dest_path)
        dest_row.addWidget(self.btn_browse_dest)
        dest_layout.addLayout(dest_row)

        self.lbl_drive_safety = QLabel("🛡️ " + self.strings["safe_drive_lbl"])
        self.lbl_drive_safety.setStyleSheet("font-size: 10px; color: #10B981; font-weight: 700;")
        dest_layout.addWidget(self.lbl_drive_safety)

        insp_layout.addWidget(dest_box)
        self.splitter.addWidget(self.right_inspector)

        # Full-width EaseUS-style distribution: [Tree: 250px, Table: 580px, Inspector: 225px]
        self.splitter.setSizes([250, 580, 225])
        main_layout.addWidget(self.splitter, 1)

        # 3. Unified Bottom Live Scan & Action Bar (Zero Clipping)
        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("Card")
        bot_v_layout = QVBoxLayout(self.bottom_bar)
        bot_v_layout.setContentsMargins(12, 6, 12, 7)
        bot_v_layout.setSpacing(4)

        prog_header_layout = QHBoxLayout()
        self.lbl_live_searching = QLabel("Searching: ...")
        self.lbl_live_searching.setObjectName("AccentLabel")
        prog_header_layout.addWidget(self.lbl_live_searching, 1)

        self.lbl_live_speed = QLabel("0%  •  0.0 MB/s")
        self.lbl_live_speed.setObjectName("MutedLabel")
        prog_header_layout.addWidget(self.lbl_live_speed)
        bot_v_layout.addLayout(prog_header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)  # Fixes clipped percentage text!
        self.progress_bar.setFixedHeight(5)
        bot_v_layout.addWidget(self.progress_bar)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.spinner_widget = ScanningSpinnerWidget()
        ctrl_row.addWidget(self.spinner_widget)

        status_v = QVBoxLayout()
        status_v.setSpacing(1)
        self.lbl_status_title = QLabel(f"{self.strings['status_scanning']} 0 (0 B)")
        self.lbl_status_title.setObjectName("CardTitle")
        status_v.addWidget(self.lbl_status_title)

        self.lbl_status_sub = QLabel(self.strings["status_patient"])
        self.lbl_status_sub.setObjectName("MutedLabel")
        status_v.addWidget(self.lbl_status_sub)
        ctrl_row.addLayout(status_v, 1)

        self.btn_pause = QPushButton(" " + self.strings["btn_pause"])
        self.btn_pause.setIcon(get_ui_icon("ui_pause.png"))
        self.btn_pause.setIconSize(QSize(16, 16))
        self.btn_pause.setObjectName("SecondaryActionBtn")
        self.btn_pause.clicked.connect(self.toggle_pause)
        ctrl_row.addWidget(self.btn_pause)

        self.btn_stop = QPushButton(" " + self.strings["btn_stop"])
        self.btn_stop.setIcon(get_ui_icon("ui_stop.png"))
        self.btn_stop.setIconSize(QSize(16, 16))
        self.btn_stop.setObjectName("DangerActionBtn")
        self.btn_stop.clicked.connect(self.stop_scan)
        ctrl_row.addWidget(self.btn_stop)

        self.lbl_selected_summary = QLabel(f"{self.strings['selected_lbl']} 0 {self.strings['files_word']} (0 B)")
        self.lbl_selected_summary.setObjectName("AccentLabel")
        ctrl_row.addWidget(self.lbl_selected_summary)

        self.btn_recover = QPushButton(self.strings["btn_recover"])
        self.btn_recover.setObjectName("PrimaryActionBtn")
        self.btn_recover.setMinimumWidth(120)
        self.btn_recover.clicked.connect(self.recover_selected_files)
        ctrl_row.addWidget(self.btn_recover)

        bot_v_layout.addLayout(ctrl_row)
        main_layout.addWidget(self.bottom_bar)

    def set_language(self, lang: str):
        self.lang = lang
        self.strings = STRINGS[lang]
        self.btn_home.setText(" " + self.strings["home_btn"])
        self.btn_sel_all.setText(" " + self.strings["select_all_btn"])
        self.btn_desel_all.setText(" " + self.strings["deselect_all_btn"])
        self._update_filter_btn_text()
        self.txt_search.setPlaceholderText(self.strings["search_placeholder"])
        self.left_tabs.setTabText(0, "📁 " + self.strings["tab_path"])
        self.left_tabs.setTabText(1, "🏷️ " + self.strings["tab_type"])
        self.tree_path.setHeaderLabel(self.strings["tab_path"])
        self.tree_type.setHeaderLabel(self.strings["tab_type"])
        self._update_table_headers()
        self.btn_preview.setText("👁️ " + self.strings["preview_btn"])
        self.lbl_dest_t.setText(self.strings["recovery_path_lbl"])
        self.btn_pause.setText((" " + self.strings["btn_resume"]) if self.is_paused else (" " + self.strings["btn_pause"]))
        self.btn_pause.setIcon(get_ui_icon("ui_resume.png") if self.is_paused else get_ui_icon("ui_pause.png"))
        self.btn_stop.setText(" " + self.strings["btn_stop"])
        self.btn_recover.setText(self.strings["btn_recover"])
        self.validate_dest_drive_safety()
        self.update_selection_summary()

    def _update_table_headers(self):
        prefix = "[✓] " if self.all_selected_state else "[ ] "
        self.table.setHorizontalHeaderLabels([
            prefix + self.strings["col_name"],
            self.strings["col_date"],
            self.strings["col_type"],
            self.strings["col_size"],
            self.strings["col_quality"]
        ])

    def _update_filter_btn_text(self):
        active_cnt = sum(1 for v in self.advanced_filters.values() if v != "all")
        suffix = f" ({active_cnt})" if active_cnt > 0 else ""
        self.btn_filter.setText(f"🔍 {self.strings['filter_btn']}{suffix}")

    def open_filter_dialog(self):
        dlg = AdvancedFilterDialog(self.lang, self.advanced_filters, parent=self)
        if dlg.exec():
            self.advanced_filters = dlg.filters
            self._update_filter_btn_text()
            self._apply_filters()

    def set_target(self, target_path: str):
        # CRITICAL FIX: Completely reset all stale state from any previous scan!
        self.target_path = target_path
        self.all_files = []
        self.filtered_files = []
        self.active_tree_filter_path = None
        self.active_category_filter = None
        self._tree_children_map = {}
        self._tree_cum_counts = {}
        self._tree_cum_sizes = {}
        self._tree_disp_names = {}
        self.is_paused = False
        self.is_scanning = True

        self.tree_path.blockSignals(True)
        self.tree_path.clear()
        self.tree_path.blockSignals(False)
        self.tree_type.blockSignals(True)
        self.tree_type.clear()
        self.tree_type.blockSignals(False)
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.blockSignals(False)
        self.txt_search.blockSignals(True)
        self.txt_search.clear()
        self.txt_search.blockSignals(False)

        self.lbl_prop_name.setText(f"{self.strings['prop_name']} -")
        self.lbl_prop_size.setText(f"{self.strings['prop_size']} -")
        self.lbl_prop_type.setText(f"{self.strings['prop_type']} -")
        self.lbl_prop_date.setText(f"{self.strings['prop_date']} -")
        self.lbl_prop_quality.setText(f"{self.strings['prop_status']} -")
        self.lbl_prop_path.setText(f"{self.strings['prop_path']} -")
        self.lbl_thumb.clear()
        self.lbl_selected_summary.setText(f"{self.strings['selected_lbl']} 0 {self.strings['files_word']} (0 B)")

        disp = target_path if len(target_path) < 28 else "..." + target_path[-25:]
        self.lbl_breadcrumb.setText(f"📁 {disp}")
        self.lbl_breadcrumb.setToolTip(target_path)
        self.advanced_filters = {"size": "all", "date": "all", "quality": "all"}
        self._update_filter_btn_text()
        self.btn_pause.setText(" " + self.strings["btn_pause"])
        self.btn_pause.setIcon(get_ui_icon("ui_pause.png"))
        self.btn_pause.setVisible(True)
        self.btn_stop.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.lbl_live_searching.setVisible(True)
        self.lbl_live_speed.setVisible(True)
        self.lbl_live_speed.setText("0%  •  0.0 MB/s")
        self.spinner_widget.start_scanning()
        self.lbl_status_title.setText(f"{self.strings['status_scanning']} 0 (0 B)")
        self.lbl_status_sub.setText(self.strings["status_patient"])

        safe_path = self.determine_safe_default_destination(target_path)
        self.recovery_dest_dir = safe_path
        self.txt_dest.setText(safe_path)
        self.validate_dest_drive_safety()

    def validate_dest_drive_safety(self):
        src_drive = os.path.splitdrive(os.path.abspath(self.target_path))[0].upper() if self.target_path else ""
        dest_text = self.txt_dest.text().strip()
        dest_drive = os.path.splitdrive(os.path.abspath(dest_text))[0].upper() if dest_text else ""

        if src_drive and dest_drive and src_drive == dest_drive:
            self.lbl_drive_safety.setText(f"⚠️ {self.strings['warn_same_drive_lbl']}")
            self.lbl_drive_safety.setStyleSheet("font-size: 10px; color: #EF4444; font-weight: 700;")
        else:
            self.lbl_drive_safety.setText(f"🛡️ {self.strings['safe_drive_lbl']} ({dest_drive})")
            self.lbl_drive_safety.setStyleSheet("font-size: 10px; color: #10B981; font-weight: 700;")

    def update_progress(self, pct: Optional[int], status: str, found_count: int, speed_mbps: float = 0.0):
        if pct is not None:
            self._last_pct = pct
            self.progress_bar.setValue(pct)
        self._last_found_count = found_count
        self._last_speed = speed_mbps
        disp_st = status if len(status) < 65 else "..." + status[-62:]
        self.lbl_live_searching.setText(f"🔎 {disp_st}")
        self.lbl_live_speed.setText(f"{self._last_pct}%  •  {speed_mbps:.1f} MB/s")
        self.lbl_status_title.setText(f"{self.strings['status_scanning']} {found_count} {self.strings['files_word']}")

    def set_results(self, files: List[RecoverableFile], session_loaded: bool = False):
        self.is_scanning = False
        self.is_paused = False
        self.all_files = files
        self.filtered_files = list(files)
        self.active_tree_filter_path = None
        self.active_category_filter = None

        # Smart commercial default (matches EaseUS): on huge partition scans (>2,000 files),
        # start unchecked so user picks only the exact deleted folder(s) they want!
        if len(self.all_files) > 2000:
            self.all_selected_state = False
            for f in self.all_files:
                f.selected = False
        else:
            self.all_selected_state = True
            for f in self.all_files:
                f.selected = True
        self._update_table_headers()

        self.populate_path_tree()
        self.populate_type_tree()
        self.populate_table()

        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.lbl_live_searching.setVisible(False)
        self.lbl_live_speed.setVisible(False)
        self.btn_pause.setVisible(False)
        self.btn_stop.setVisible(False)
        self.spinner_widget.set_completed()

        total_sz = sum(f.size_bytes for f in self.all_files)
        total_sz_str = self.format_bytes(total_sz)
        del_cnt = sum(1 for f in self.all_files if getattr(f, "is_deleted", False))

        prefix = self.strings["status_session_loaded"] if session_loaded else self.strings["status_scan_complete"]
        del_note = f"  •  🗑️ {del_cnt:,} deleted/cut" if del_cnt > 0 else ""
        self.lbl_status_title.setText(f"{prefix} {len(self.all_files):,} ({total_sz_str}){del_note}")
        self.lbl_status_sub.setText(self.strings["status_scan_complete_sub"])
        self.update_selection_summary()

    @staticmethod
    def _bucket_icon(name: str) -> str:
        low = name.lower()
        if "deleted" in low or "cut" in low or "recycle" in low:
            return "🗑️"
        if "lost" in low or "orphan" in low:
            return "🧩"
        if "partition" in low or (":" in name and len(name) <= 18):
            return "💾"
        if "reconstructed" in low or "raw" in low:
            return "🔬"
        return "📁"

    def populate_path_tree(self):
        """
        Ultra-fast Lazy Commercial Folder Tree (handles 500,000+ files in < 150ms!).
        Uses standard commercial buckets: Deleted & Cut Files, Deleted Files (Drive),
        Target Location, Partition Root, Lost & Orphaned Files.
        """
        self.tree_path.setUpdatesEnabled(False)
        self.tree_path.blockSignals(True)
        self.tree_path.setIconSize(QSize(18, 18))
        self.tree_path.clear()

        root_name = os.path.basename(self.target_path) or self.target_path or "Root"
        total_sz = self.format_bytes(sum(f.size_bytes for f in self.all_files))
        init_chk = Qt.CheckState.Checked if self.all_selected_state else Qt.CheckState.Unchecked

        root_item = QTreeWidgetItem(self.tree_path)
        root_item.setText(0, f"{root_name}  ({len(self.all_files):,} - {total_sz})")
        root_item.setIcon(0, get_ui_icon("ui_folder.png"))
        root_item.setFlags(root_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        root_item.setCheckState(0, init_chk)
        root_item.setData(0, Qt.ItemDataRole.UserRole, "__ROOT__")

        # Index folder hierarchy purely in Python dicts (blazing fast even for 500K files!)
        children_map: Dict[str, set] = {}
        cum_counts: Dict[str, int] = {}
        cum_sizes: Dict[str, int] = {}
        disp_names: Dict[str, str] = {}
        norm_target = os.path.normpath(self.target_path).lower() if self.target_path else ""

        for f in self.all_files:
            disp_rel = getattr(f, "display_folder_rel", "")
            if not disp_rel:
                f_dir = os.path.dirname(os.path.normpath(f.original_path))
                if norm_target and f_dir.lower().startswith(norm_target):
                    rel = os.path.relpath(f_dir, self.target_path)
                    disp_rel = "" if rel == "." else rel
                else:
                    disp_rel = f.category
                f.display_folder_rel = disp_rel

            rel_low = disp_rel.lower()
            f.folder_rel = rel_low
            if not rel_low:
                continue

            parts_disp = disp_rel.split(os.sep)
            parts_low = rel_low.split(os.sep)
            acc_low = ""
            parent_low = ""
            sz = f.size_bytes

            for pd, pl in zip(parts_disp, parts_low):
                if not pl:
                    continue
                acc_low = (acc_low + os.sep + pl) if acc_low else pl
                if acc_low not in disp_names:
                    disp_names[acc_low] = pd
                children_map.setdefault(parent_low, set()).add(acc_low)
                cum_counts[acc_low] = cum_counts.get(acc_low, 0) + 1
                cum_sizes[acc_low] = cum_sizes.get(acc_low, 0) + sz
                parent_low = acc_low

        self._tree_children_map = children_map
        self._tree_cum_counts = cum_counts
        self._tree_cum_sizes = cum_sizes
        self._tree_disp_names = disp_names

        # Populate immediate Level-1 children of root (Deleted & Cut first, then Target, Partition, Lost!)
        self._populate_tree_children(root_item, "", init_chk)
        root_item.setExpanded(True)
        self.tree_path.blockSignals(False)
        self.tree_path.setUpdatesEnabled(True)

    def _populate_tree_children(self, parent_item: QTreeWidgetItem, parent_key: str, inherit_chk: Qt.CheckState):
        child_keys = self._tree_children_map.get(parent_key, set())
        if not child_keys:
            return

        def sort_priority(k: str):
            name = self._tree_disp_names.get(k, k).lower()
            if "deleted & cut" in name:
                return (0, name)
            if "deleted" in name:
                return (1, name)
            if "lost" in name or "orphan" in name:
                return (4, name)
            if "partition" in name:
                return (3, name)
            return (2, name)

        for ck in sorted(child_keys, key=sort_priority):
            base = self._tree_disp_names.get(ck, os.path.basename(ck))
            cnt = self._tree_cum_counts.get(ck, 0)
            sz_str = self.format_bytes(self._tree_cum_sizes.get(ck, 0))
            low_b = base.lower()

            node = QTreeWidgetItem(parent_item)
            node.setText(0, f"{base}  ({cnt:,} - {sz_str})")
            if parent_key == "" and ("deleted" in low_b or "cut" in low_b or "recycle" in low_b):
                node.setIcon(0, get_ui_icon("ui_trash.png"))
            elif parent_key == "" and ("partition" in low_b):
                node.setIcon(0, QIcon(get_asset_path("disk_3d.png")))
            else:
                node.setIcon(0, get_ui_icon("ui_folder.png"))
            node.setToolTip(0, ck)
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, inherit_chk)
            node.setData(0, Qt.ItemDataRole.UserRole, ck)

            if self._tree_children_map.get(ck):
                dummy = QTreeWidgetItem(node)
                dummy.setText(0, "...")
                dummy.setData(0, Qt.ItemDataRole.UserRole, "__LAZY__")

    def on_path_tree_expanded(self, item: QTreeWidgetItem):
        """Lazily populate child folders on demand in < 1ms when user clicks [+] / ▶!"""
        if item.childCount() == 1 and item.child(0).data(0, Qt.ItemDataRole.UserRole) == "__LAZY__":
            self.tree_path.setUpdatesEnabled(False)
            self.tree_path.blockSignals(True)
            item.takeChild(0)
            folder_key = item.data(0, Qt.ItemDataRole.UserRole)
            if folder_key and folder_key != "__ROOT__":
                self._populate_tree_children(item, folder_key, item.checkState(0))
            self.tree_path.blockSignals(False)
            self.tree_path.setUpdatesEnabled(True)

    def populate_type_tree(self):
        self.tree_type.blockSignals(True)
        self.tree_type.clear()
        self.tree_type.setIconSize(QSize(18, 18))

        total_sz = self.format_bytes(sum(f.size_bytes for f in self.all_files))
        root_item = QTreeWidgetItem(self.tree_type)
        root_item.setText(0, f"{self.strings['tab_all']}  ({len(self.all_files):,} - {total_sz})")
        root_item.setIcon(0, get_ui_icon("ui_folder.png"))
        root_item.setData(0, Qt.ItemDataRole.UserRole, "ALL")

        cats: Dict[str, List[RecoverableFile]] = {}
        for f in self.all_files:
            cats.setdefault(f.category, []).append(f)

        for c_name, flist in sorted(cats.items()):
            c_sz = self.format_bytes(sum(x.size_bytes for x in flist))
            child = QTreeWidgetItem(root_item)
            child.setText(0, f"{c_name}  ({len(flist):,} - {c_sz})")
            child.setIcon(0, get_category_icon(c_name))
            child.setData(0, Qt.ItemDataRole.UserRole, c_name)

        root_item.setExpanded(True)
        self.tree_type.blockSignals(False)

    def populate_table(self):
        """High-performance batch table population with crisp per-extension icons."""
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setIconSize(QSize(18, 18))
        self.table.clearContents()

        display_count = min(2000, len(self.filtered_files))
        self.table.setRowCount(display_count)

        for row in range(display_count):
            f = self.filtered_files[row]

            name_item = QTableWidgetItem(f.name)
            name_item.setIcon(get_ext_icon(f.ext, f.category))
            name_item.setToolTip(f.original_path)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
            name_item.setCheckState(Qt.CheckState.Checked if getattr(f, 'selected', True) else Qt.CheckState.Unchecked)
            name_item.setData(Qt.ItemDataRole.UserRole, f)
            self.table.setItem(row, 0, name_item)

            date_str = f.deleted_time.strftime("%Y-%m-%d %H:%M") if hasattr(f, 'deleted_time') and f.deleted_time else "-"
            date_item = QTableWidgetItem(date_str)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, date_item)

            type_item = QTableWidgetItem(f".{f.ext.upper()} ({f.category.split()[0]})")
            type_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 2, type_item)

            size_item = SizeTableWidgetItem(f.size_display)
            size_item.setData(Qt.ItemDataRole.UserRole, f.size_bytes)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            size_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 3, size_item)

            qual_item = QTableWidgetItem(f.quality)
            if f.quality == "Excellent":
                qual_item.setForeground(QColor("#10B981"))
            elif f.quality == "Good":
                qual_item.setForeground(QColor("#3B82F6"))
            else:
                qual_item.setForeground(QColor("#EF4444"))
            qual_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 4, qual_item)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)

        if display_count > 0:
            self.table.selectRow(0)
            first_it = self.table.item(0, 0)
            if first_it and first_it.data(Qt.ItemDataRole.UserRole):
                self.show_file_details(first_it.data(Qt.ItemDataRole.UserRole))

    def on_table_item_changed(self, item: QTableWidgetItem):
        if item.column() == 0 and not self._suppress_table_check:
            f = item.data(Qt.ItemDataRole.UserRole)
            if f:
                f.selected = (item.checkState() == Qt.CheckState.Checked)
                self.update_selection_summary()

    def sync_table_checkboxes(self):
        """Ultra-fast zero-repopulation table checkbox synchronization."""
        self._suppress_table_check = True
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            it = self.table.item(r, 0)
            if it:
                f = it.data(Qt.ItemDataRole.UserRole)
                if f:
                    is_sel = getattr(f, 'selected', True)
                    expected = Qt.CheckState.Checked if is_sel else Qt.CheckState.Unchecked
                    if it.checkState() != expected:
                        it.setCheckState(expected)
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)
        self._suppress_table_check = False

    def select_all_files(self):
        for f in self.all_files:
            f.selected = True
        self._set_all_tree_checks(Qt.CheckState.Checked)
        self.all_selected_state = True
        self._update_table_headers()
        self.sync_table_checkboxes()
        self.update_selection_summary()

    def deselect_all_files(self):
        for f in self.all_files:
            f.selected = False
        self._set_all_tree_checks(Qt.CheckState.Unchecked)
        self.all_selected_state = False
        self._update_table_headers()
        self.sync_table_checkboxes()
        self.update_selection_summary()

    def _set_all_tree_checks(self, state: Qt.CheckState):
        self.tree_path.setUpdatesEnabled(False)
        self.tree_path.blockSignals(True)
        def walk(parent_item):
            for i in range(parent_item.childCount()):
                ch = parent_item.child(i)
                ch.setCheckState(0, state)
                walk(ch)
        root = self.tree_path.topLevelItem(0)
        if root:
            root.setCheckState(0, state)
            walk(root)
        self.tree_path.blockSignals(False)
        self.tree_path.setUpdatesEnabled(True)

    def on_header_section_clicked(self, logical_index: int):
        if logical_index == 0:
            if self.all_selected_state:
                self.deselect_all_files()
            else:
                self.select_all_files()

    def update_selection_summary(self):
        selected_count = 0
        total_sz = 0
        for f in self.all_files:
            if getattr(f, 'selected', False):
                selected_count += 1
                total_sz += f.size_bytes
        sz_disp = self.format_bytes(total_sz)
        self.lbl_selected_summary.setText(f"{self.strings['selected_lbl']} {selected_count} {self.strings['files_word']} ({sz_disp})")

    def on_file_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        name_it = self.table.item(row, 0)
        if name_it:
            f: RecoverableFile = name_it.data(Qt.ItemDataRole.UserRole)
            if f:
                self.show_file_details(f)

    def show_file_details(self, f: RecoverableFile):
        short_name = f.name if len(f.name) < 30 else f.name[:27] + "..."
        self.lbl_prop_name.setText(f"{self.strings['prop_name']} {short_name}")
        self.lbl_prop_name.setToolTip(f.name)
        self.lbl_prop_size.setText(f"{self.strings['prop_size']} {f.size_display}")
        self.lbl_prop_type.setText(f"{self.strings['prop_type']} {f.category} (.{f.ext})")
        dt_str = f.deleted_time.strftime("%Y-%m-%d %H:%M") if hasattr(f, 'deleted_time') and f.deleted_time else "-"
        self.lbl_prop_date.setText(f"{self.strings['prop_date']} {dt_str}")
        self.lbl_prop_quality.setText(f"{self.strings['prop_status']} {f.quality}")
        q_color = "#10B981" if f.quality == "Excellent" else ("#3B82F6" if f.quality == "Good" else "#EF4444")
        self.lbl_prop_quality.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {q_color};")

        short_path = f.original_path if len(f.original_path) < 48 else "..." + f.original_path[-45:]
        self.lbl_prop_path.setText(f"{self.strings['prop_path']} {short_path}")
        self.lbl_prop_path.setToolTip(f.original_path)

        # Reset right-panel preview box cleanly before rendering
        self.lbl_thumb.clear()
        self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ext_l = (f.ext or "").lower()

        # 1. Live Image Thumbnail (works for live, Recycle Bin $R, AND deleted NTFS $MFT clusters!)
        if ext_l in {"png", "jpg", "jpeg", "bmp", "ico", "webp", "gif", "tif", "tiff"}:
            raw_img, _ = read_recoverable_file_bytes(f, max_bytes=4 * 1024 * 1024)
            pix = load_qpixmap_from_bytes(raw_img)
            if pix and not pix.isNull():
                self.lbl_thumb.setPixmap(pix.scaled(190, 104, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return

        # 2. Live PDF Page-1 Mini Thumbnail
        elif ext_l == "pdf":
            try:
                raw_pdf, _ = read_recoverable_file_bytes(f, max_bytes=4 * 1024 * 1024)
                if raw_pdf:
                    import fitz
                    doc = fitz.open(stream=raw_pdf, filetype="pdf")
                    if doc.page_count > 0:
                        pm = doc.load_page(0).get_pixmap(matrix=fitz.Matrix(0.35, 0.35))
                        qimg = QImage(pm.samples, pm.width, pm.height, pm.stride, QImage.Format.Format_RGB888)
                        pix = QPixmap.fromImage(qimg.copy())
                        doc.close()
                        if not pix.isNull():
                            self.lbl_thumb.setPixmap(pix.scaled(190, 104, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                            return
                    doc.close()
            except Exception:
                pass

        # 3. Live Mini Content Snippet right inside the right panel for Text / Code / DOCX / ZIP / LNK!
        snippet = ""
        try:
            if ext_l in {"txt", "py", "json", "xml", "ini", "cfg", "log", "md", "csv", "html", "htm", "css", "js", "sql", "bat", "ps1", "srt", "yaml", "yml", "crt"}:
                raw_t, _ = read_recoverable_file_bytes(f, max_bytes=4096)
                if raw_t:
                    txt_lines = [ln.strip() for ln in decode_text_bytes(raw_t, 600).splitlines() if ln.strip()][:5]
                    if txt_lines:
                        snippet = "\n".join(ln[:34] + ("..." if len(ln) > 34 else "") for ln in txt_lines)
            elif ext_l == "docx":
                raw_d, _ = read_recoverable_file_bytes(f, max_bytes=2 * 1024 * 1024)
                if raw_d:
                    with zipfile.ZipFile(io.BytesIO(raw_d), "r") as zf:
                        if "word/document.xml" in zf.namelist():
                            root = ET.fromstring(zf.read("word/document.xml"))
                            words = [el.text.strip() for el in root.iter() if el.text and el.tag.endswith("}t") and el.text.strip()]
                            if words:
                                snippet = "📄 " + " ".join(words)[:165] + ("..." if len(" ".join(words)) > 165 else "")
            elif ext_l in {"zip", "jar", "apk"}:
                raw_z, _ = read_recoverable_file_bytes(f, max_bytes=4 * 1024 * 1024)
                if raw_z:
                    with zipfile.ZipFile(io.BytesIO(raw_z), "r") as zf:
                        names = zf.namelist()
                        top_n = [os.path.basename(n.rstrip("/")) or n for n in names[:3]]
                        snippet = f"📦 ZIP ({len(names):,} files)\n" + "\n".join("• " + x[:28] for x in top_n)
            elif ext_l == "lnk":
                raw_l, _ = read_recoverable_file_bytes(f, max_bytes=16384)
                li = parse_windows_lnk_bytes(raw_l)
                if li and li["target_paths"]:
                    tp = li["target_paths"][0]
                    snippet = f"🔗 Shortcut Target:\n{os.path.basename(tp)[:32]}\n({tp[:42]}...)"
        except Exception:
            snippet = ""

        if snippet:
            self.lbl_thumb.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.lbl_thumb.setText(snippet)
            self.lbl_thumb.setFont(QFont("Consolas", 8))
            return

        ext_ico = get_ext_icon(f.ext, f.category)
        if not ext_ico.isNull():
            self.lbl_thumb.setPixmap(ext_ico.pixmap(56, 56))
        else:
            ico_path = get_asset_path("file_3d.png")
            if os.path.exists(ico_path):
                self.lbl_thumb.setPixmap(QPixmap(ico_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def on_path_tree_clicked(self, item: QTreeWidgetItem, column: int):
        if self._suppress_tree_check:
            return
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        self.active_tree_filter_path = folder_path if folder_path != "__ROOT__" else None
        self._apply_filters()

    def on_path_tree_check_changed(self, item: QTreeWidgetItem, column: int):
        if column != 0 or self._suppress_tree_check:
            return
        is_chk = (item.checkState(0) == Qt.CheckState.Checked)
        folder_path = item.data(0, Qt.ItemDataRole.UserRole)
        if folder_path is None:
            return

        self._suppress_tree_check = True
        self.tree_path.setUpdatesEnabled(False)
        self.tree_path.blockSignals(True)
        def set_children_check(parent_item, state):
            for i in range(parent_item.childCount()):
                ch = parent_item.child(i)
                ch.setCheckState(0, state)
                set_children_check(ch, state)
        set_children_check(item, item.checkState(0))
        self.tree_path.blockSignals(False)
        self.tree_path.setUpdatesEnabled(True)
        self._suppress_tree_check = False

        if folder_path == "__ROOT__":
            for f in self.all_files:
                f.selected = is_chk
        else:
            accum_low = folder_path.lower()
            for f in self.all_files:
                rel = getattr(f, 'folder_rel', '')
                if rel == accum_low or rel.startswith(accum_low + os.sep) or rel.startswith(accum_low + "/"):
                    f.selected = is_chk

        self.sync_table_checkboxes()
        self.update_selection_summary()

    def on_type_tree_clicked(self, item: QTreeWidgetItem, column: int):
        cat_name = item.data(0, Qt.ItemDataRole.UserRole)
        self.active_category_filter = cat_name if cat_name != "ALL" else None
        self._apply_filters()

    def _apply_filters(self):
        query = self.txt_search.text().strip().lower()
        results = list(self.all_files)

        # 1. Folder Path filter (exact relative path prefix)
        if self.active_tree_filter_path:
            p_low = self.active_tree_filter_path.lower()
            results = [
                f for f in results
                if getattr(f, 'folder_rel', '') == p_low
                or getattr(f, 'folder_rel', '').startswith(p_low + os.sep)
                or getattr(f, 'folder_rel', '').startswith(p_low + "/")
                or p_low in f.original_path.lower()
            ]

        # 2. Category filter
        if self.active_category_filter:
            results = [f for f in results if f.category == self.active_category_filter]

        # 3. Advanced filters (Size, Date, Integrity)
        sz_f = self.advanced_filters.get("size", "all")
        if sz_f == "small":
            results = [f for f in results if f.size_bytes < 1024 * 1024]
        elif sz_f == "medium":
            results = [f for f in results if 1024 * 1024 <= f.size_bytes <= 100 * 1024 * 1024]
        elif sz_f == "large":
            results = [f for f in results if f.size_bytes > 100 * 1024 * 1024]

        dt_f = self.advanced_filters.get("date", "all")
        if dt_f != "all":
            now = datetime.now()
            deltas = {"today": 1, "week": 7, "month": 30, "year": 365}
            cutoff = now - timedelta(days=deltas.get(dt_f, 36500))
            results = [f for f in results if getattr(f, 'deleted_time', None) and f.deleted_time >= cutoff]

        q_f = self.advanced_filters.get("quality", "all")
        if q_f != "all":
            results = [f for f in results if f.quality == q_f]

        # 4. Search query filter
        if query:
            results = [f for f in results if query in f.name.lower() or query in f.ext.lower()]

        self.filtered_files = results
        self.populate_table()

    def browse_dest_path(self):
        chosen = QFileDialog.getExistingDirectory(self, "Select Safe Recovery Destination", self.recovery_dest_dir)
        if chosen:
            self.recovery_dest_dir = os.path.normpath(chosen)
            self.txt_dest.setText(self.recovery_dest_dir)
            self.validate_dest_drive_safety()

    def recover_selected_files(self):
        target_dir = self.txt_dest.text().strip() or self.recovery_dest_dir
        selected = [f for f in self.all_files if getattr(f, 'selected', True)]

        if not selected:
            QMessageBox.warning(
                self,
                "لم يتم تحديد ملفات" if self.lang == "ar" else "No Files Selected",
                "يرجى تحديد ملف أو مجلد واحد على الأقل للاستعادة." if self.lang == "ar" else "Please select at least one file or folder to recover."
            )
            return

        src_drive = os.path.splitdrive(os.path.abspath(self.target_path))[0].upper() if self.target_path else ""
        dest_drive = os.path.splitdrive(os.path.abspath(target_dir))[0].upper() if target_dir else ""

        if src_drive and dest_drive and src_drive == dest_drive:
            warn_box = QMessageBox(self)
            warn_box.setIcon(QMessageBox.Icon.Warning)
            warn_box.setWindowTitle("⚠️ تحذير أمان الاسترجاع: نفس القرص!" if self.lang == "ar" else "⚠️ Recovery Safety: Same Drive!")
            warn_msg = (
                f"أنت تحاول استرجاع الملفات إلى نفس القرص ({dest_drive}) الذي تم الفحص منه!\n\n"
                "⚠️ كتابة الملفات المسترجعة على نفس القرص قد تتلف القطاعات المحذوفة الأخرى نهائياً.\n"
                "يُرجى اختيار قرص مختلف (مثل D: أو فلاشة USB خارجية)."
                if self.lang == "ar" else
                f"You are recovering to the same drive ({dest_drive}) being scanned!\n\n"
                "⚠️ Writing to the same drive may overwrite deleted sectors permanently.\n"
                "Please choose a different drive."
            )
            warn_box.setText(warn_msg)
            btn_choose = warn_box.addButton("اختيار قرص آخر آمن (موصى به)" if self.lang == "ar" else "Choose Different Drive (Recommended)", QMessageBox.ButtonRole.AcceptRole)
            warn_box.addButton("المتابعة على أي حال" if self.lang == "ar" else "Continue Anyway", QMessageBox.ButtonRole.RejectRole)
            warn_box.setDefaultButton(btn_choose)
            warn_box.exec()

            if warn_box.clickedButton() == btn_choose:
                self.browse_dest_path()
                new_dest = self.txt_dest.text().strip()
                if os.path.splitdrive(os.path.abspath(new_dest))[0].upper() == src_drive:
                    return
                target_dir = new_dest

        try:
            os.makedirs(target_dir, exist_ok=True)
            prog = QProgressDialog(
                "جاري استعادة الملفات بأمان..." if self.lang == "ar" else "Recovering selected files safely...",
                "إلغاء" if self.lang == "ar" else "Cancel",
                0, len(selected), self
            )
            prog.setWindowModality(Qt.WindowModality.WindowModal)
            prog.setMinimumDuration(150)

            success_count = 0
            for idx, f in enumerate(selected):
                if prog.wasCanceled():
                    break
                ok, _ = restore_file(f, target_dir)
                if ok:
                    success_count += 1
                if idx % 10 == 0 or idx == len(selected) - 1:
                    prog.setValue(idx + 1)
                    QApplication.processEvents()
            prog.close()

            done_box = QMessageBox(self)
            done_box.setIcon(QMessageBox.Icon.Information)
            done_box.setWindowTitle("اكتملت الاستعادة بنجاح" if self.lang == "ar" else "Recovery Complete")
            done_box.setText(
                f"تم استرجاع {success_count} من أصل {len(selected)} ملف بنجاح!\nالمسار: {target_dir}"
                if self.lang == "ar" else
                f"Successfully recovered {success_count} of {len(selected)} files!\nSaved to: {target_dir}"
            )
            btn_open = done_box.addButton("📂 فتح مجلد الملفات المسترجعة" if self.lang == "ar" else "📂 Open Recovered Folder", QMessageBox.ButtonRole.AcceptRole)
            done_box.addButton("إغلاق" if self.lang == "ar" else "Close", QMessageBox.ButtonRole.RejectRole)
            done_box.exec()
            if done_box.clickedButton() == btn_open:
                try:
                    os.startfile(target_dir)
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Recovery Error", f"Failed to restore files: {str(e)}")

    def open_full_preview(self):
        r = self.table.currentRow()
        if r < 0:
            return
        name_it = self.table.item(r, 0)
        if not name_it:
            return
        f = name_it.data(Qt.ItemDataRole.UserRole)
        if not f:
            return
        dlg = PreviewHexDialog(f, lang=self.lang, parent=self)
        dlg.exec()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.setText((" " + self.strings["btn_resume"]) if self.is_paused else (" " + self.strings["btn_pause"]))
        self.btn_pause.setIcon(get_ui_icon("ui_resume.png") if self.is_paused else get_ui_icon("ui_pause.png"))
        if self.scanner_instance and hasattr(self.scanner_instance, "is_paused"):
            self.scanner_instance.is_paused = self.is_paused
        if self.is_paused:
            self.lbl_live_searching.setText("⏸ تم إيقاف الفحص مؤقتاً — اضغط استئناف للمتابعة" if self.lang == "ar" else "⏸ Scan Paused — Click Resume to continue")
            self.spinner_widget.set_paused(True)
        else:
            self.lbl_live_searching.setText("🔎 جاري استئناف الفحص..." if self.lang == "ar" else "🔎 Resuming scan...")
            self.spinner_widget.set_paused(False)

    def stop_scan(self):
        self.is_paused = False
        if self.scanner_instance and hasattr(self.scanner_instance, "stop"):
            self.scanner_instance.stop()
        self.spinner_widget.set_stopped()
        self.lbl_live_searching.setText("تم إيقاف الفحص بواسطة المستخدم." if self.lang == "ar" else "Scan stopped by user.")
        self.btn_pause.setVisible(False)
        self.btn_stop.setVisible(False)

    @staticmethod
    def format_bytes(b: int) -> str:
        if b < 1024: return f"{b} B"
        elif b < 1024 * 1024: return f"{b / 1024:.2f} KB"
        elif b < 1024 * 1024 * 1024: return f"{b / (1024 * 1024):.2f} MB"
        else: return f"{b / (1024 * 1024 * 1024):.2f} GB"
