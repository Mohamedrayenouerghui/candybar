# CandyBarV2 simplified architecture

## 1. Core runtime
These are the files that actually power the app:

- app/main.py
  - startup
  - creates Qt app
  - wires services together
- app/mqtt_client.py
  - MQTT connection and message handling
- app/helper/DisplayPersistence.py
  - saves and reloads display state
- app/helper/AudioEngine.py
  - plays announcements
- app/helper/NetworkHelper.py
  - exposes URLs for admin/public access
- app/helper/UsageStats.py
  - keeps simple usage statistics

## 2. UI layer
These define the visible interface:

- app/imports/app/qml/App.qml
  - main window and fullscreen behavior
- app/imports/app/qml/MainDisplay.qml
  - screen composition and overlays
- app/imports/app/qml/DisplayView.qml
  - main queue display layout and animations
- app/imports/app/qml/global/DisplayState.qml
  - shared UI state and persistence bridge

## 3. Assets and resources
These support images/fonts/resources:

- app/imports/resource.qrc
- app/imports/resource_rc.py
- app/imports/app/qml/...
- background/
- sound/

## 4. Web/admin layer
Optional but part of the project:

- web/server.py
- web/admin.html
- web/public.html

## 5. FluentUI dependency
The app uses FluentUI only in a limited way:

- theme setup in App.qml
- QR component in CustomerSiteQrOverlay.qml
- import registration in app/main.py

It does not appear to use most of the large FluentUI control library directly.

## Recommended simplified folder structure

```text
CandyBarV2/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── mqtt_client.py
│   ├── helper/
│   │   ├── AudioEngine.py
│   │   ├── CategoryAudioHelper.py
│   │   ├── DisplayPersistence.py
│   │   ├── FontManager.py
│   │   ├── NetworkHelper.py
│   │   └── UsageStats.py
│   └── imports/
│       ├── resource.qrc
│       ├── resource_rc.py
│       └── app/
│           └── qml/
│               ├── App.qml
│               ├── MainDisplay.qml
│               ├── DisplayView.qml
│               ├── CustomerSiteQrOverlay.qml
│               ├── WelcomeSplash.qml
│               ├── ConnectionBanner.qml
│               └── global/
│                   └── DisplayState.qml
├── web/
│   ├── server.py
│   ├── admin.html
│   ├── public.html
│   └── mqtt.min.js
├── background/
├── sound/
├── scripts/
├── fluentui/
├── requirements.txt
├── run.py
└── docs/
```

## Keep vs optional
### Keep
- app/main.py
- app/mqtt_client.py
- app/helper/*
- app/imports/app/qml/*
- web/server.py (if you need admin/web control)
- fluentui/ (only if you want to preserve current theme/QR support)

### Optional
- scripts/
- CategoryAudioHelper.py
- UsageStats.py
- FontManager.py
- web/admin.html/public.html if you want a simpler kiosk-only version
