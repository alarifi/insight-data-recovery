"""
Insight Data Recovery Studio Pro - Lost Partition Rescue View v5.0
Full Light/Dark theme parity, background scanning thread, zero hardcoded colors,
and full Arabic/English localization.
"""
import threading
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject

from engine.disk_scanner import enumerate_physical_disks
from engine.partition_rescue import PartitionRescueScanner, LostPartitionInfo
from ui.theme import STRINGS


class PartitionSignals(QObject):
    progress = pyqtSignal(int, str, int)
    finished = pyqtSignal(list)


class PartitionRescueView(QWidget):
    open_partition_scan = pyqtSignal(str)

    def __init__(self, lang: str = "en", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.lang = lang
        self.strings = STRINGS[lang]
        self.physical_disks = []
        self.discovered_partitions: List[LostPartitionInfo] = []
        self.scanner_instance: Optional[PartitionRescueScanner] = None
        self.signals = PartitionSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.finished.connect(self._on_finished)

        self.setup_ui()
        self.load_physical_disks()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 16, 22, 16)
        main_layout.setSpacing(12)

        self.lbl_title = QLabel(self.strings["partition_title"])
        self.lbl_title.setObjectName("PageTitle")
        main_layout.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(self.strings["partition_desc"])
        self.lbl_desc.setObjectName("MutedLabel")
        main_layout.addWidget(self.lbl_desc)

        # 3 Mode Cards (Theme-aware)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.c1_title, self.c1_sub, c1 = self.create_feature_card(
            "🧩  " + ("Partition Missing" if self.lang == "en" else "قسم مفقود أو محذوف"),
            "Recover partitions showing as Unallocated Space or RAW" if self.lang == "en" else "استرجاع الأقسام التي تظهر كمساحة غير مخصصة (Unallocated) أو RAW"
        )
        cards_layout.addWidget(c1)

        self.c2_title, self.c2_sub, c2 = self.create_feature_card(
            "🚫  " + ("Partition Cannot Be Opened" if self.lang == "en" else "قسم يتعذر فتحه"),
            "Fix partitions displaying Access Denied or Format Required" if self.lang == "en" else "معالجة الأقسام التي تطلب التهيئة الفورية (Format Required) أو رفض الوصول"
        )
        cards_layout.addWidget(c2)

        self.c3_title, self.c3_sub, c3 = self.create_feature_card(
            "🔒  " + ("BitLocker Damaged" if self.lang == "en" else "بارتشن BitLocker متضرر"),
            "Repair lost or corrupted BitLocker encrypted partitions" if self.lang == "en" else "إنقاذ واستعادة أقسام BitLocker المشفرة المفقودة أو المتضررة"
        )
        cards_layout.addWidget(c3)
        main_layout.addLayout(cards_layout)

        # Physical Disk Selector Card
        sel_card = QFrame()
        sel_card.setObjectName("Card")
        select_layout = QHBoxLayout(sel_card)
        select_layout.setContentsMargins(14, 10, 14, 10)
        select_layout.setSpacing(10)

        self.lbl_disk = QLabel("Physical Hard Drive:" if self.lang == "en" else "القرص الصلب الفيزيائي:")
        self.lbl_disk.setObjectName("CardTitle")
        select_layout.addWidget(self.lbl_disk)

        self.cmb_disks = QComboBox()
        self.cmb_disks.setMinimumWidth(320)
        select_layout.addWidget(self.cmb_disks, 1)

        self.btn_scan = QPushButton("🔍  " + self.strings["btn_scan_partitions"])
        self.btn_scan.setObjectName("PrimaryActionBtn")
        self.btn_scan.clicked.connect(self.start_partition_scan)
        select_layout.addWidget(self.btn_scan)

        main_layout.addWidget(sel_card)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.lbl_scan_status = QLabel("")
        self.lbl_scan_status.setObjectName("AccentLabel")
        main_layout.addWidget(self.lbl_scan_status)

        # Discovered Partitions Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self._update_headers()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.table, 1)

        # Bottom Action Bar
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.btn_recover_partition = QPushButton(
            "Search Files in Lost Partition →" if self.lang == "en" else "فحص واستخراج الملفات من هذا البارتشن ←"
        )
        self.btn_recover_partition.setObjectName("PrimaryActionBtn")
        self.btn_recover_partition.clicked.connect(self.explore_selected_partition)
        bottom_layout.addWidget(self.btn_recover_partition)

        main_layout.addLayout(bottom_layout)

    def _update_headers(self):
        headers = (
            ["Partition Label", "Filesystem", "Size", "Start Sector (LBA)", "Status"]
            if self.lang == "en" else
            ["اسم البارتشن المكتشف", "نظام الملفات", "الحجم", "قطاع البداية (LBA)", "الحالة"]
        )
        self.table.setHorizontalHeaderLabels(headers)

    def set_language(self, lang: str):
        self.lang = lang
        self.strings = STRINGS[lang]
        self.lbl_title.setText(self.strings["partition_title"])
        self.lbl_desc.setText(self.strings["partition_desc"])
        self.c1_title.setText("🧩  " + ("Partition Missing" if lang == "en" else "قسم مفقود أو محذوف"))
        self.c1_sub.setText("Recover partitions showing as Unallocated Space or RAW" if lang == "en" else "استرجاع الأقسام التي تظهر كمساحة غير مخصصة (Unallocated) أو RAW")
        self.c2_title.setText("🚫  " + ("Partition Cannot Be Opened" if lang == "en" else "قسم يتعذر فتحه"))
        self.c2_sub.setText("Fix partitions displaying Access Denied or Format Required" if lang == "en" else "معالجة الأقسام التي تطلب التهيئة الفورية (Format Required) أو رفض الوصول")
        self.c3_title.setText("🔒  " + ("BitLocker Damaged" if lang == "en" else "بارتشن BitLocker متضرر"))
        self.c3_sub.setText("Repair lost or corrupted BitLocker encrypted partitions" if lang == "en" else "إنقاذ واستعادة أقسام BitLocker المشفرة المفقودة أو المتضررة")
        self.lbl_disk.setText("Physical Hard Drive:" if lang == "en" else "القرص الصلب الفيزيائي:")
        self.btn_scan.setText("🔍  " + self.strings["btn_scan_partitions"])
        self.btn_recover_partition.setText("Search Files in Lost Partition →" if lang == "en" else "فحص واستخراج الملفات من هذا البارتشن ←")
        self._update_headers()

    def create_feature_card(self, title: str, subtitle: str):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("CardTitle")
        layout.addWidget(lbl_t)

        lbl_s = QLabel(subtitle)
        lbl_s.setObjectName("MutedLabel")
        lbl_s.setWordWrap(True)
        layout.addWidget(lbl_s)

        return lbl_t, lbl_s, card

    def load_physical_disks(self):
        self.physical_disks = enumerate_physical_disks()
        self.cmb_disks.clear()
        for d in self.physical_disks:
            self.cmb_disks.addItem(f"{d['name']} ({d['size_gb']} GB) — {d['device_path']}", d)

    def start_partition_scan(self):
        idx = self.cmb_disks.currentIndex()
        if idx < 0:
            return
        disk_data = self.cmb_disks.itemData(idx)
        disk_num = disk_data.get("number", 0)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        self.btn_scan.setEnabled(False)
        self.lbl_scan_status.setText(f"Scanning MBR/GPT sectors on PhysicalDrive{disk_num}...")

        def _worker():
            scanner = PartitionRescueScanner(disk_number=disk_num)
            self.scanner_instance = scanner
            parts = scanner.scan_disk(progress_callback=lambda pct, st, cnt: self.signals.progress.emit(pct, st, cnt))
            self.signals.finished.emit(parts)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_progress(self, pct: int, status: str, found_cnt: int):
        self.progress_bar.setValue(pct)
        self.lbl_scan_status.setText(f"{status}  |  Discovered: {found_cnt}")

    def _on_finished(self, parts: list):
        self.progress_bar.setValue(100)
        self.btn_scan.setEnabled(True)
        self.discovered_partitions = parts
        self.populate_partitions_table()

    def populate_partitions_table(self):
        self.table.setRowCount(len(self.discovered_partitions))
        for row, p in enumerate(self.discovered_partitions):
            self.table.setItem(row, 0, QTableWidgetItem(p.label))
            self.table.setItem(row, 1, QTableWidgetItem(p.fs_type))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p.capacity_gb:.2f} GB"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p.start_sector:,}"))
            self.table.setItem(row, 4, QTableWidgetItem(p.status))

        if not self.discovered_partitions:
            self.lbl_scan_status.setText("✓ الفحص مكتمل: كافة الأقسام على هذا القرص سليمة ومقروءة." if self.lang == "ar" else "✓ Scan complete: All partitions healthy on this physical disk.")

    def explore_selected_partition(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(
                self,
                "اختر بارتشن" if self.lang == "ar" else "Select Partition",
                "يرجى تحديد بارتشن من الجدول أولاً." if self.lang == "ar" else "Please select a partition from the table first."
            )
            return
        p = self.discovered_partitions[rows[0].row()]
        self.open_partition_scan.emit(p.label)
