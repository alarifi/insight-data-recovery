"""
Insight Data Recovery Studio Pro - Commercial Design System & Localization v5.0
Full Light & Dark theme parity across every view and dialog, crisp custom checkboxes/radios,
and complete Arabic (RTL) / English (LTR) localization.
"""
import os
import sys

STRINGS = {
    "ar": {
        "app_title": "Insight Data Recovery Studio Pro",
        "app_subtitle": "المنظومة الاحترافية الشاملة لاستعادة البيانات وترميم الملفات المعطوبة",
        "sec_data_recovery": "استعادة البيانات",
        "nav_hardware_disk": "الأقراص الصلبة",
        "nav_sd_card": "كروت الذاكرة و USB",
        "nav_folder_scan": "فحص مجلد مخصص",
        "nav_format_recovery": "استعادة بعد الفورمات",
        "sec_advanced": "المزايا المتقدمة",
        "nav_file_repair": "مركز إصلاح الملفات",
        "nav_lost_partition": "استعادة الأقسام المفقودة",
        "sec_backup": "الأمان والنسخ الاحتياطي",
        "nav_disk_image": "صورة القرص (ChronoSnap)",
        "select_location_title": "حدد مساراً للبحث عن البيانات المفقودة",
        "internal_drives": "الأقراص الداخلية ووحدات التخزين",
        "removable_drives": "وحدات التخزين القابلة للإزالة (SD Card / USB)",
        "no_removable_found": "لم يتم اكتشاف بطاقة SD أو فلاشة USB حالياً. قم بتوصيلها ثم اضغط تحديث.",
        "specify_location": "أو حدد مساراً سريعاً",
        "recycle_bin": "سلة المحذوفات",
        "desktop": "سطح المكتب",
        "select_folder": "اختيار مجلد بعينه",
        "file_types_title": "تحديد أنواع الملفات:",
        "cat_graphics": "صور ورسومات",
        "cat_documents": "مستندات ووثائق",
        "cat_video": "فيديوهات",
        "cat_audio": "ملفات صوتية",
        "cat_archives": "ملفات مضغوطة",
        "cat_database": "قواعد بيانات وأكواد",
        "mode_deleted": "فحص المحذوفات السريع",
        "mode_format": "فحص الفورمات العميق",
        "btn_search": "ابدأ البحث عن البيانات المفقودة",
        "status_ready": "المحرك جاهز للعمل 100% دون إنترنت",
        "btn_recover": "استعادة المحدد",
        "btn_stop": "إيقاف",
        "btn_pause": "إيقاف مؤقت",
        "btn_resume": "استئناف",
        "col_name": "اسم الملف",
        "col_path": "المسار الأصلي",
        "col_size": "الحجم",
        "col_type": "النوع",
        "col_date": "التاريخ",
        "col_quality": "السلامة",
        "tab_all": "كافة الملفات",
        "tab_preview": "معاينة الملف",
        "tab_hex": "فاحص البايتات السداسي (Hex)",
        "repair_title": "مركز إصلاح وترميم الملفات المعطوبة (File Repair)",
        "repair_desc": "إصلاح ملفات الأوفيس، الصور المشوهة، الفيديو بدون صوت، والـ PDF التالف",
        "btn_select_repair_file": "اختر الملف التالف للإصلاح",
        "btn_start_repair": "بدء عملية الإصلاح والترميم",
        "partition_title": "استعادة الأقسام المفقودة (Lost Partition Rescue)",
        "partition_desc": "إنقاذ البارتشنات التي تظهر كـ RAW أو Unallocated أو المتضررة بواسطة BitLocker",
        "btn_scan_partitions": "فحص الأقسام المفقودة الآن",
        "btn_save_session": "حفظ الجلسة",
        "btn_load_session": "استرجاع جلسة",
        "btn_settings": "الإعدادات",
        "tab_path": "المسار",
        "tab_type": "النوع",
        "search_placeholder": "بحث بالاسم أو الامتداد...",
        "filter_btn": "تصفية",
        "preview_btn": "معاينة / Hex",
        "recovery_path_lbl": "مسار الاستعادة الآمن:",
        "btn_browse": "استعراض...",
        "status_scanning": "جاري الفحص السريع، تم العثور على:",
        "status_patient": "جاري فحص العناقيد ومطابقة التواقيع. يرجى الانتظار!",
        "status_session_loaded": "تم استرجاع الجلسة بنجاح، تم العثور على:",
        "status_scan_complete": "اكتمل الفحص بنجاح، تم العثور على:",
        "status_scan_complete_sub": "يمكنك استعراض الشجرة وتحديد الملفات أو المجلدات المطلوبة للاسترجاع.",
        "lang_toggle": "English",
        "theme_toggle": "الوضع الداكن",
        "select_all_btn": "تحديد الكل",
        "deselect_all_btn": "إلغاء التحديد",
        "home_btn": "الرئيسية",
        "settings_title": "إعدادات المنظومة والترخيص",
        "settings_general": "اللغة والمظهر",
        "settings_license": "الريجستري والتسجيل",
        "settings_updates": "التحقق من التحديثات",
        "settings_help": "المساعدة والدعم",
        "settings_about": "حول البرنامج",
        "prop_name": "الاسم:",
        "prop_size": "الحجم:",
        "prop_type": "النوع:",
        "prop_date": "التاريخ:",
        "prop_status": "السلامة:",
        "prop_path": "المسار:",
        "selected_lbl": "المحدد:",
        "files_word": "ملف",
        "safe_drive_lbl": "قرص استعادة آمن:",
        "warn_same_drive_lbl": "تحذير: نفس القرص المفحوص!"
    },
    "en": {
        "app_title": "Insight Data Recovery Studio Pro",
        "app_subtitle": "Professional Comprehensive Data Recovery & File Repair Suite",
        "sec_data_recovery": "Data Recovery",
        "nav_hardware_disk": "Hardware Disk",
        "nav_sd_card": "SD Card && USB",
        "nav_folder_scan": "Targeted Folder Scan",
        "nav_format_recovery": "Format Recovery",
        "sec_advanced": "Advanced Features",
        "nav_file_repair": "File Repair Center",
        "nav_lost_partition": "Lost Partition Rescue",
        "sec_backup": "File Backup & Safety",
        "nav_disk_image": "ChronoSnap Disk Image",
        "select_location_title": "Select a location to search for lost data",
        "internal_drives": "Internal Drives & Storage",
        "removable_drives": "Removable Storage (SD Card / USB)",
        "no_removable_found": "No SD Card or USB Drive detected. Plug in a removable device and click Refresh.",
        "specify_location": "Specify a location",
        "recycle_bin": "Recycle Bin",
        "desktop": "Desktop",
        "select_folder": "Select Folder",
        "file_types_title": "Filter by File Types:",
        "cat_graphics": "Graphics && Photos",
        "cat_documents": "Documents && Office",
        "cat_video": "Videos",
        "cat_audio": "Audio Files",
        "cat_archives": "Archives && ZIP",
        "cat_database": "Databases && Code",
        "mode_deleted": "Quick Undelete Mode",
        "mode_format": "Deep Format Recovery",
        "btn_search": "Search for Lost Data",
        "status_ready": "100% Offline Commercial Recovery Engine Ready",
        "btn_recover": "Recover Selected",
        "btn_stop": "Stop",
        "btn_pause": "Pause",
        "btn_resume": "Resume",
        "col_name": "Name",
        "col_path": "Original Path",
        "col_size": "Size",
        "col_type": "Type",
        "col_date": "Date Modified",
        "col_quality": "Integrity",
        "tab_all": "All Files",
        "tab_preview": "Live Preview",
        "tab_hex": "Hex Inspector",
        "repair_title": "Intelligent File Repair Center",
        "repair_desc": "Repair corrupted Office docs, distorted photos, broken videos & PDFs",
        "btn_select_repair_file": "Select Corrupted File to Repair",
        "btn_start_repair": "Start Repair Process",
        "partition_title": "Lost Partition Rescue",
        "partition_desc": "Recover partitions showing as RAW, Unallocated, or damaged BitLocker",
        "btn_scan_partitions": "Scan for Lost Partitions",
        "btn_save_session": "Save Session",
        "btn_load_session": "Load Session",
        "btn_settings": "Settings",
        "tab_path": "Path",
        "tab_type": "Type",
        "search_placeholder": "Search files or extensions...",
        "filter_btn": "Filter",
        "preview_btn": "Preview / Hex",
        "recovery_path_lbl": "Safe Recovery Destination:",
        "btn_browse": "Browse...",
        "status_scanning": "Quick Scanning, Files Found:",
        "status_patient": "Scanning clusters and analyzing signatures. Please be patient!",
        "status_session_loaded": "Scan Session Loaded, Files Found:",
        "status_scan_complete": "Scan Complete, Files Found:",
        "status_scan_complete_sub": "All clusters processed. Expand folders or select files to recover.",
        "lang_toggle": "العربية",
        "theme_toggle": "Dark Mode",
        "select_all_btn": "Select All",
        "deselect_all_btn": "Deselect All",
        "home_btn": "Home",
        "settings_title": "System Settings & Licensing",
        "settings_general": "Language & Theme",
        "settings_license": "Registry & License",
        "settings_updates": "Check for Updates",
        "settings_help": "Help & Documentation",
        "settings_about": "About",
        "prop_name": "Name:",
        "prop_size": "Size:",
        "prop_type": "Type:",
        "prop_date": "Date:",
        "prop_status": "Integrity:",
        "prop_path": "Path:",
        "selected_lbl": "Selected:",
        "files_word": "files",
        "safe_drive_lbl": "Safe drive:",
        "warn_same_drive_lbl": "Warning: Same drive as source!"
    }
}


def get_asset_path(filename: str) -> str:
    """Resolve asset paths reliably across development and PyInstaller bundles (contents_directory='InsightRecovery')."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "assets", filename))
        candidates.append(os.path.join(sys._MEIPASS, filename))
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "InsightRecovery", "assets", filename))
        candidates.append(os.path.join(exe_dir, "assets", filename))
        candidates.append(os.path.join(exe_dir, "_internal", "assets", filename))
        candidates.append(os.path.join(exe_dir, filename))
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    candidates.append(os.path.join(project_root, "assets", filename))
    candidates.append(os.path.join(r"E:\PortableApps\insight software\Insight Reconery\InsightDataRecovery\assets", filename))

    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0] if candidates else filename


_ICON_CACHE = {}


def get_ui_icon(name: str):
    """Return cached QIcon from assets/icons/<name> for zero-overhead rendering across trees, tables & buttons."""
    from PyQt6.QtGui import QIcon
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    path = get_asset_path(os.path.join("icons", name))
    ico = QIcon(path) if os.path.exists(path) else QIcon()
    _ICON_CACHE[name] = ico
    return ico


def get_category_icon(category_name: str):
    """Return crisp glossy QIcon for each file category in the left Type tree."""
    low = (category_name or "").lower()
    if "archive" in low:
        return get_ui_icon("cat_archives.png")     # rar.png as requested!
    if "audio" in low:
        return get_ui_icon("cat_audio.png")
    if "video" in low:
        return get_ui_icon("cat_video.png")
    if "graphic" in low or "image" in low or "photo" in low:
        return get_ui_icon("cat_graphics.png")
    if "document" in low:
        return get_ui_icon("cat_documents.png")
    if "database" in low or "code" in low:
        return get_ui_icon("cat_database.png")
    return get_ui_icon("cat_other.png")


_EXT_ICON_MAP = {
    "doc": "ext_word.png", "docx": "ext_word.png", "odt": "ext_word.png",
    "xls": "ext_excel.png", "xlsx": "ext_excel.png", "ods": "ext_excel.png",
    "ppt": "ext_ppt.png", "pptx": "ext_ppt.png", "odp": "ext_ppt.png",
    "pdf": "ext_pdf.png",
    "gif": "ext_gif.png",
    "png": "cat_graphics.png", "jpg": "cat_graphics.png", "jpeg": "cat_graphics.png", "bmp": "cat_graphics.png",
    "ico": "ext_ico.png", "svg": "ext_svg.png", "webp": "ext_webp.png",
    "rar": "cat_archives.png", "zip": "ext_zip.png", "7z": "ext_7z.png",
    "tar": "ext_tar.png", "gz": "ext_tar.png", "bz2": "ext_tar.png", "xz": "cat_archives.png",
    "mp4": "cat_video.png", "mkv": "cat_video.png", "avi": "cat_video.png", "mov": "cat_video.png", "wmv": "cat_video.png", "flv": "cat_video.png",
    "mp3": "cat_audio.png", "wav": "cat_audio.png", "flac": "cat_audio.png", "aac": "cat_audio.png", "ogg": "cat_audio.png", "m4a": "cat_audio.png",
    "txt": "ext_txt.png", "md": "ext_txt.png", "rtf": "ext_rtf.png",
    "csv": "ext_csv.png", "json": "ext_json.png", "xml": "ext_xml.png",
    "html": "ext_html.png", "htm": "ext_html.png", "log": "ext_log.png",
    "ini": "ext_ini.png", "cfg": "ext_ini.png",
    "exe": "ext_exe.png", "dll": "ext_dll.png", "msi": "ext_msi.png", "iso": "ext_iso.png",
    "py": "cat_database.png", "js": "cat_database.png", "java": "cat_database.png",
    "c": "cat_database.png", "cpp": "cat_database.png", "h": "cat_database.png",
    "sql": "cat_database.png", "db": "cat_database.png", "sqlite": "cat_database.png",
}


def get_ext_icon(ext: str, category: str = ""):
    """Return crisp glossy QIcon matching a specific file extension (with category fallback)."""
    clean = (ext or "").lower().lstrip(".")
    icon_file = _EXT_ICON_MAP.get(clean)
    if icon_file:
        return get_ui_icon(icon_file)
    return get_category_icon(category)


def _check_icon_qss() -> str:
    p = get_asset_path("check_white.png").replace("\\", "/")
    return f"image: url({p});" if os.path.exists(get_asset_path("check_white.png")) else ""


def get_light_stylesheet() -> str:
    chk_img = _check_icon_qss()
    return f"""
    QMainWindow, QDialog {{
        background-color: #F4F7FB;
        color: #1E293B;
        font-family: 'Segoe UI', Tahoma, Arial;
    }}
    QWidget {{
        font-family: 'Segoe UI', Tahoma, Arial;
    }}
    QWidget#Sidebar {{
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
        border-left: 1px solid #E2E8F0;
    }}
    QLabel {{
        color: #1E293B;
        border: none;
        background: transparent;
    }}
    QLabel#SidebarSection {{
        color: #94A3B8;
        font-size: 11px;
        font-weight: 700;
        padding: 10px 14px 4px 14px;
    }}
    QLabel#PageTitle {{
        color: #0F172A;
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#SectionHeader {{
        color: #475569;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#CardTitle {{
        color: #0F172A;
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#CardSub {{
        color: #64748B;
        font-size: 11px;
    }}
    QLabel#MutedLabel {{
        color: #64748B;
        font-size: 11px;
    }}
    QLabel#AccentLabel {{
        color: #0D6EFD;
        font-weight: 700;
        font-size: 12px;
    }}
    QLabel#ProBadge {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
        color: #FFFFFF;
        font-size: 9px;
        font-weight: 800;
        border-radius: 4px;
        padding: 2px 6px;
    }}
    QPushButton {{
        outline: 0;
    }}
    QPushButton#NavBtn {{
        background-color: transparent;
        color: #334155;
        text-align: left;
        padding: 9px 14px;
        font-size: 12px;
        font-weight: 500;
        border: none;
        border-radius: 8px;
        margin: 1px 8px;
    }}
    QPushButton#NavBtn:hover {{
        background-color: #F1F5F9;
        color: #0D6EFD;
    }}
    QPushButton#NavBtn[active="true"] {{
        background-color: #E8F1FF;
        color: #0D6EFD;
        font-weight: 700;
    }}
    QFrame#Card, QFrame#DriveCard, QFrame#QuickCard {{
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
    }}
    QFrame#DriveCard:hover, QFrame#QuickCard:hover {{
        border: 1.5px solid #60A5FA;
        background-color: #F8FBFF;
    }}
    QFrame#DriveCard[selected="true"], QFrame#QuickCard[selected="true"] {{
        border: 2px solid #0D6EFD;
        background-color: #EFF6FF;
    }}
    QFrame#DropZoneCard {{
        background-color: #FFFFFF;
        border: 2px dashed #93C5FD;
        border-radius: 12px;
    }}
    QFrame#DropZoneCard:hover {{
        border-color: #0D6EFD;
        background-color: #F8FBFF;
    }}
    QFrame#InsetBox {{
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
    }}
    QFrame#SettingsCard {{
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
    }}
    QFrame#SuccessBadge {{
        background-color: #ECFDF5;
        border: 1px solid #10B981;
        border-radius: 8px;
    }}
    QLabel#ThumbPreview {{
        background-color: #F1F5F9;
        color: #334155;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 6px;
    }}
    QPushButton#PrimaryActionBtn {{
        background-color: #0D6EFD;
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 700;
    }}
    QPushButton#PrimaryActionBtn:hover {{
        background-color: #0B5ED7;
    }}
    QPushButton#PrimaryActionBtn:pressed {{
        background-color: #0A58CA;
    }}
    QPushButton#SuccessActionBtn {{
        background-color: #10B981;
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        padding: 9px 28px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton#SuccessActionBtn:hover {{
        background-color: #059669;
    }}
    QPushButton#DangerActionBtn {{
        background-color: #FFFFFF;
        color: #DC2626;
        border: 1px solid #FCA5A5;
        border-radius: 6px;
        padding: 5px 11px;
        font-size: 11px;
        font-weight: 700;
    }}
    QPushButton#DangerActionBtn:hover {{
        background-color: #FEF2F2;
        border: 1px solid #EF4444;
        color: #B91C1C;
    }}
    QPushButton#SecondaryActionBtn {{
        background-color: #FFFFFF;
        color: #334155;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 5px 11px;
        font-size: 11px;
        font-weight: 600;
    }}
    QPushButton#SecondaryActionBtn:hover {{
        background-color: #F1F5F9;
        border-color: #94A3B8;
        color: #0D6EFD;
    }}
    QLineEdit, QComboBox {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 12px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1.5px solid #0D6EFD;
    }}
    QComboBox QAbstractItemView {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #CBD5E1;
        selection-background-color: #EFF6FF;
        selection-color: #0D6EFD;
    }}
    QProgressBar {{
        border: none;
        background-color: #E2E8F0;
        border-radius: 3px;
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: #0D6EFD;
        border-radius: 3px;
    }}
    QTableWidget {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        gridline-color: #F1F5F9;
        font-size: 12px;
        outline: 0;
        alternate-background-color: #FAFBFD;
    }}
    QTableWidget::item {{
        padding: 4px 6px;
    }}
    QTableWidget::item:selected {{
        background-color: #E0F2FE;
        color: #0F172A;
    }}
    QHeaderView::section {{
        background-color: #F8FAFC;
        color: #475569;
        padding: 7px 6px;
        border: none;
        border-bottom: 1px solid #E2E8F0;
        font-weight: 700;
        font-size: 11px;
    }}
    QTreeWidget {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        font-size: 12px;
        outline: 0;
    }}
    QTreeWidget::item {{
        padding: 4px 2px;
    }}
    QTreeWidget::item:selected {{
        background-color: #EFF6FF;
        color: #0D6EFD;
        font-weight: 600;
    }}
    QTabWidget::pane {{
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        background: #FFFFFF;
        top: -1px;
    }}
    QTabBar::tab {{
        background: #F1F5F9;
        color: #475569;
        padding: 6px 14px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: 600;
        font-size: 11px;
    }}
    QTabBar::tab:selected {{
        background: #FFFFFF;
        color: #0D6EFD;
        border: 1px solid #E2E8F0;
        border-bottom: 2px solid #0D6EFD;
    }}
    QListWidget {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        outline: 0;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 6px;
        margin-bottom: 2px;
        color: #334155;
    }}
    QListWidget::item:selected {{
        background-color: #0D6EFD;
        color: #FFFFFF;
        font-weight: 700;
    }}
    QListWidget::item:hover:!selected {{
        background-color: #F1F5F9;
    }}
    QCheckBox {{
        color: #334155;
        font-size: 12px;
        spacing: 6px;
    }}
    QCheckBox::indicator, QTreeWidget::indicator, QTableWidget::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1.5px solid #94A3B8;
        background-color: #FFFFFF;
    }}
    QCheckBox::indicator:checked, QTreeWidget::indicator:checked, QTableWidget::indicator:checked {{
        background-color: #0D6EFD;
        border-color: #0D6EFD;
        {chk_img}
    }}
    QRadioButton {{
        color: #1E293B;
        font-size: 12px;
        spacing: 6px;
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 9px;
        border: 2px solid #94A3B8;
        background-color: #FFFFFF;
    }}
    QRadioButton::indicator:checked {{
        width: 8px;
        height: 8px;
        border-radius: 9px;
        border: 5px solid #0D6EFD;
        background-color: #FFFFFF;
    }}
    QScrollBar:vertical {{
        background: #F8FAFC;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: #F8FAFC;
    }}
    QScrollBar::handle:vertical {{
        background: #CBD5E1;
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #94A3B8;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: #F8FAFC;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: #F8FAFC;
    }}
    QScrollBar::handle:horizontal {{
        background: #CBD5E1;
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QTextEdit {{
        background-color: #FFFFFF;
        color: #1E293B;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
    }}
    QSplitter::handle {{
        background-color: #E2E8F0;
        width: 2px;
        margin: 4px 2px;
    }}
    """


def get_dark_stylesheet() -> str:
    chk_img = _check_icon_qss()
    return f"""
    QMainWindow, QDialog {{
        background-color: #0B1120;
        color: #F1F5F9;
        font-family: 'Segoe UI', Tahoma, Arial;
    }}
    QWidget {{
        font-family: 'Segoe UI', Tahoma, Arial;
    }}
    QWidget#Sidebar {{
        background-color: #111827;
        border-right: 1px solid #1F2937;
        border-left: 1px solid #1F2937;
    }}
    QLabel {{
        color: #E2E8F0;
        border: none;
        background: transparent;
    }}
    QLabel#SidebarSection {{
        color: #64748B;
        font-size: 11px;
        font-weight: 700;
        padding: 10px 14px 4px 14px;
    }}
    QLabel#PageTitle {{
        color: #F8FAFC;
        font-size: 18px;
        font-weight: 700;
    }}
    QLabel#SectionHeader {{
        color: #94A3B8;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#CardTitle {{
        color: #F8FAFC;
        font-size: 13px;
        font-weight: 700;
    }}
    QLabel#CardSub {{
        color: #94A3B8;
        font-size: 11px;
    }}
    QLabel#MutedLabel {{
        color: #94A3B8;
        font-size: 11px;
    }}
    QLabel#AccentLabel {{
        color: #38BDF8;
        font-weight: 700;
        font-size: 12px;
    }}
    QLabel#ProBadge {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
        color: #FFFFFF;
        font-size: 9px;
        font-weight: 800;
        border-radius: 4px;
        padding: 2px 6px;
    }}
    QPushButton {{
        outline: 0;
    }}
    QPushButton#NavBtn {{
        background-color: transparent;
        color: #CBD5E1;
        text-align: left;
        padding: 9px 14px;
        font-size: 12px;
        font-weight: 500;
        border: none;
        border-radius: 8px;
        margin: 1px 8px;
    }}
    QPushButton#NavBtn:hover {{
        background-color: #1E293B;
        color: #38BDF8;
    }}
    QPushButton#NavBtn[active="true"] {{
        background-color: #172554;
        color: #60A5FA;
        font-weight: 700;
    }}
    QFrame#Card, QFrame#DriveCard, QFrame#QuickCard {{
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
    }}
    QFrame#DriveCard:hover, QFrame#QuickCard:hover {{
        border: 1.5px solid #38BDF8;
        background-color: #162032;
    }}
    QFrame#DriveCard[selected="true"], QFrame#QuickCard[selected="true"] {{
        border: 2px solid #38BDF8;
        background-color: #172554;
    }}
    QFrame#DropZoneCard {{
        background-color: #111827;
        border: 2px dashed #3B82F6;
        border-radius: 12px;
    }}
    QFrame#DropZoneCard:hover {{
        border-color: #38BDF8;
        background-color: #162032;
    }}
    QFrame#InsetBox {{
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
    }}
    QFrame#SettingsCard {{
        background-color: #0F172A;
        border: 1px solid #1F2937;
        border-radius: 8px;
    }}
    QFrame#SuccessBadge {{
        background-color: #064E3B;
        border: 1px solid #10B981;
        border-radius: 8px;
    }}
    QLabel#ThumbPreview {{
        background-color: #0F172A;
        color: #CBD5E1;
        border: 1px dashed #334155;
        border-radius: 8px;
        padding: 6px;
    }}
    QPushButton#PrimaryActionBtn {{
        background-color: #0284C7;
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        padding: 7px 18px;
        font-size: 12px;
        font-weight: 700;
    }}
    QPushButton#PrimaryActionBtn:hover {{
        background-color: #0369A1;
    }}
    QPushButton#SuccessActionBtn {{
        background-color: #059669;
        color: #FFFFFF;
        border: none;
        border-radius: 7px;
        padding: 9px 28px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton#SuccessActionBtn:hover {{
        background-color: #047857;
    }}
    QPushButton#DangerActionBtn {{
        background-color: #1E293B;
        color: #FCA5A5;
        border: 1px solid #7F1D1D;
        border-radius: 6px;
        padding: 5px 11px;
        font-size: 11px;
        font-weight: 700;
    }}
    QPushButton#DangerActionBtn:hover {{
        background-color: #3B181C;
        border: 1px solid #EF4444;
        color: #FECACA;
    }}
    QPushButton#SecondaryActionBtn {{
        background-color: #1E293B;
        color: #E2E8F0;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 5px 11px;
        font-size: 11px;
        font-weight: 600;
    }}
    QPushButton#SecondaryActionBtn:hover {{
        background-color: #334155;
        border-color: #38BDF8;
        color: #FFFFFF;
    }}
    QLineEdit, QComboBox {{
        background-color: #0F172A;
        color: #F1F5F9;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 5px 10px;
        font-size: 12px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1.5px solid #38BDF8;
    }}
    QComboBox QAbstractItemView {{
        background-color: #111827;
        color: #F1F5F9;
        border: 1px solid #334155;
        selection-background-color: #172554;
        selection-color: #38BDF8;
    }}
    QProgressBar {{
        border: none;
        background-color: #1F2937;
        border-radius: 3px;
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: #38BDF8;
        border-radius: 3px;
    }}
    QTableWidget {{
        background-color: #111827;
        color: #E2E8F0;
        border: 1px solid #1F2937;
        border-radius: 8px;
        gridline-color: #1E293B;
        font-size: 12px;
        outline: 0;
        alternate-background-color: #0F172A;
    }}
    QTableWidget::item {{
        padding: 4px 6px;
    }}
    QTableWidget::item:selected {{
        background-color: #1E3A5F;
        color: #FFFFFF;
    }}
    QHeaderView::section {{
        background-color: #0F172A;
        color: #94A3B8;
        padding: 7px 6px;
        border: none;
        border-bottom: 1px solid #1F2937;
        font-weight: 700;
        font-size: 11px;
    }}
    QTreeWidget {{
        background-color: #111827;
        color: #E2E8F0;
        border: 1px solid #1F2937;
        border-radius: 8px;
        font-size: 12px;
        outline: 0;
    }}
    QTreeWidget::item {{
        padding: 4px 2px;
    }}
    QTreeWidget::item:selected {{
        background-color: #172554;
        color: #38BDF8;
        font-weight: 600;
    }}
    QTabWidget::pane {{
        border: 1px solid #1F2937;
        border-radius: 8px;
        background: #111827;
        top: -1px;
    }}
    QTabBar::tab {{
        background: #0F172A;
        color: #94A3B8;
        padding: 6px 14px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        font-weight: 600;
        font-size: 11px;
    }}
    QTabBar::tab:selected {{
        background: #111827;
        color: #38BDF8;
        border: 1px solid #1F2937;
        border-bottom: 2px solid #38BDF8;
    }}
    QListWidget {{
        background-color: #111827;
        color: #E2E8F0;
        border: 1px solid #1F2937;
        border-radius: 8px;
        outline: 0;
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 10px 12px;
        border-radius: 6px;
        margin-bottom: 2px;
        color: #CBD5E1;
    }}
    QListWidget::item:selected {{
        background-color: #0284C7;
        color: #FFFFFF;
        font-weight: 700;
    }}
    QListWidget::item:hover:!selected {{
        background-color: #1E293B;
    }}
    QCheckBox {{
        color: #E2E8F0;
        font-size: 12px;
        spacing: 6px;
    }}
    QCheckBox::indicator, QTreeWidget::indicator, QTableWidget::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1.5px solid #475569;
        background-color: #0F172A;
    }}
    QCheckBox::indicator:checked, QTreeWidget::indicator:checked, QTableWidget::indicator:checked {{
        background-color: #38BDF8;
        border-color: #38BDF8;
        {chk_img}
    }}
    QRadioButton {{
        color: #E2E8F0;
        font-size: 12px;
        spacing: 6px;
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 9px;
        border: 2px solid #64748B;
        background-color: #0F172A;
    }}
    QRadioButton::indicator:checked {{
        width: 8px;
        height: 8px;
        border-radius: 9px;
        border: 5px solid #38BDF8;
        background-color: #0F172A;
    }}
    QScrollBar:vertical {{
        background: #111827;
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: #111827;
    }}
    QScrollBar::handle:vertical {{
        background: #334155;
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #475569;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: #111827;
        height: 8px;
        margin: 0px;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: #111827;
    }}
    QScrollBar::handle:horizontal {{
        background: #334155;
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    QTextEdit {{
        background-color: #0F172A;
        color: #E2E8F0;
        border: 1px solid #1F2937;
        border-radius: 6px;
    }}
    QSplitter::handle {{
        background-color: #1F2937;
        width: 2px;
        margin: 4px 2px;
    }}
    """
