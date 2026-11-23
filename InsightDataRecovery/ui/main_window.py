"""
Insight Data Recovery Studio Pro - Commercial Main Window v5.0
Matches and surpasses EaseUS Data Recovery Wizard Professional:
- Clean RTL Arabic & LTR English native layout
- Seamless Light & Dark themes across all pages & dialogs
- Dedicated Hardware Disks, SD Card/USB, Folder Scan, Format Recovery, File Repair, Lost Partition Rescue, ChronoSnap Disk Image
- Sidebar icons + golden PRO badge + clean header (Save Session, Load Session, Settings Center)
"""
import os
import sys
import ctypes
import threading
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QCheckBox, QRadioButton, QButtonGroup,
    QStackedWidget, QFileDialog, QMessageBox, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QPixmap

from engine.disk_scanner import enumerate_logical_drives, DriveInfo, DRIVE_REMOVABLE
from engine.undelete_engine import UndeleteScanner
from engine.ntfs_mft_scanner import is_admin
from engine.format_engine import FormatRecoveryEngine
from engine.session_manager import save_scan_session, load_scan_session
from engine.signatures import CAT_GRAPHICS, CAT_DOCUMENTS, CAT_VIDEO, CAT_AUDIO, CAT_ARCHIVES, CAT_DATABASE
from ui.theme import STRINGS, get_light_stylesheet, get_dark_stylesheet, get_asset_path, get_ui_icon
from ui.scan_view import ScanView
from ui.repair_dialog import FileRepairView
from ui.partition_dialog import PartitionRescueView
from ui.imager_dialog import ChronoSnapView


class ScanWorkerSignals(QObject):
    progress = pyqtSignal(object, str, int, float)
    finished = pyqtSignal(list)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self.is_dark = False
        self.strings = STRINGS[self.lang]
        self.drives: List[DriveInfo] = []
        self.selected_target: Optional[str] = None
        self.selected_target_type: str = "drive"
        self.filter_removable_only = False
        self.worker_signals = ScanWorkerSignals()
        self.drive_cards = []

        self.setup_window()
        self.setup_ui()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight)
        self.apply_theme()
        self.refresh_drives()

    def setup_window(self):
        self.setWindowTitle(self.strings["app_title"])
        self.resize(1060, 620)
        self.setMinimumSize(960, 560)

        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_h_layout = QHBoxLayout(central_widget)
        self.main_h_layout.setContentsMargins(0, 0, 0, 0)
        self.main_h_layout.setSpacing(0)

        # 1. Commercial Sidebar (Width 218px)
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(218)
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 14, 0, 12)
        self.sidebar_layout.setSpacing(2)

        # Brand / Logo + PRO Badge
        brand_layout = QHBoxLayout()
        brand_layout.setContentsMargins(14, 0, 14, 10)
        brand_layout.setSpacing(7)

        lbl_logo = QLabel()
        shield_path = get_asset_path("shield_3d.png")
        if os.path.exists(shield_path):
            lbl_logo.setPixmap(QPixmap(shield_path).scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        brand_layout.addWidget(lbl_logo)

        lbl_app_name = QLabel("Insight Recovery")
        lbl_app_name.setStyleSheet("font-size: 14px; font-weight: 800; color: #0D6EFD;")
        brand_layout.addWidget(lbl_app_name)

        lbl_pro = QLabel("PRO")
        lbl_pro.setObjectName("ProBadge")
        brand_layout.addWidget(lbl_pro)
        brand_layout.addStretch()
        self.sidebar_layout.addLayout(brand_layout)

        # Section: Data Recovery
        self.lbl_sec_rec = QLabel(self.strings["sec_data_recovery"])
        self.lbl_sec_rec.setObjectName("SidebarSection")
        self.sidebar_layout.addWidget(self.lbl_sec_rec)

        self.btn_nav_hardware = self.create_sidebar_btn("💾  " + self.strings["nav_hardware_disk"], self.show_drives_view, active=True)
        self.btn_nav_sd = self.create_sidebar_btn("💳  " + self.strings["nav_sd_card"], self.show_sd_card_view)
        self.btn_nav_folder = self.create_sidebar_btn("📁  " + self.strings["nav_folder_scan"], self.pick_custom_folder)
        self.btn_nav_format = self.create_sidebar_btn("🔄  " + self.strings["nav_format_recovery"], self.activate_format_mode)

        # Section: Advanced Features
        self.lbl_sec_adv = QLabel(self.strings["sec_advanced"])
        self.lbl_sec_adv.setObjectName("SidebarSection")
        self.sidebar_layout.addWidget(self.lbl_sec_adv)

        self.btn_nav_repair = self.create_sidebar_btn("🛠️  " + self.strings["nav_file_repair"], self.show_repair_view)
        self.btn_nav_partition = self.create_sidebar_btn("🧩  " + self.strings["nav_lost_partition"], self.show_partition_view)

        # Section: Backup
        self.lbl_sec_bak = QLabel(self.strings["sec_backup"])
        self.lbl_sec_bak.setObjectName("SidebarSection")
        self.sidebar_layout.addWidget(self.lbl_sec_bak)

        self.btn_nav_backup = self.create_sidebar_btn("⏱️  " + self.strings["nav_disk_image"], self.show_backup_view)

        self.sidebar_layout.addStretch()

        if is_admin():
            self.lbl_admin_status = QLabel("🛡️ Admin NTFS $MFT Ready")
            self.lbl_admin_status.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 700; padding: 8px 14px;")
            self.sidebar_layout.addWidget(self.lbl_admin_status)
        else:
            self.btn_elevate_admin = QPushButton("🛡️ تشغيل كمسؤول ($MFT)" if self.lang == "ar" else "🛡️ Elevate Admin ($MFT)")
            self.btn_elevate_admin.setStyleSheet(
                "background: #FEF3C7; color: #B45309; border: 1px solid #F59E0B; "
                "border-radius: 7px; padding: 7px 10px; margin: 6px 10px; font-size: 11px; font-weight: 700;"
            )
            self.btn_elevate_admin.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_elevate_admin.setToolTip("Restart with Administrator privileges for deep raw NTFS $MFT & deleted/cut folder recovery")
            self.btn_elevate_admin.clicked.connect(self.relaunch_as_admin)
            self.sidebar_layout.addWidget(self.btn_elevate_admin)

        self.main_h_layout.addWidget(self.sidebar)

        # 2. Content Area
        self.content_widget = QWidget()
        content_v_layout = QVBoxLayout(self.content_widget)
        content_v_layout.setContentsMargins(0, 0, 0, 0)
        content_v_layout.setSpacing(0)

        # Clean Commercial Top Bar (Save Session, Load Session, Settings)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(18, 10, 18, 6)
        top_bar.setSpacing(8)

        self.lbl_top_info = QLabel(self.strings["app_subtitle"])
        self.lbl_top_info.setObjectName("SectionHeader")
        top_bar.addWidget(self.lbl_top_info)

        top_bar.addStretch()

        self.btn_save_session = QPushButton("💾 " + self.strings["btn_save_session"])
        self.btn_save_session.setObjectName("SecondaryActionBtn")
        self.btn_save_session.clicked.connect(self.save_current_session)
        top_bar.addWidget(self.btn_save_session)

        self.btn_load_session = QPushButton(" " + self.strings["btn_load_session"])
        self.btn_load_session.setIcon(get_ui_icon("ui_load_session.png"))
        self.btn_load_session.setIconSize(QSize(16, 16))
        self.btn_load_session.setObjectName("SecondaryActionBtn")
        self.btn_load_session.clicked.connect(self.load_session_flow)
        top_bar.addWidget(self.btn_load_session)

        self.btn_settings = QPushButton(" " + self.strings["btn_settings"])
        self.btn_settings.setIcon(get_ui_icon("ui_settings.png"))
        self.btn_settings.setIconSize(QSize(16, 16))
        self.btn_settings.setObjectName("SecondaryActionBtn")
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        top_bar.addWidget(self.btn_settings)

        content_v_layout.addLayout(top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()

        self.page_main = self.create_main_selection_page()
        self.stack.addWidget(self.page_main)

        self.page_scan = ScanView(lang=self.lang)
        self.page_scan.back_to_main.connect(self.show_drives_view)
        self.stack.addWidget(self.page_scan)

        self.page_repair = FileRepairView(lang=self.lang)
        self.stack.addWidget(self.page_repair)

        self.page_partition = PartitionRescueView(lang=self.lang)
        self.page_partition.open_partition_scan.connect(self.start_partition_scan_flow)
        self.stack.addWidget(self.page_partition)

        self.page_backup = ChronoSnapView(lang=self.lang)
        self.stack.addWidget(self.page_backup)

        # EaseUS-style full-width Scan View: automatically hide main sidebar when inspecting scan results
        self.stack.currentChanged.connect(lambda idx: self.sidebar.setVisible(idx != 1))

        content_v_layout.addWidget(self.stack, 1)
        self.main_h_layout.addWidget(self.content_widget, 1)

    def create_sidebar_btn(self, text: str, callback, active: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("NavBtn")
        btn.setProperty("active", "true" if active else "false")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        self.sidebar_layout.addWidget(btn)
        return btn

    def set_active_sidebar_btn(self, active_btn: QPushButton):
        for btn in [self.btn_nav_hardware, self.btn_nav_sd, self.btn_nav_folder,
                    self.btn_nav_format, self.btn_nav_repair, self.btn_nav_partition, self.btn_nav_backup]:
            btn.setProperty("active", "true" if btn == active_btn else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def create_main_selection_page(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 8, 20, 14)
        layout.setSpacing(10)

        # Title Row
        title_row = QHBoxLayout()
        self.lbl_select_title = QLabel(self.strings["select_location_title"])
        self.lbl_select_title.setObjectName("PageTitle")
        title_row.addWidget(self.lbl_select_title)

        btn_refresh = QPushButton("↻")
        btn_refresh.setObjectName("SecondaryActionBtn")
        btn_refresh.setFixedSize(28, 28)
        btn_refresh.setStyleSheet("padding: 0px; font-size: 16px; font-weight: 700; border-radius: 14px;")
        btn_refresh.setToolTip("Refresh drives")
        btn_refresh.clicked.connect(self.refresh_drives)
        title_row.addWidget(btn_refresh)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 1. Internal / Removable Drives Grid
        self.lbl_internal_drives = QLabel(self.strings["internal_drives"])
        self.lbl_internal_drives.setObjectName("SectionHeader")
        layout.addWidget(self.lbl_internal_drives)

        self.drives_grid = QGridLayout()
        self.drives_grid.setSpacing(10)
        layout.addLayout(self.drives_grid)

        # 2. Specify a Quick Location
        self.lbl_specify_loc = QLabel(self.strings["specify_location"])
        self.lbl_specify_loc.setObjectName("SectionHeader")
        layout.addWidget(self.lbl_specify_loc)

        quick_locs_layout = QHBoxLayout()
        quick_locs_layout.setSpacing(10)

        self.card_recycle = self.create_quick_location_card(
            self.strings["recycle_bin"],
            get_asset_path("recycle_3d.png"),
            "recycle"
        )
        quick_locs_layout.addWidget(self.card_recycle)

        self.card_desktop = self.create_quick_location_card(
            self.strings["desktop"],
            get_asset_path("desktop_3d.png"),
            "desktop"
        )
        quick_locs_layout.addWidget(self.card_desktop)

        self.card_folder = self.create_quick_location_card(
            self.strings["select_folder"],
            get_asset_path("folder_3d.png"),
            "folder"
        )
        quick_locs_layout.addWidget(self.card_folder)

        layout.addLayout(quick_locs_layout)

        # 3. File Types Filter Panel
        type_panel = QFrame()
        type_panel.setObjectName("Card")
        type_layout = QHBoxLayout(type_panel)
        type_layout.setContentsMargins(12, 8, 12, 8)
        type_layout.setSpacing(6)

        self.lbl_types_title = QLabel(self.strings["file_types_title"])
        self.lbl_types_title.setObjectName("SectionHeader")
        type_layout.addWidget(self.lbl_types_title)

        self.chk_graphics = QCheckBox(self.strings["cat_graphics"])
        self.chk_graphics.setChecked(True)
        type_layout.addWidget(self.chk_graphics)

        self.chk_docs = QCheckBox(self.strings["cat_documents"])
        self.chk_docs.setChecked(True)
        type_layout.addWidget(self.chk_docs)

        self.chk_video = QCheckBox(self.strings["cat_video"])
        self.chk_video.setChecked(True)
        type_layout.addWidget(self.chk_video)

        self.chk_audio = QCheckBox(self.strings["cat_audio"])
        self.chk_audio.setChecked(True)
        type_layout.addWidget(self.chk_audio)

        self.chk_archives = QCheckBox(self.strings["cat_archives"])
        self.chk_archives.setChecked(True)
        type_layout.addWidget(self.chk_archives)

        self.chk_database = QCheckBox(self.strings["cat_database"])
        self.chk_database.setChecked(True)
        type_layout.addWidget(self.chk_database)

        type_layout.addStretch()
        layout.addWidget(type_panel)

        layout.addStretch()

        # 4. Mode Selection & Primary Search Action Bar
        action_bar = QFrame()
        action_bar.setObjectName("Card")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(16, 10, 16, 10)
        action_layout.setSpacing(12)

        self.lbl_selected_target_disp = QLabel("Target: None")
        self.lbl_selected_target_disp.setObjectName("SectionHeader")
        action_layout.addWidget(self.lbl_selected_target_disp)

        action_layout.addStretch()

        self.rb_deleted = QRadioButton(self.strings["mode_deleted"])
        self.rb_deleted.setChecked(True)
        action_layout.addWidget(self.rb_deleted)

        self.rb_format = QRadioButton(self.strings["mode_format"])
        action_layout.addWidget(self.rb_format)

        mode_group = QButtonGroup(self)
        mode_group.addButton(self.rb_deleted)
        mode_group.addButton(self.rb_format)

        action_layout.addSpacing(6)

        self.btn_search = QPushButton("🔍  " + self.strings["btn_search"])
        self.btn_search.setObjectName("PrimaryActionBtn")
        self.btn_search.setMinimumWidth(190)
        self.btn_search.clicked.connect(self.start_recovery_scan)
        action_layout.addWidget(self.btn_search)

        layout.addWidget(action_bar)
        return container

    def create_quick_location_card(self, title: str, icon_path: str, loc_type: str) -> QFrame:
        card = QFrame()
        card.setObjectName("QuickCard")
        card.setFixedHeight(64)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if os.path.exists(icon_path):
            lbl_ico = QLabel()
            lbl_ico.setPixmap(QPixmap(icon_path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            layout.addWidget(lbl_ico)

        lbl_t = QLabel(title)
        lbl_t.setObjectName("CardTitle")
        lbl_t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.lbl_t = lbl_t
        layout.addWidget(lbl_t)

        card.mousePressEvent = lambda e: self.select_quick_location(card, loc_type)
        return card

    def select_quick_location(self, card: QFrame, loc_type: str):
        self.clear_drive_card_selections()
        self.card_recycle.setProperty("selected", "true" if loc_type == "recycle" else "false")
        self.card_desktop.setProperty("selected", "true" if loc_type == "desktop" else "false")
        self.card_folder.setProperty("selected", "true" if loc_type == "folder" else "false")

        for c in [self.card_recycle, self.card_desktop, self.card_folder]:
            c.style().unpolish(c)
            c.style().polish(c)

        self.selected_target_type = loc_type
        if loc_type == "desktop":
            self.selected_target = os.path.join(os.path.expanduser("~"), "Desktop")
            self.lbl_selected_target_disp.setText("🎯 " + self.strings["desktop"])
        elif loc_type == "recycle":
            self.selected_target = "C:\\$Recycle.Bin"
            self.lbl_selected_target_disp.setText("🎯 " + self.strings["recycle_bin"])
        elif loc_type == "folder":
            self.pick_custom_folder()

    def pick_custom_folder(self):
        fpath = QFileDialog.getExistingDirectory(self, "Select Specific Folder to Scan")
        if fpath:
            self.selected_target = os.path.normpath(fpath)
            self.selected_target_type = "folder"
            disp = fpath if len(fpath) < 36 else "..." + fpath[-33:]
            self.lbl_selected_target_disp.setText(f"🎯 {disp}")
            self.clear_drive_card_selections()
            self.card_folder.setProperty("selected", "true")
            self.card_folder.style().unpolish(self.card_folder)
            self.card_folder.style().polish(self.card_folder)
            self.filter_removable_only = False
            self.stack.setCurrentIndex(0)
            self.set_active_sidebar_btn(self.btn_nav_folder)

    def activate_format_mode(self):
        self.show_drives_view()
        self.rb_format.setChecked(True)
        self.set_active_sidebar_btn(self.btn_nav_format)

    def show_sd_card_view(self):
        self.filter_removable_only = True
        self.stack.setCurrentIndex(0)
        self.set_active_sidebar_btn(self.btn_nav_sd)
        self.lbl_internal_drives.setText(self.strings["removable_drives"])
        self.refresh_drives()

    def refresh_drives(self):
        while self.drives_grid.count():
            item = self.drives_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        all_drives = enumerate_logical_drives()
        if self.filter_removable_only:
            self.drives = [d for d in all_drives if d.drive_type == DRIVE_REMOVABLE]
        else:
            self.drives = all_drives
        self.drive_cards = []

        if not self.drives and self.filter_removable_only:
            empty_card = QFrame()
            empty_card.setObjectName("Card")
            empty_card.setFixedHeight(96)
            el = QHBoxLayout(empty_card)
            el.setContentsMargins(20, 12, 20, 12)
            el.setSpacing(14)
            ico_lbl = QLabel()
            usb_p = get_asset_path("usb_3d.png")
            if os.path.exists(usb_p):
                ico_lbl.setPixmap(QPixmap(usb_p).scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            el.addWidget(ico_lbl)
            txt = QLabel(self.strings["no_removable_found"])
            txt.setObjectName("MutedLabel")
            txt.setWordWrap(True)
            el.addWidget(txt, 1)
            self.drives_grid.addWidget(empty_card, 0, 0, 1, 4)
            return

        cols = 4
        for idx, drive in enumerate(self.drives):
            row = idx // cols
            col = idx % cols
            card = self.create_drive_card(drive)
            self.drives_grid.addWidget(card, row, col)
            self.drive_cards.append((drive, card))

        if self.drives:
            self.select_drive_card(self.drive_cards[0][1], self.drives[0])

    def create_drive_card(self, drive: DriveInfo) -> QFrame:
        card = QFrame()
        card.setObjectName("DriveCard")
        card.setFixedHeight(86)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_ico = QLabel()
        ico_name = "usb_3d.png" if drive.drive_type == DRIVE_REMOVABLE else "disk_3d.png"
        disk_ico_path = get_asset_path(ico_name)
        if os.path.exists(disk_ico_path):
            lbl_ico.setPixmap(QPixmap(disk_ico_path).scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(lbl_ico)

        name_layout = QVBoxLayout()
        name_layout.setSpacing(1)
        lbl_name = QLabel(f"{drive.label} ({drive.letter[0]}:)")
        lbl_name.setObjectName("CardTitle")
        name_layout.addWidget(lbl_name)

        lbl_space = QLabel(f"{drive.free_gb:.1f} GB / {drive.total_gb:.1f} GB")
        lbl_space.setObjectName("CardSub")
        name_layout.addWidget(lbl_space)
        header_layout.addLayout(name_layout)

        header_layout.addStretch()

        lbl_check = QLabel("✓")
        lbl_check.setStyleSheet("color: #0D6EFD; font-weight: 800; font-size: 14px;")
        lbl_check.setVisible(False)
        card.lbl_check = lbl_check
        header_layout.addWidget(lbl_check)

        layout.addLayout(header_layout)

        # Clean Progress Bar WITHOUT overlapping duplicate text!
        prog_layout = QHBoxLayout()
        prog_layout.setSpacing(8)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(drive.usage_percentage)
        bar.setTextVisible(False)  # CRITICAL FIX: eliminates clipped duplicate % text!
        bar.setFixedHeight(6)
        prog_layout.addWidget(bar, 1)

        lbl_pct = QLabel(f"{drive.usage_percentage}%")
        lbl_pct.setObjectName("CardSub")
        prog_layout.addWidget(lbl_pct)

        layout.addLayout(prog_layout)

        card.mousePressEvent = lambda e: self.select_drive_card(card, drive)
        return card

    def clear_drive_card_selections(self):
        for d, c in getattr(self, "drive_cards", []):
            c.setProperty("selected", "false")
            if hasattr(c, "lbl_check"):
                c.lbl_check.setVisible(False)
            c.style().unpolish(c)
            c.style().polish(c)

    def select_drive_card(self, card: QFrame, drive: DriveInfo):
        self.clear_drive_card_selections()
        for c in [self.card_recycle, self.card_desktop, self.card_folder]:
            c.setProperty("selected", "false")
            c.style().unpolish(c)
            c.style().polish(c)

        card.setProperty("selected", "true")
        if hasattr(card, "lbl_check"):
            card.lbl_check.setVisible(True)
        card.style().unpolish(card)
        card.style().polish(card)

        self.selected_target = drive.letter
        self.selected_target_type = "drive"
        self.lbl_selected_target_disp.setText(f"🎯 {drive.label} ({drive.letter})")

    def get_selected_categories(self) -> List[str]:
        cats = []
        if self.chk_graphics.isChecked(): cats.append(CAT_GRAPHICS)
        if self.chk_docs.isChecked(): cats.append(CAT_DOCUMENTS)
        if self.chk_video.isChecked(): cats.append(CAT_VIDEO)
        if self.chk_audio.isChecked(): cats.append(CAT_AUDIO)
        if self.chk_archives.isChecked(): cats.append(CAT_ARCHIVES)
        if self.chk_database.isChecked(): cats.append(CAT_DATABASE)
        return cats

    def start_recovery_scan(self):
        if not self.selected_target:
            QMessageBox.warning(self, "No Target Selected", "Please select a drive or folder to scan.")
            return

        chosen_cats = self.get_selected_categories()
        is_format_mode = self.rb_format.isChecked()
        target_path = self.selected_target

        self.stack.setCurrentIndex(1)
        self.page_scan.all_files.clear()
        self.page_scan.table.setRowCount(0)
        self.page_scan.set_target(target_path)

        try:
            self.worker_signals.progress.disconnect()
            self.worker_signals.finished.disconnect()
        except Exception:
            pass

        self.worker_signals.progress.connect(self.page_scan.update_progress)
        self.worker_signals.finished.connect(self.page_scan.set_results)

        def worker():
            try:
                if is_format_mode:
                    engine = FormatRecoveryEngine(
                        target_drive_letter_or_path=target_path,
                        selected_categories=chosen_cats
                    )
                    self.page_scan.scanner_instance = engine
                    results = engine.scan_drive(
                        progress_callback=lambda p, s, c, sp: self.worker_signals.progress.emit(p, s, c, sp),
                        max_sectors=150000
                    )
                else:
                    engine = UndeleteScanner(
                        target_path=target_path,
                        selected_categories=chosen_cats
                    )
                    self.page_scan.scanner_instance = engine
                    results = engine.scan_targeted_folder(
                        progress_callback=lambda p, s, c, sp=0.0: self.worker_signals.progress.emit(p, s, c, sp)
                    )
                self.worker_signals.finished.emit(results)
            except Exception as e:
                print("Worker error:", e)
                self.worker_signals.finished.emit([])

        threading.Thread(target=worker, daemon=True).start()

    def start_partition_scan_flow(self, partition_label: str):
        self.selected_target = partition_label
        self.start_recovery_scan()

    def relaunch_as_admin(self):
        """Relaunch Insight Recovery elevated with UAC Administrator privileges for raw NTFS $MFT access."""
        try:
            if getattr(sys, "frozen", False):
                exe = sys.executable
                params = " ".join(f'"{a}"' for a in sys.argv[1:])
            else:
                exe = sys.executable
                script = os.path.abspath(sys.argv[0])
                params = f'"{script}"'
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            if ret > 32:
                QApplication.quit()
        except Exception as e:
            QMessageBox.warning(self, "Elevation Error", f"Could not elevate privileges: {e}")

    def show_drives_view(self):
        self.filter_removable_only = False
        self.stack.setCurrentIndex(0)
        self.set_active_sidebar_btn(self.btn_nav_hardware)
        self.lbl_internal_drives.setText(self.strings["internal_drives"])
        self.refresh_drives()

    def show_repair_view(self):
        self.stack.setCurrentIndex(2)
        self.set_active_sidebar_btn(self.btn_nav_repair)

    def show_partition_view(self):
        self.stack.setCurrentIndex(3)
        self.set_active_sidebar_btn(self.btn_nav_partition)

    def show_backup_view(self):
        self.stack.setCurrentIndex(4)
        self.set_active_sidebar_btn(self.btn_nav_backup)

    def save_current_session(self):
        if not self.page_scan.all_files:
            QMessageBox.information(
                self,
                "لا توجد نتائج للحفظ" if self.lang == "ar" else "No Scan Results",
                "قم بإجراء فحص أولاً ثم احفظ نتائج الجلسة لاسترجاعها لاحقاً." if self.lang == "ar" else "Please run a scan first before saving a session."
            )
            return

        default_name = f"Insight_Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.irsession"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Scan Session", default_name,
            "Insight Recovery Session (*.irsession);;All Files (*.*)"
        )
        if file_path:
            ok, msg = save_scan_session(file_path, self.page_scan.target_path or "Target", self.page_scan.all_files)
            if ok:
                QMessageBox.information(self, "Session Saved", msg)
            else:
                QMessageBox.warning(self, "Save Error", msg)

    def load_session_flow(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Scan Session", "",
            "Insight Recovery Session (*.irsession);;All Files (*.*)"
        )
        if file_path:
            ok, msg, target_path, files = load_scan_session(file_path)
            if ok and files:
                self.stack.setCurrentIndex(1)
                self.page_scan.set_target(target_path)
                self.page_scan.set_results(files, session_loaded=True)
                QMessageBox.information(self, "Session Loaded", msg)
            else:
                QMessageBox.warning(self, "Load Error", msg)

    def open_settings_dialog(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(current_lang=self.lang, is_dark=self.is_dark, parent=self)
        dlg.theme_changed.connect(self.set_theme_mode)
        dlg.language_changed.connect(self.set_language_mode)
        dlg.exec()

    def set_theme_mode(self, is_dark: bool):
        self.is_dark = is_dark
        self.apply_theme()

    def apply_theme(self):
        sheet = get_dark_stylesheet() if self.is_dark else get_light_stylesheet()
        self.setStyleSheet(sheet)

    def set_language_mode(self, new_lang: str):
        if self.lang != new_lang:
            self.lang = new_lang
            self.strings = STRINGS[self.lang]
            self.update_language_ui()

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self.apply_theme()

    def toggle_language(self):
        new_lang = "en" if self.lang == "ar" else "ar"
        self.set_language_mode(new_lang)

    def update_language_ui(self):
        self.btn_save_session.setText("💾 " + self.strings["btn_save_session"])
        self.btn_load_session.setText(" " + self.strings["btn_load_session"])
        self.btn_settings.setText(" " + self.strings["btn_settings"])

        self.setWindowTitle(self.strings["app_title"])
        self.lbl_top_info.setText(self.strings["app_subtitle"])
        self.lbl_sec_rec.setText(self.strings["sec_data_recovery"])
        self.lbl_sec_adv.setText(self.strings["sec_advanced"])
        self.lbl_sec_bak.setText(self.strings["sec_backup"])

        self.btn_nav_hardware.setText("💾  " + self.strings["nav_hardware_disk"])
        self.btn_nav_sd.setText("💳  " + self.strings["nav_sd_card"])
        self.btn_nav_folder.setText("📁  " + self.strings["nav_folder_scan"])
        self.btn_nav_format.setText("🔄  " + self.strings["nav_format_recovery"])
        self.btn_nav_repair.setText("🛠️  " + self.strings["nav_file_repair"])
        self.btn_nav_partition.setText("🧩  " + self.strings["nav_lost_partition"])
        self.btn_nav_backup.setText("⏱️  " + self.strings["nav_disk_image"])

        self.lbl_select_title.setText(self.strings["select_location_title"])
        self.lbl_internal_drives.setText(self.strings["removable_drives"] if self.filter_removable_only else self.strings["internal_drives"])
        self.lbl_specify_loc.setText(self.strings["specify_location"])
        self.card_recycle.lbl_t.setText(self.strings["recycle_bin"])
        self.card_desktop.lbl_t.setText(self.strings["desktop"])
        self.card_folder.lbl_t.setText(self.strings["select_folder"])

        self.lbl_types_title.setText(self.strings["file_types_title"])
        self.chk_graphics.setText(self.strings["cat_graphics"])
        self.chk_docs.setText(self.strings["cat_documents"])
        self.chk_video.setText(self.strings["cat_video"])
        self.chk_audio.setText(self.strings["cat_audio"])
        self.chk_archives.setText(self.strings["cat_archives"])
        self.chk_database.setText(self.strings["cat_database"])

        self.rb_deleted.setText(self.strings["mode_deleted"])
        self.rb_format.setText(self.strings["mode_format"])
        self.btn_search.setText("🔍  " + self.strings["btn_search"])
        if hasattr(self, "btn_elevate_admin"):
            self.btn_elevate_admin.setText("🛡️ تشغيل كمسؤول ($MFT)" if self.lang == "ar" else "🛡️ Elevate Admin ($MFT)")

        # Propagate language to all sub-pages!
        self.page_scan.set_language(self.lang)
        self.page_repair.set_language(self.lang)
        self.page_partition.set_language(self.lang)
        self.page_backup.set_language(self.lang)

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight)
