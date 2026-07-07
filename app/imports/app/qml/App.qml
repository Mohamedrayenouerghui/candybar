import QtQuick 2.15
import QtQuick.Window 2.15
import FluentUI 1.0
import "global"

// Pure kiosk app — no routing, no navigation shell, one window, one view.

Window {
    id: root
    visible: true
    visibility: Window.FullScreen
    color: "#0d0f12"
    title: "CandyBarV2"

    Component.onCompleted: {
        FluTheme.darkMode = FluThemeType.DarkMode.Dark
        FluTheme.animationEnabled = true

        // Populate URLs from NetworkHelper
        DisplayState.publicUrl = NetworkHelper.publicUrl
        DisplayState.adminUrl  = NetworkHelper.adminUrl
        DisplayState.siteUrl   = NetworkHelper.siteUrl

        // Load persisted display settings from disk
        DisplayState.loadFromDisk()
    }
    Connections {
        target: MqttClient
        function onConnectedChanged()              { DisplayState.mqttConnected = MqttClient.connected }
        function onConnectionStatusChanged(status) { DisplayState.mqttStatus    = status }
        function onDisplayCommandReceived(key, val){ DisplayState.applyMqttCommand(key, val) }
    }

    // Sync category to MqttClient after loading from disk
    Connections {
        target: DisplayState
        function onCategoryChanged() { MqttClient.category = DisplayState.category }
    }

    // ── The single full-screen display item ─────────────────────────────
    MainDisplay {
        anchors.fill: parent
    }

    // ── Keyboard shortcuts (kiosk management) ────────────────────────────
    // Escape or Super+M → exit fullscreen to windowed (for maintenance)
    // Super+Q          → close the app
    Item {
        focus: true
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Escape) {
                root.showNormal()
                root.width  = 1280
                root.height = 720
                event.accepted = true
            } else if (event.key === Qt.Key_M && (event.modifiers & Qt.MetaModifier)) {
                root.showMinimized()
                event.accepted = true
            } else if (event.key === Qt.Key_Q && (event.modifiers & Qt.MetaModifier)) {
                Qt.quit()
                event.accepted = true
            }
        }
    }
}
