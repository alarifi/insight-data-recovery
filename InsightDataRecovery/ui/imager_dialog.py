"""
Insight Data Recovery Studio Pro - ChronoSnap Disk Image & Safe Clone View v5.0
Full Light/Dark theme parity, non-blocking background cloning thread, and Arabic/English localization.
"""
import threading
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QComboBox, QLineEdit, QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from engine.disk_scanner import enumerate_logical_drives
from engine.disk_imager import DiskImager
from ui.theme import STRINGS


class ImagerSignals(QObject):
    progress = pyqtSignal(int, str, float)
    finished = pyqtSignal(bool, str)


class ChronoSnapView(QWidget):
    def __init__(self, lang: str = "en", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.lang = lang
        self.strings = STRINGS[lang]
        self.drives = []
        self.imager_instance: Optional[DiskImager] = None
        self.signals = ImagerSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        self.setup_ui()
        self.load_drives()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 16, 22, 16)
        main_layout.setSpacing(12)

        self.lbl_title = QLabel("ChronoSnap Disk Image & Safe Clone" if self.lang == "en" else "صورة القرص الآمنة (ChronoSnap Backup & Clone)")
        self.lbl_title.setObjectName("PageTitle")
        main_layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(
            "Create a bit-for-bit raw image (.img / .raw) of any failing drive or partition to recover data safely."
            if self.lang == "en" else
            "إنشاء صورة قطاعية خام متطابقة (Bit-by-Bit Image) لأي قرص أو فلاشة معرضة للتلف لاستعادة البيانات منها بأمان تام."
        )
        self.lbl_desc.setObjectName("MutedLabel")
        self.lbl_desc.setWordWrap(True)
        main_layout.addWidget(self.lbl_desc)

        # 3 Features Card
        features_card = QFrame()
        features_card.setObjectName("Card")
        feat_layout = QVBoxLayout(features_card)
        feat_layout.setContentsMargins(16, 12, 16, 12)
        feat_layout.setSpacing(10)

        self.feat_rows = []
        self._build_feature_rows(feat_layout)
        main_layout.addWidget(features_card)

        # Source & Destination Card
        form_card = QFrame()
        form_card.setObjectName("Card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(10)

        row1 = QHBoxLayout()
        self.lbl_src = QLabel("Source Drive to Clone:" if self.lang == "en" else "القرص المستهدف للاستنساخ:")
        self.lbl_src.setObjectName("CardTitle")
        row1.addWidget(self.lbl_src)

        self.cmb_src_drive = QComboBox()
        self.cmb_src_drive.setMinimumWidth(300)
        row1.addWidget(self.cmb_src_drive)
        row1.addStretch()
        form_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.lbl_dst = QLabel("Save Disk Image (.img) to:" if self.lang == "en" else "مسار حفظ ملف الصورة (.img):")
        self.lbl_dst.setObjectName("CardTitle")
        row2.addWidget(self.lbl_dst)

        self.txt_output_path = QLineEdit()
        self.txt_output_path.setPlaceholderText("Select destination file path..." if self.lang == "en" else "اختر مسار حفظ ملف الصورة...")
        row2.addWidget(self.txt_output_path, 1)

        self.btn_browse = QPushButton(self.strings["btn_browse"])
        self.btn_browse.setObjectName("SecondaryActionBtn")
        self.btn_browse.clicked.connect(self.browse_destination)
        row2.addWidget(self.btn_browse)
        form_layout.addLayout(row2)

        main_layout.addWidget(form_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("AccentLabel")
        main_layout.addWidget(self.lbl_status)

        # Start Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_start = QPushButton("💾  " + ("Start ChronoSnap Image Creation" if self.lang == "en" else "بدء إنشاء صورة القرص الآن"))
        self.btn_start.setObjectName("PrimaryActionBtn")
        self.btn_start.clicked.connect(self.start_imaging)
        btn_layout.addWidget(self.btn_start)

        main_layout.addLayout(btn_layout)
        main_layout.addStretch()

    def _build_feature_rows(self, layout: QVBoxLayout):
        items_ar = [
            ("🛡️ حماية قطاعية تلقائية (Automatic Protection)", "استنساخ قطاعي ذكي يعمل في الخلفية بأمان دون تعطيل عملك."),
            ("⏱️ استرجاع نقطة زمنية (Point-in-Time Imaging)", "استرجاع الملفات من أي لقطة تاريخية مع مطابقة البايتات بنسبة 100%."),
            ("⚡ تجاوز القطاعات التالفة (Bad Sector Tolerance)", "تخطي القطاعات المعطوبة وتصفيرها بأمان لمنع انهيار القرص الفيزيائي.")
        ]
        items_en = [
            ("🛡️ Automatic Protection", "Smart continuous raw backup operating safely in the background."),
            ("⏱️ Point-in-Time Sector Imaging", "Restore files from any historical snapshot with bit-level integrity."),
            ("⚡ Bad Sector Fault Tolerance", "Intelligently skips and pads unreadable sectors to salvage surviving clusters.")
        ]
        for t, d in (items_ar if self.lang == "ar" else items_en):
            row = QVBoxLayout()
            row.setSpacing(2)
            lbl_t = QLabel(t)
            lbl_t.setObjectName("CardTitle")
            lbl_d = QLabel(d)
            lbl_d.setObjectName("MutedLabel")
            row.addWidget(lbl_t)
            row.addWidget(lbl_d)
            layout.addLayout(row)
            self.feat_rows.append((lbl_t, lbl_d))

    def set_language(self, lang: str):
        self.lang = lang
        self.strings = STRINGS[lang]
        self.lbl_title.setText("ChronoSnap Disk Image & Safe Clone" if lang == "en" else "صورة القرص الآمنة (ChronoSnap Backup & Clone)")
        self.lbl_desc.setText(
            "Create a bit-for-bit raw image (.img / .raw) of any failing drive or partition to recover data safely."
            if lang == "en" else
            "إنشاء صورة قطاعية خام متطابقة (Bit-by-Bit Image) لأي قرص أو فلاشة معرضة للتلف لاستعادة البيانات منها بأمان تام."
        )
        self.lbl_src.setText("Source Drive to Clone:" if lang == "en" else "القرص المستهدف للاستنساخ:")
        self.lbl_dst.setText("Save Disk Image (.img) to:" if lang == "en" else "مسار حفظ ملف الصورة (.img):")
        self.btn_browse.setText(self.strings["btn_browse"])
        self.btn_start.setText("💾  " + ("Start ChronoSnap Image Creation" if lang == "en" else "بدء إنشاء صورة القرص الآن"))

    def load_drives(self):
        self.drives = enumerate_logical_drives()
        self.cmb_src_drive.clear()
        for d in self.drives:
            self.cmb_src_drive.addItem(f"{d.letter} [{d.label}] ({d.total_gb} GB - {d.fs_type})", d.letter)

    def browse_destination(self):
        fpath, _ = QFileDialog.getSaveFileName(self, "Save Raw Disk Image", "Disk_Backup.img", "Raw Disk Image (*.img *.raw *.bin)")
        if fpath:
            self.txt_output_path.setText(fpath)

    def start_imaging(self):
        src_letter = self.cmb_src_drive.currentData()
        dst_path = self.txt_output_path.text().strip()

        if not dst_path:
            QMessageBox.warning(
                self,
                "لم يتم تحديد المسار" if self.lang == "ar" else "No Destination",
                "يرجى اختيار مسار حفظ ملف صورة القرص أولاً." if self.lang == "ar" else "Please choose where to save the disk image file."
            )
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(5)
        self.btn_start.setEnabled(False)
        self.lbl_status.setText("Initializing sector cloner..." if self.lang == "en" else "جاري تهيئة مستنسخ القطاعات...")

        def _worker():
            imager = DiskImager(source_drive=src_letter, output_image_path=dst_path)
            self.imager_instance = imager
            ok = imager.create_image(progress_callback=lambda pct, msg, spd: self.signals.progress.emit(pct, msg, spd))
            self.signals.finished.emit(ok, dst_path)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress(self, pct: int, msg: str, speed: float):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"{msg}  •  {speed:.1f} MB/s")

    def _on_finished(self, ok: bool, dst_path: str):
        self.btn_start.setEnabled(True)
        self.progress_bar.setValue(100 if ok else 0)
        if ok:
            self.lbl_status.setText("✅ Disk image created successfully!" if self.lang == "en" else "✅ تم إنشاء صورة القرص بنجاح!")
            QMessageBox.information(self, "Image Complete", f"Disk image successfully created at:\n{dst_path}")
        else:
            self.lbl_status.setText("❌ Imaging requires Administrator privileges." if self.lang == "en" else "❌ يتطلب الاستنساخ القطاعي تشغيل البرنامج كمسؤول (Administrator).")
            QMessageBox.warning(self, "Imaging Notice", "Raw sector cloning requires Administrator privileges on Windows.")
