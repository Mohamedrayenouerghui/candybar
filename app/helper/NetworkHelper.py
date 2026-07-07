"""
NetworkHelper — exposes LAN IP, public tracking URL, admin URL, and official
site URL to QML.

publicUrl  → http://<LAN-IP>:8080/          (read-only customer tracking page)
adminUrl   → http://<LAN-IP>:8080/admin     (PIN-protected staff page)
siteUrl    → CANDYBAR_SITE_URL constant    (official marketing / info site)
"""

import socket

from PySide6.QtCore import QObject, Property, Signal

# Single place to update the official site URL shown on the display QR.
CANDYBAR_SITE_URL = "https://candybarv2.app"

PUBLIC_PORT = 8080


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class NetworkHelper(QObject):
    publicUrlChanged = Signal()
    adminUrlChanged = Signal()
    siteUrlChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        ip = _get_local_ip()
        self._public_url = f"http://{ip}:{PUBLIC_PORT}/"
        self._admin_url = f"http://{ip}:{PUBLIC_PORT}/admin"
        self._site_url = CANDYBAR_SITE_URL
        print("")
        print("┌─────────────────────────────────────────────────┐")
        print("│              CandyBarV2  —  ready               │")
        print("├─────────────────────────────────────────────────┤")
        print(f"│  Admin panel  :  {self._admin_url:<31}│")
        print(f"│  Public page  :  {self._public_url:<31}│")
        print(f"│  Site URL     :  {self._site_url:<31}│")
        print("└─────────────────────────────────────────────────┘")
        print("")

    @Property(str, notify=publicUrlChanged)
    def publicUrl(self) -> str:
        return self._public_url

    @Property(str, notify=adminUrlChanged)
    def adminUrl(self) -> str:
        return self._admin_url

    @Property(str, notify=siteUrlChanged)
    def siteUrl(self) -> str:
        return self._site_url
