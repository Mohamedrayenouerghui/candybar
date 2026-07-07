"""
CandyBarV2 — kiosk queue display entry point.
"""

import os
import sys
import threading
import pathlib

from PySide6.QtCore import QUrl, QFile, QStandardPaths
from PySide6.QtGui import QGuiApplication, QFontDatabase
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface

from fluentui import FluentUI
from fluentui.FluLogger import LogSetup, Logger

from app.mqtt_client import MQTTClient
from app.helper.NetworkHelper import NetworkHelper
from app.helper.DisplayPersistence import DisplayPersistence
from app.helper.UsageStats import UsageStats
from app.helper.AudioEngine import AudioEngine
from app.helper.FontManager import FontManager
from app.imports import resource_rc as rc


def _copy_static_assets_to_data_dir(data_dir: str) -> None:
    pathlib.Path(data_dir).mkdir(parents=True, exist_ok=True)
    assets = [
        (":/app/res/image/noise_texture.png", "noise_texture.png"),
    ]
    for qrc_path, filename in assets:
        dest = os.path.join(data_dir, filename)
        if not os.path.exists(dest):
            qf = QFile(qrc_path)
            if qf.open(QFile.OpenModeFlag.ReadOnly):
                with open(dest, "wb") as f:
                    f.write(qf.readAll().data())
                qf.close()
                Logger().debug(f"Seeded {filename} → {dest}")


def _start_web_server(mqtt_client, display_persistence, usage_stats, font_manager):
    import web.server as srv
    t = threading.Thread(
        target=srv.run,
        args=(mqtt_client, display_persistence, usage_stats, font_manager),
        daemon=True,
    )
    t.start()


def main():
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)

    QGuiApplication.setOrganizationName("CandyBarV2")
    QGuiApplication.setOrganizationDomain("candybar.local")
    QGuiApplication.setApplicationName("CandyBarV2")
    QGuiApplication.setApplicationDisplayName("CandyBarV2")

    LogSetup("candybar")
    Logger().debug(f"Loading resource bundle: {rc.__name__}")

    app = QGuiApplication(sys.argv)

    _reg = QFontDatabase.addApplicationFont(":/app/res/font/DMMono-Regular.otf")
    _med = QFontDatabase.addApplicationFont(":/app/res/font/DMMono-Medium.otf")
    if _reg == -1 or _med == -1:
        Logger().debug("Warning: DM Mono font not loaded from QRC bundle")

    _data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )
    _copy_static_assets_to_data_dir(_data_dir)

    engine = QQmlApplicationEngine()
    FluentUI.registerTypes(engine)

    persistence = DisplayPersistence()
    usage_stats = UsageStats()
    network_helper = NetworkHelper()
    mqtt_client = MQTTClient()
    audio_engine = AudioEngine()
    font_manager = FontManager()

    audio_engine.set_data_dir(os.path.join(_data_dir, "audio"))
    font_manager.load_saved_fonts(_data_dir)

    ctx = engine.rootContext()
    ctx.setContextProperty("DisplayPersistence", persistence)
    ctx.setContextProperty("UsageStats", usage_stats)
    ctx.setContextProperty("NetworkHelper", network_helper)
    ctx.setContextProperty("MqttClient", mqtt_client)
    ctx.setContextProperty("AudioEngine", audio_engine)
    ctx.setContextProperty("FontManager", font_manager)

    mqtt_client.connect_broker()
    _start_web_server(mqtt_client, persistence, usage_stats, font_manager)

    engine.load(QUrl("qrc:/app/qml/App.qml"))
    if not engine.rootObjects():
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
