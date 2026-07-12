"""
DisplayPersistence — saves/loads all display state to disk immediately on
every change.  A power loss must not reset customization.

Storage: QSettings INI at AppLocalDataLocation/candybar_display.ini
Logo:    AppLocalDataLocation/logo.<ext>  (copied on upload, path stored)
Fonts:   AppLocalDataLocation/fonts/*.ttf|otf
Background: AppLocalDataLocation/background.<ext>
"""

import os
import shutil

from PySide6.QtCore import QObject, Slot, QStandardPaths, QSettings
from PySide6.QtGui import QGuiApplication

from fluentui.Singleton import Singleton

_DATA_DIR = QStandardPaths.writableLocation(
    QStandardPaths.StandardLocation.AppLocalDataLocation
)


def _data_dir() -> str:
    os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


@Singleton
class DisplayPersistence(QObject):
    def __init__(self):
        super().__init__(QGuiApplication.instance())
        self._ini_path = os.path.join(_data_dir(), "candybar_display.ini")

    # ── generic helpers ────────────────────────────────────────────────
    @Slot(str, 'QVariant')
    def save(self, key: str, value) -> None:
        s = QSettings(self._ini_path, QSettings.Format.IniFormat)
        s.setValue(key, value)
        s.sync()

    @Slot(str, 'QVariant', result='QVariant')
    def load(self, key: str, default=None):
        s = QSettings(self._ini_path, QSettings.Format.IniFormat)
        v = s.value(key)
        return v if v is not None else default

    # ── logo file handling ─────────────────────────────────────────────
    @Slot(str, result=str)
    def save_logo(self, src_path: str) -> str:
        """Copy uploaded logo to data dir, return the new absolute path."""
        ext = os.path.splitext(src_path)[1].lower() or ".png"
        dest = os.path.join(_data_dir(), f"logo{ext}")
        shutil.copy2(src_path, dest)
        self.save("logoPath", dest)
        return dest

    @Slot(result=str)
    def logo_path(self) -> str:
        return self.load("logoPath", "")

    def background_path(self) -> str:
        bg = self.load("backgroundImage", "")
        if bg and not bg.startswith("qrc:") and os.path.isfile(bg):
            return bg
        return bg

    # ── PIN ────────────────────────────────────────────────────────────
    @Slot(result=str)
    def get_pin(self) -> str:
        return str(self.load("adminPin", "1234"))

    @Slot(str)
    def set_pin(self, pin: str) -> None:
        self.save("adminPin", pin)

    # ── convenience read helpers (used by server.py _build_state) ──────
    def get_current_number(self) -> str:
        return str(self.load("currentNumber", "001"))

    @Slot(result='QVariantList')
    def get_next_up(self) -> list:
        raw = self.load("nextUp", "")
        if not raw:
            return []
        return [x.strip() for x in str(raw).split(",") if x.strip()]

    def get_layout(self) -> str:
        return str(self.load("layoutType", "Classic"))

    def get_accent(self) -> str:
        return str(self.load("accentColor", "#FFB84D"))

    def get_banner(self) -> str:
        return str(self.load("bannerText", "Welcome — please wait for your number to be called"))

    def get_facility(self) -> str:
        return str(self.load("facilityName", "CandyBar Service Centre"))

    def get_font_size(self) -> int:
        """Return the continuous font size (48–200px). Default 96."""
        v = self.load("fontSize", 96)
        try:
            fs = int(v)
            return fs if 48 <= fs <= 200 else 96
        except (TypeError, ValueError):
            return 96

    def get_logo_size(self) -> int:
        """Return the logo container height (24–120px). Default 48."""
        v = self.load("logoSize", 48)
        try:
            ls = int(v)
            return ls if 24 <= ls <= 120 else 48
        except (TypeError, ValueError):
            return 48

    def get_text_size(self, key: str, default: int) -> int:
        v = self.load(key, default)
        try:
            val = int(v)
            return val if 8 <= val <= 240 else default
        except (TypeError, ValueError):
            return default

    def get_display_language(self) -> str:
        """Return the display language code (en / fr / ar). Default en."""
        v = str(self.load("displayLanguage", "en"))
        return v if v in ("en", "fr", "ar") else "en"
