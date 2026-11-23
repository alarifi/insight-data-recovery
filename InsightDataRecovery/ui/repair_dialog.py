"""
Insight Data Recovery Studio Pro - Intelligent File Repair Center v5.0
Full Light/Dark theme parity, real Drag & Drop support, supported format badges,
background repair thread, and Arabic/English localization.
"""
import os
import threading
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QProgressBar, QMessageBox, QFrame, QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

from repair.office_repair import repair_office_file
from repair.image_repair import repair_image_file
from repair.video_repair import repair_video_file, resolve_ffmpeg_path
from repair.pdf_repair import repair_pdf_file
from repair.audio_repair import repair_audio_file
from ui.theme import STRINGS, get_asset_path


class RepairSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str, str)


class FileRepairView(QWidget):
    def __init__(self, lang: str = "en", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.lang = lang
        self.strings = STRINGS[lang]
        self.selected_corrupt_file: Optional[str] = None
        self.selected_sample_video: Optional[str] = None
        self.signals = RepairSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        self.setAcceptDrops(True)
        self.setup_ui()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            fpath = urls[0].toLocalFile()
            if fpath and os.path.isfile(fpath):
                self.selected_corrupt_file = fpath
                self.lbl_selected_path.setText(f"✅ {os.path.basename(fpath)}")

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 16, 22, 16)
        main_layout.setSpacing(12)

        # Header
        self.lbl_title = QLabel(self.strings["repair_title"])
        self.lbl_title.setObjectName("PageTitle")
        main_layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(self.strings["repair_desc"])
        self.lbl_desc.setObjectName("MutedLabel")
        main_layout.addWidget(self.lbl_desc)

        # Supported Formats Strip
        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(6)
        for badge_txt, col in [
            ("📄 DOCX / XLSX / PPTX", "#2563EB"),
            ("📕 PDF", "#DC2626"),
            ("🖼️ JPG / PNG / BMP", "#0891B2"),
            ("🎬 MP4 / MOV / AVI", "#7C3AED"),
            ("🎵 MP3 / WAV", "#059669"),
        ]:
            b = QLabel(badge_txt)
            b.setStyleSheet(f"background: {col}; color: #FFFFFF; border-radius: 5px; padding: 3px 9px; font-size: 10px; font-weight: 700;")
            fmt_row.addWidget(b)
        fmt_row.addStretch()
        ff_ok = bool(resolve_ffmpeg_path())
        self.lbl_ffmpeg_badge = QLabel("🟢 FFmpeg Engine Ready" if ff_ok else "⚙️ Structural Repair Mode")
        self.lbl_ffmpeg_badge.setStyleSheet(
            "background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; border-radius: 5px; padding: 3px 9px; font-size: 10px; font-weight: 700;"
            if ff_ok else
            "background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; border-radius: 5px; padding: 3px 9px; font-size: 10px; font-weight: 700;"
        )
        fmt_row.addWidget(self.lbl_ffmpeg_badge)
        main_layout.addLayout(fmt_row)

        # Drop Zone Card (Theme-aware via objectName!)
        drop_card = QFrame()
        drop_card.setObjectName("DropZoneCard")
        drop_layout = QVBoxLayout(drop_card)
        drop_layout.setContentsMargins(20, 18, 20, 18)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.setSpacing(10)

        shield_path = get_asset_path("shield_3d.png")
        lbl_icon = QLabel()
        if os.path.exists(shield_path):
            lbl_icon.setPixmap(QPixmap(shield_path).scaled(52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(lbl_icon)

        self.lbl_selected_path = QLabel(
            "Select or drag & drop a corrupted file here"
            if self.lang == "en" else
            "اختر أو اسحب الملف التالف وأفلته هنا لبدء ترقيع البايتات وترميمه"
        )
        self.lbl_selected_path.setObjectName("CardTitle")
        self.lbl_selected_path.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(self.lbl_selected_path)

        self.btn_browse = QPushButton("📂  " + self.strings["btn_select_repair_file"])
        self.btn_browse.setObjectName("PrimaryActionBtn")
        self.btn_browse.setMaximumWidth(280)
        self.btn_browse.clicked.connect(self.browse_corrupt_file)
        drop_layout.addWidget(self.btn_browse, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(drop_card)

        # Advanced Repair Options Card
        options_card = QFrame()
        options_card.setObjectName("Card")
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(16, 12, 16, 12)
        options_layout.setSpacing(9)

        self.lbl_opt_title = QLabel("Advanced Repair Settings:" if self.lang == "en" else "خيارات الترميم المتقدمة:")
        self.lbl_opt_title.setObjectName("CardTitle")
        options_layout.addWidget(self.lbl_opt_title)

        self.chk_ai_upscale = QCheckBox(
            "Apply AI Super-Resolution && Face Restoration (Real-ESRGAN)"
            if self.lang == "en" else
            "تفعيل الترميم البصري الفائق بالذكاء الاصطناعي للصور (AI Upscaling && Face Restoration)"
        )
        options_layout.addWidget(self.chk_ai_upscale)

        sample_layout = QHBoxLayout()
        self.lbl_sample = QLabel("Reference Video (MP4/MOV moov):" if self.lang == "en" else "فيديو عينة سليم (لترقيع moov atom):")
        self.lbl_sample.setObjectName("MutedLabel")
        sample_layout.addWidget(self.lbl_sample)

        self.txt_sample_path = QLineEdit()
        self.txt_sample_path.setPlaceholderText("Optional healthy reference video from same device..." if self.lang == "en" else "اختياري: ملف فيديو سليم تم تصويره بنفس الكاميرا أو الهاتف...")
        sample_layout.addWidget(self.txt_sample_path, 1)

        self.btn_browse_sample = QPushButton(self.strings["btn_browse"])
        self.btn_browse_sample.setObjectName("SecondaryActionBtn")
        self.btn_browse_sample.clicked.connect(self.browse_sample_video)
        sample_layout.addWidget(self.btn_browse_sample)

        options_layout.addLayout(sample_layout)
        main_layout.addWidget(options_card)

        # Progress & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("AccentLabel")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.lbl_status)

        # Start Repair Action Button
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.btn_repair = QPushButton("🛠️  " + self.strings["btn_start_repair"])
        self.btn_repair.setObjectName("SuccessActionBtn")
        self.btn_repair.clicked.connect(self.execute_repair)
        action_layout.addWidget(self.btn_repair)

        action_layout.addStretch()
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

    def set_language(self, lang: str):
        self.lang = lang
        self.strings = STRINGS[lang]
        self.lbl_title.setText(self.strings["repair_title"])
        self.lbl_desc.setText(self.strings["repair_desc"])
        if not self.selected_corrupt_file:
            self.lbl_selected_path.setText(
                "Select or drag & drop a corrupted file here"
                if lang == "en" else
                "اختر أو اسحب الملف التالف وأفلته هنا لبدء ترقيع البايتات وترميمه"
            )
        self.btn_browse.setText("📂  " + self.strings["btn_select_repair_file"])
        self.lbl_opt_title.setText("Advanced Repair Settings:" if lang == "en" else "خيارات الترميم المتقدمة:")
        self.chk_ai_upscale.setText(
            "Apply AI Super-Resolution & Face Restoration (Real-ESRGAN)"
            if lang == "en" else
            "تفعيل الترميم البصري الفائق بالذكاء الاصطناعي للصور (AI Upscaling & Face Restoration)"
        )
        self.lbl_sample.setText("Reference Video (MP4/MOV moov):" if lang == "en" else "فيديو عينة سليم (لترقيع moov atom):")
        self.btn_browse_sample.setText(self.strings["btn_browse"])
        self.btn_repair.setText("🛠️  " + self.strings["btn_start_repair"])

    def browse_corrupt_file(self):
        file_filter = (
            "All Supported Formats (*.docx *.xlsx *.pptx *.pdf *.jpg *.jpeg *.png *.bmp *.mp4 *.mov *.avi *.mp3 *.wav);;"
            "Office Documents (*.docx *.xlsx *.pptx);;"
            "Images (*.jpg *.jpeg *.png *.bmp);;"
            "Videos (*.mp4 *.mov *.avi);;"
            "PDF Files (*.pdf);;"
            "Audio (*.mp3 *.wav);;"
            "All Files (*.*)"
        )
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Damaged File", "", file_filter)
        if fpath:
            self.selected_corrupt_file = fpath
            self.lbl_selected_path.setText(f"✅ {os.path.basename(fpath)}")

    def browse_sample_video(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Reference Sample Video", "", "Video Files (*.mp4 *.mov *.avi)")
        if fpath:
            self.selected_sample_video = fpath
            self.txt_sample_path.setText(fpath)

    def execute_repair(self):
        if not self.selected_corrupt_file or not os.path.exists(self.selected_corrupt_file):
            QMessageBox.warning(
                self,
                "لم يتم اختيار ملف" if self.lang == "ar" else "No File Selected",
                "يرجى اختيار ملف تالف للترميم أولاً." if self.lang == "ar" else "Please select a corrupted file to repair first."
            )
            return

        src_file = self.selected_corrupt_file
        ext = os.path.splitext(src_file)[1].lower()
        base = os.path.splitext(src_file)[0]
        output_path = f"{base}_Repaired{ext}"
        apply_ai = self.chk_ai_upscale.isChecked()
        sample_p = self.txt_sample_path.text().strip() or None

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        self.btn_repair.setEnabled(False)
        self.lbl_status.setText("Analyzing structural byte corruption..." if self.lang == "en" else "جاري تحليل التلف وتفكيك الهيكل الداخلي...")

        def _worker():
            self.signals.progress.emit(55, "Reconstructing headers & streams..." if self.lang == "en" else "جاري إعادة بناء الترويسات والجداول الداخلية...")
            if ext in (".docx", ".xlsx", ".pptx"):
                ok, msg = repair_office_file(src_file, output_path)
            elif ext in (".jpg", ".jpeg", ".png", ".bmp"):
                ok, msg = repair_image_file(src_file, output_path, apply_ai_upscale=apply_ai)
            elif ext in (".mp4", ".mov", ".avi", ".mkv"):
                ok, msg = repair_video_file(src_file, output_path, sample_video_path=sample_p)
            elif ext == ".pdf":
                ok, msg = repair_pdf_file(src_file, output_path)
            elif ext in (".mp3", ".wav", ".m4a", ".aac"):
                ok, msg = repair_audio_file(src_file, output_path)
            else:
                ok, msg = False, "Unsupported file format for structural repair."
            self.signals.finished.emit(ok, msg, output_path)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress(self, val: int, text: str):
        self.progress_bar.setValue(val)
        self.lbl_status.setText(text)

    def _on_finished(self, ok: bool, msg: str, output_path: str):
        self.progress_bar.setValue(100)
        self.btn_repair.setEnabled(True)
        if ok:
            self.lbl_status.setText("Repair Complete!" if self.lang == "en" else "✅ تمت عملية الإصلاح بنجاح!")
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("تم الإصلاح بنجاح" if self.lang == "ar" else "Repair Successful")
            box.setText(msg)
            btn_open = box.addButton("📂 فتح مجلد الملف المرمم" if self.lang == "ar" else "📂 Open Repaired Folder", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("إغلاق" if self.lang == "ar" else "Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == btn_open:
                try:
                    os.startfile(os.path.dirname(os.path.abspath(output_path)))
                except Exception:
                    pass
        else:
            self.lbl_status.setText("Repair Failed" if self.lang == "en" else "❌ تعذر الإصلاح")
            QMessageBox.critical(self, "فشل الإصلاح" if self.lang == "ar" else "Repair Failed", msg)
