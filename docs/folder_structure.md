# Suggested simplified project structure

```text
CandyBarV2/
├── app/                  # existing runtime package
├── src/
│   ├── core/             # business logic and services
│   │   ├── mqtt_client.py
│   │   ├── persistence.py
│   │   ├── audio.py
│   │   └── networking.py
│   ├── ui/               # Qt/QML interface
│   │   ├── qml/
│   │   │   ├── App.qml
│   │   │   ├── MainDisplay.qml
│   │   │   ├── DisplayView.qml
│   │   │   ├── CustomerSiteQrOverlay.qml
│   │   │   ├── WelcomeSplash.qml
│   │   │   ├── ConnectionBanner.qml
│   │   │   └── global/
│   │   │       └── DisplayState.qml
│   ├── web/              # admin/public server files
│   └── assets/           # images, fonts, audio
├── fluentui/             # keep only if you want to preserve current theme support
├── scripts/
├── requirements.txt
├── run.py
└── docs/
```

## Notes
- This is a cleaner conceptual structure, not a forced rename of the existing code.
- The current app can stay working while you gradually move files into this shape.
- The most important files to keep visible are the QML UI files and the Python services.
