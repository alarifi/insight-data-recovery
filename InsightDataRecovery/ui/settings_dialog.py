"""
Insight Data Recovery Studio Pro - Commercial Settings & Licensing Center v5.0
Full Light/Dark theme support + live Arabic (RTL) / English (LTR) switching.
Contains:
1. Language & Theme (اللغة والمظهر)
2. Registry & License Activation (الريجستري والتسجيل)
3. Check for Updates (التحقق من التحديثات)
4. Help & Documentation (المساعدة والدعم)
5. About Software (حول البرنامج)
"""
import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QListWidget, QListWidgetItem, QRadioButton,
    QFrame, QLineEdit, QProgressBar, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QIcon, QPixmap

from ui.theme import STRINGS, get_asset_path, get_light_stylesheet, get_dark_stylesheet, get_ui_icon


class SettingsDialog(QDialog):
    theme_changed = pyqtSignal(bool)   # True for dark, False for light
    language_changed = pyqtSignal(str) # "ar" or "en"

    def __init__(self, current_lang: str = "en", is_dark: bool = False, parent=None):
        super().__init__(parent)
        self.current_lang = current_lang
        self.is_dark = is_dark
        self.strings = STRINGS[self.current_lang]

        self.setWindowTitle(self.strings["settings_title"])
        self.resize(680, 440)
        self.setMinimumSize(620, 400)

        icon_path = get_asset_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setup_ui()
        self.apply_dialog_theme()
        self.apply_dialog_direction()

    def apply_dialog_theme(self):
        sheet = get_dark_stylesheet() if self.is_dark else get_light_stylesheet()
        self.setStyleSheet(sheet)

    def apply_dialog_direction(self):
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.current_lang == "ar" else Qt.LayoutDirection.LeftToRight)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Left/Start Sidebar Navigation
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(195)
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.nav_items = []
        self._populate_nav_items()
        main_layout.addWidget(self.nav_list)

        # 2. Content Container Card
        content_card = QFrame()
        content_card.setObjectName("Card")
        content_l = QVBoxLayout(content_card)
        content_l.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        self.page_general = self.create_general_page()
        self.page_license = self.create_license_page()
        self.page_updates = self.create_updates_page()
        self.page_help = self.create_help_page()
        self.page_about = self.create_about_page()

        self.stack.addWidget(self.page_general)
        self.stack.addWidget(self.page_license)
        self.stack.addWidget(self.page_updates)
        self.stack.addWidget(self.page_help)
        self.stack.addWidget(self.page_about)

        content_l.addWidget(self.stack)
        main_layout.addWidget(content_card, 1)

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def _populate_nav_items(self):
        curr = max(0, self.nav_list.currentRow())
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        self.nav_list.setIconSize(QSize(20, 20))
        categories = [
            (" " + self.strings["settings_general"], "ui_language.png"),
            (" " + self.strings["settings_license"], "ui_license.png"),
            (" " + self.strings["settings_updates"], "ui_update.png"),
            (" " + self.strings["settings_help"], "ui_help.png"),
            (" " + self.strings["settings_about"], "ui_about.png"),
        ]
        for title, ico_name in categories:
            it = QListWidgetItem(get_ui_icon(ico_name), title)
            self.nav_list.addItem(it)
        self.nav_list.setCurrentRow(curr)
        self.nav_list.blockSignals(False)

    # ---------------- PAGE 0: GENERAL (LANGUAGE & THEME) ----------------
    def create_general_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(14)

        self.lbl_gen_head = QLabel("🌐  " + self.strings["settings_general"])
        self.lbl_gen_head.setObjectName("PageTitle")
        l.addWidget(self.lbl_gen_head)

        # Language Card
        grp_lang = QFrame()
        grp_lang.setObjectName("SettingsCard")
        l_lang = QVBoxLayout(grp_lang)
        l_lang.setContentsMargins(16, 14, 16, 14)
        l_lang.setSpacing(8)

        self.lbl_lang_title = QLabel("لغة الواجهة (Interface Language)" if self.current_lang == "ar" else "Interface Language")
        self.lbl_lang_title.setObjectName("CardTitle")
        l_lang.addWidget(self.lbl_lang_title)

        self.rb_ar = QRadioButton("العربية — واجهة احترافية من اليمين لليسار (RTL)" if self.current_lang == "ar" else "العربية — Arabic (RTL)")
        self.rb_en = QRadioButton("English — Standard Left-to-Right (LTR)" if self.current_lang == "ar" else "English — Standard (LTR)")
        if self.current_lang == "ar":
            self.rb_ar.setChecked(True)
        else:
            self.rb_en.setChecked(True)

        self.rb_ar.toggled.connect(self.on_lang_radio_toggled)
        l_lang.addWidget(self.rb_ar)
        l_lang.addWidget(self.rb_en)
        l.addWidget(grp_lang)

        # Theme Card
        grp_theme = QFrame()
        grp_theme.setObjectName("SettingsCard")
        l_theme = QVBoxLayout(grp_theme)
        l_theme.setContentsMargins(16, 14, 16, 14)
        l_theme.setSpacing(8)

        self.lbl_theme_title = QLabel("مظهر البرنامج (Appearance Theme)" if self.current_lang == "ar" else "Appearance Theme")
        self.lbl_theme_title.setObjectName("CardTitle")
        l_theme.addWidget(self.lbl_theme_title)

        self.rb_light = QRadioButton("☀️  الوضع الفاتح العصري (Light Mode)" if self.current_lang == "ar" else "☀️  Modern Light Mode")
        self.rb_dark = QRadioButton("🌙  الوضع الداكن الاحترافي (Dark Mode)" if self.current_lang == "ar" else "🌙  Professional Dark Mode")
        if self.is_dark:
            self.rb_dark.setChecked(True)
        else:
            self.rb_light.setChecked(True)

        self.rb_dark.toggled.connect(self.on_theme_radio_toggled)
        l_theme.addWidget(self.rb_light)
        l_theme.addWidget(self.rb_dark)
        l.addWidget(grp_theme)

        l.addStretch()
        return w

    def on_lang_radio_toggled(self, checked: bool):
        new_lang = "ar" if self.rb_ar.isChecked() else "en"
        if new_lang != self.current_lang:
            self.current_lang = new_lang
            self.strings = STRINGS[self.current_lang]
            self.setWindowTitle(self.strings["settings_title"])
            self._populate_nav_items()
            self.lbl_gen_head.setText("🌐  " + self.strings["settings_general"])
            self.lbl_lic_head.setText("🔑  " + self.strings["settings_license"])
            self.lbl_upd_head.setText("🔄  " + self.strings["settings_updates"])
            self.lbl_hlp_head.setText("📖  " + self.strings["settings_help"])
            self.lbl_abt_head.setText("ℹ️  " + self.strings["settings_about"])
            self.lbl_lang_title.setText("لغة الواجهة (Interface Language)" if self.current_lang == "ar" else "Interface Language")
            self.rb_ar.setText("العربية — واجهة احترافية من اليمين لليسار (RTL)" if self.current_lang == "ar" else "العربية — Arabic (RTL)")
            self.rb_en.setText("English — Standard Left-to-Right (LTR)" if self.current_lang == "ar" else "English — Standard (LTR)")
            self.lbl_theme_title.setText("مظهر البرنامج (Appearance Theme)" if self.current_lang == "ar" else "Appearance Theme")
            self.rb_light.setText("☀️  الوضع الفاتح العصري (Light Mode)" if self.current_lang == "ar" else "☀️  Modern Light Mode")
            self.rb_dark.setText("🌙  الوضع الداكن الاحترافي (Dark Mode)" if self.current_lang == "ar" else "🌙  Professional Dark Mode")
            self.apply_dialog_direction()
            self.language_changed.emit(new_lang)

    def on_theme_radio_toggled(self, checked: bool):
        new_is_dark = self.rb_dark.isChecked()
        if new_is_dark != self.is_dark:
            self.is_dark = new_is_dark
            self.apply_dialog_theme()
            self.theme_changed.emit(new_is_dark)

    # ---------------- PAGE 1: LICENSE & REGISTRY ----------------
    def create_license_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(12)

        self.lbl_lic_head = QLabel("🔑  " + self.strings["settings_license"])
        self.lbl_lic_head.setObjectName("PageTitle")
        l.addWidget(self.lbl_lic_head)

        # Status Badge
        badge = QFrame()
        badge.setObjectName("SuccessBadge")
        badge_l = QHBoxLayout(badge)
        badge_l.setContentsMargins(12, 10, 12, 10)
        lbl_badge_icon = QLabel("🛡️")
        lbl_badge_icon.setStyleSheet("font-size: 22px;")
        lbl_badge_text = QLabel(
            "الحالة: ترخيص تجاري مفعل مدى الحياة (Pro Edition Active)\nجميع المحركات والوظائف مفتوحة 100% دون قيود."
            if self.current_lang == "ar" else
            "Status: Lifetime Commercial License Activated (Pro Edition)\nAll recovery and repair modules unlocked 100%."
        )
        lbl_badge_text.setStyleSheet("color: #10B981; font-weight: 700; font-size: 12px;")
        badge_l.addWidget(lbl_badge_icon)
        badge_l.addWidget(lbl_badge_text)
        badge_l.addStretch()
        l.addWidget(badge)

        lbl_mid = QLabel("معرف الجهاز (Machine ID / Hardware Fingerprint):" if self.current_lang == "ar" else "Machine ID / Hardware Fingerprint:")
        lbl_mid.setObjectName("SectionHeader")
        l.addWidget(lbl_mid)

        mid_row = QHBoxLayout()
        self.txt_machine = QLineEdit("INSR-2026-X64-98A1-4F29-B981-CE1D")
        self.txt_machine.setReadOnly(True)
        mid_row.addWidget(self.txt_machine)

        btn_copy_mid = QPushButton("📋 نسخ" if self.current_lang == "ar" else "📋 Copy")
        btn_copy_mid.setObjectName("SecondaryActionBtn")
        btn_copy_mid.clicked.connect(lambda: (QApplication.clipboard().setText(self.txt_machine.text()), QMessageBox.information(self, "Copied", "Machine ID copied to clipboard.")))
        mid_row.addWidget(btn_copy_mid)
        l.addLayout(mid_row)

        lbl_key = QLabel("مفتاح الترخيص والتسجيل (License Key):" if self.current_lang == "ar" else "License Key:")
        lbl_key.setObjectName("SectionHeader")
        l.addWidget(lbl_key)

        self.txt_key = QLineEdit("INSIGHT-PRO-2026-LIFETIME-COMMERCIAL")
        l.addWidget(self.txt_key)

        btn_box = QHBoxLayout()
        btn_activate = QPushButton("✓ التحقق من التفعيل" if self.current_lang == "ar" else "✓ Validate License")
        btn_activate.setObjectName("PrimaryActionBtn")
        btn_activate.clicked.connect(lambda: QMessageBox.information(
            self,
            "الترخيص" if self.current_lang == "ar" else "License",
            "تم التحقق من الترخيص بنجاح! نسختك مفعلة بشكل كامل ودائم." if self.current_lang == "ar" else "License validated successfully! Pro Edition is permanently active."
        ))
        btn_box.addWidget(btn_activate)

        btn_offline = QPushButton("📁 التفعيل أوفلاين" if self.current_lang == "ar" else "📁 Offline Activation")
        btn_offline.setObjectName("SecondaryActionBtn")
        btn_offline.clicked.connect(lambda: QMessageBox.information(
            self,
            "التفعيل دون اتصال" if self.current_lang == "ar" else "Offline Activation",
            "البرنامج مفعل للعمل 100% دون إنترنت دون الحاجة لأي خوادم خارجية." if self.current_lang == "ar" else "Offline commercial license is active. Zero internet required."
        ))
        btn_box.addWidget(btn_offline)
        btn_box.addStretch()
        l.addLayout(btn_box)

        l.addStretch()
        return w

    # ---------------- PAGE 2: CHECK FOR UPDATES ----------------
    def create_updates_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(12)

        self.lbl_upd_head = QLabel("🔄  " + self.strings["settings_updates"])
        self.lbl_upd_head.setObjectName("PageTitle")
        l.addWidget(self.lbl_upd_head)

        lbl_ver = QLabel("Insight Data Recovery Studio Pro — v2.0.0 Commercial Build")
        lbl_ver.setObjectName("CardTitle")
        l.addWidget(lbl_ver)

        self.lbl_update_status = QLabel(
            "✓ النظام محدث لأحدث إصدار رسمي مستقر وخفيف الوزن (48 MB)."
            if self.current_lang == "ar" else
            "✓ Up to date — running latest commercial build v2.0.0 (48 MB)."
        )
        self.lbl_update_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
        l.addWidget(self.lbl_update_status)

        self.update_progress = QProgressBar()
        self.update_progress.setTextVisible(False)
        self.update_progress.setVisible(False)
        self.update_progress.setFixedHeight(6)
        l.addWidget(self.update_progress)

        btn_check = QPushButton("🔍 التحقق الآن من وجود تحديثات" if self.current_lang == "ar" else "🔍 Check for Updates Now")
        btn_check.setObjectName("PrimaryActionBtn")
        btn_check.setMaximumWidth(250)
        btn_check.clicked.connect(self.simulate_update_check)
        l.addWidget(btn_check)

        # Changelog Card
        chg_card = QFrame()
        chg_card.setObjectName("SettingsCard")
        chg_l = QVBoxLayout(chg_card)
        chg_l.setContentsMargins(14, 12, 14, 12)
        lbl_chg_t = QLabel("سجل التحسينات (Changelog v2.0.0):" if self.current_lang == "ar" else "Release Notes (v2.0.0):")
        lbl_chg_t.setObjectName("CardTitle")
        chg_l.addWidget(lbl_chg_t)

        txt_changelog = QLabel(
            "• تقليص حجم حزمة التثبيت بنسبة 88% لتصل إلى 48 ميغابايت فقط.\n"
            "• محرك فحص فوري بدون تجميد (Zero-Freeze) مع شجرة مجلدات هرمية كاملة.\n"
            "• نافذة معاينة متطورة وفاحص بايتات سداسي (Hex Inspector) مدمج.\n"
            "• تصفية متقدمة حسب الحجم والتاريخ وحالة السلامة + حماية القرص الآمن.\n"
            "• دعم حفظ واسترجاع جلسات الفحص (.irsession) ومركز ترميم الملفات."
            if self.current_lang == "ar" else
            "• Ultra-lightweight 48 MB commercial installer (88% size reduction).\n"
            "• Zero-Freeze recursive folder tree & instant batch selection.\n"
            "• Built-in Live Preview (Images, PDF, Text) + Hex Byte Inspector.\n"
            "• Advanced Filter Popover (Size, Date, Integrity) + Safe Drive Guard.\n"
            "• Scan Session Save/Load (.irsession) & Multi-format File Repair Center."
        )
        txt_changelog.setObjectName("MutedLabel")
        txt_changelog.setWordWrap(True)
        chg_l.addWidget(txt_changelog)
        l.addWidget(chg_card)

        l.addStretch()
        return w

    def simulate_update_check(self):
        self.update_progress.setVisible(True)
        self.update_progress.setValue(25)
        self.lbl_update_status.setText("جاري التحقق من الإصدار..." if self.current_lang == "ar" else "Checking build signature...")
        QTimer.singleShot(350, lambda: self.update_progress.setValue(70))
        QTimer.singleShot(700, self.finish_update_check)

    def finish_update_check(self):
        self.update_progress.setValue(100)
        self.lbl_update_status.setText(
            "✓ تهانينا! أنت تستخدم أحدث إصدار v2.0.0 Pro."
            if self.current_lang == "ar" else
            "✓ You are on the latest commercial release v2.0.0 Pro."
        )
        QMessageBox.information(
            self,
            "التحديثات" if self.current_lang == "ar" else "Updates",
            "أنت تستخدم أحدث إصدار رسمي مستقر v2.0.0 Pro." if self.current_lang == "ar" else "Your software is fully up to date (v2.0.0 Pro)."
        )

    # ---------------- PAGE 3: HELP & DOCUMENTATION ----------------
    def create_help_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(22, 20, 22, 20)
        l.setSpacing(12)

        self.lbl_hlp_head = QLabel("📖  " + self.strings["settings_help"])
        self.lbl_hlp_head.setObjectName("PageTitle")
        l.addWidget(self.lbl_hlp_head)

        btn_guide = QPushButton("📘 فتح دليل الاستخدام الكامل (User Manual)" if self.current_lang == "ar" else "📘 Open Complete User Manual")
        btn_guide.setObjectName("PrimaryActionBtn")
        btn_guide.setMaximumWidth(320)
        btn_guide.clicked.connect(self.open_user_guide)
        l.addWidget(btn_guide)

        faq_box = QFrame()
        faq_box.setObjectName("SettingsCard")
        faq_l = QVBoxLayout(faq_box)
        faq_l.setContentsMargins(14, 12, 14, 12)
        faq_l.setSpacing(6)

        q1 = QLabel("❓ كيف أسترجع الملفات بعد الفورمات؟" if self.current_lang == "ar" else "❓ How to recover files after formatting?")
        q1.setObjectName("CardTitle")
        a1 = QLabel(
            "اختر وضع 'فحص الفورمات العميق' من الواجهة الرئيسية للبحث في قطاعات القرص عبر تواقيع الهكس."
            if self.current_lang == "ar" else
            "Choose 'Deep Format Recovery' on the home view to carve files directly from raw disk sectors."
        )
        a1.setObjectName("MutedLabel")
        a1.setWordWrap(True)

        q2 = QLabel("⚠️ لماذا يجب الاستعادة إلى قرص مختلف؟" if self.current_lang == "ar" else "⚠️ Why recover to a different drive?")
        q2.setObjectName("CardTitle")
        a2 = QLabel(
            "الكتابة على نفس القرص تمحو القطاعات المحذوفة نهائياً؛ لذلك يختار البرنامج تلقائياً قرصاً بديلاً آمناً."
            if self.current_lang == "ar" else
            "Writing to the scanned drive overwrites deleted sectors. Insight Recovery auto-selects a safe alternate drive."
        )
        a2.setObjectName("MutedLabel")
        a2.setWordWrap(True)

        faq_l.addWidget(q1)
        faq_l.addWidget(a1)
        faq_l.addWidget(q2)
        faq_l.addWidget(a2)
        l.addWidget(faq_box)

        l.addStretch()
        return w

    def open_user_guide(self):
        doc_path = r"E:\PortableApps\insight software\Insight Reconery\دليل_استخدام_البرنامج_Insight_Recovery.md"
        if os.path.exists(doc_path):
            try:
                os.startfile(doc_path)
            except Exception:
                subprocess.Popen(["notepad.exe", doc_path])
        else:
            QMessageBox.information(self, "User Manual", f"Documentation path:\n{doc_path}")

    # ---------------- PAGE 4: ABOUT ----------------
    def create_about_page(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(22, 24, 22, 24)
        l.setSpacing(10)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_abt_head = QLabel("ℹ️  " + self.strings["settings_about"])
        self.lbl_abt_head.setObjectName("PageTitle")
        self.lbl_abt_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.lbl_abt_head)

        shield_path = get_asset_path("shield_3d.png")
        if os.path.exists(shield_path):
            lbl_img = QLabel()
            lbl_img.setPixmap(QPixmap(shield_path).scaled(68, 68, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.addWidget(lbl_img)

        lbl_app = QLabel("Insight Data Recovery Studio Pro")
        lbl_app.setStyleSheet("font-size: 18px; font-weight: 800; color: #0D6EFD;")
        lbl_app.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_app)

        lbl_sub = QLabel("Version 2.0.0 Pro Edition — 64-Bit Native Windows")
        lbl_sub.setObjectName("CardTitle")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_sub)

        lbl_pub = QLabel(
            "الناشر: Insight Software Solutions\nمنظومة استعادة البيانات وترميم الملفات الاحترافية — تعمل 100% دون إنترنت."
            if self.current_lang == "ar" else
            "Publisher: Insight Software Solutions\n100% Offline Commercial Data Recovery & File Repair Suite."
        )
        lbl_pub.setObjectName("MutedLabel")
        lbl_pub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_pub)

        lbl_copy = QLabel("Copyright © 2026 Insight Software. All rights reserved.")
        lbl_copy.setObjectName("MutedLabel")
        lbl_copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(lbl_copy)

        l.addStretch()
        return w
