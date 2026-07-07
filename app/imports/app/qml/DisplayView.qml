import QtQuick 2.15
import QtQuick.Layouts 1.15
import FluentUI 1.0
import "global"

// ── DisplayView ──────────────────────────────────────────────────────────
// The permanent, always-on display. Hosts Classic, Split, and Centered layouts.
// All three stay in the tree; opacity crossfade switches between them.
//
// Hierarchy (3-meter read test, highest to lowest):
//   1. NUMBER        — commands the screen, heaviest weight, largest size
//   2. CATEGORY      — now a high-contrast BADGE, bold, unmissable, tier 2
//   3. "NOW SERVING" — whisper label, small, subordinate
//   4. Everything else (facility, clock, banner, next-up) — clearly tertiary
//
// ── WHY THE CATEGORY WAS INVISIBLE ───────────────────────────────────────
// The old CategoryTitle rendered as bare text in `accent_gold` directly on
// top of a photographic background with no guaranteed contrast surface.
// On warm/bright backgrounds the gold text blended straight into the photo.
// The number survives this because it's huge + white + heavily weighted;
// the (much smaller) category never could.
//
// FIX: the category is now a self-contained "badge" — a translucent,
// bordered pill that carries its own contrast independent of whatever
// photo is behind it — combined with a soft glass card behind the whole
// number+category stack so BOTH stay legible on any background image.
//
// Motion: number change = lift+shrink+fade out (150ms InCubic),
//         then rise+grow+fade in (300ms OutQuart) — GPU-only transforms

Item {
    id: root
    anchors.fill: parent

    // ── Timing constants ─────────────────────────────────────────────────
    readonly property int dur_micro: 150   // number exit
    readonly property int dur_std:   300   // number entrance / state transitions
    readonly property int dur_full:  600   // layout crossfade / color transitions

    // ── Radius tokens ────────────────────────────────────────────────────
    readonly property int radius_outer: 20
    readonly property int radius_card:  14
    readonly property int radius_chip:  12

    // ── Typography scale ─────────────────────────────────────────────────
    // numScale: multiplier so the number fills the screen proportionally
    readonly property real numScale: Math.max(root.height / 480.0, 0.8)

    // Per-layout number multipliers — Centered gets the most room
    readonly property real numLayoutClassic:  1.00
    readonly property real numLayoutSplit:    1.10
    readonly property real numLayoutCentered: 1.30

    // DESIGN CHANGE: category is now sized as a larger fraction of the number
    // (0.32–0.38 instead of the old 0.24–0.28) so it reads clearly as its
    // own tier rather than a caption. Because it now lives inside a badge
    // with guaranteed contrast, it can afford to be bigger without
    // competing visually with the number.
    readonly property real catScaleClassic:  0.34
    readonly property real catScaleSplit:    0.32
    readonly property real catScaleCentered: 0.38

    // Tight tracking — binds digits into one readable unit at distance
    readonly property int numLetterSpacing: -3

    // Optical lift — focal pair sits slightly above geometric center
    readonly property real numOpticalLift: -Math.max(root.height * 0.04, 16)

    // ── Color palette ────────────────────────────────────────────────────
    readonly property color text_primary:   "#FFFFFF"
    readonly property color text_secondary: Qt.lighter(DisplayState.accentColor, 1.55)
    readonly property color text_tertiary:  Qt.lighter(DisplayState.accentColor, 1.28)
    property color accent_gold:     DisplayState.accentColor
    property color accent_gold_dim: Qt.rgba(DisplayState.accentColor.r,
                                            DisplayState.accentColor.g,
                                            DisplayState.accentColor.b, 0.15)

    // Glass card behind the whole number+category stack — a soft, neutral
    // dark scrim that guarantees a stable contrast surface no matter what
    // photo is loaded as the background.
    readonly property color glass_fill:   Qt.rgba(0, 0, 0, 0.32)
    readonly property color glass_border: Qt.rgba(1, 1, 1, 0.14)
    readonly property color glass_shadow: Qt.rgba(0, 0, 0, 0.28)
    readonly property color glass_highlight: Qt.rgba(1, 1, 1, 0.08)

    // Reusable glass-card background: soft outer shadow + fill + border +
    // a faint top highlight streak, so it reads as a lifted glass panel
    // rather than a flat dark rectangle.
    component GlassCard: Item {
        Rectangle {
            id: shadowLayer
            anchors.fill: parent
            anchors.margins: -6
            radius: root.radius_outer + 6
            color: root.glass_shadow
        }
        Rectangle {
            anchors.fill: parent
            radius: root.radius_outer
            color: root.glass_fill
            border.width: 1
            border.color: root.glass_border
            clip: true

            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: parent.height * 0.5
                radius: root.radius_outer
                color: root.glass_highlight
            }
        }
    }

    // ── Shared components ────────────────────────────────────────────────

    // CategoryBadge: redesigned from a thick, fully-rounded "pill/counter chip"
    // into a refined rectangular tag — a left accent bar + small dot instead
    // of a heavy colored outline, softer neutral glass fill, tighter corners.
    // This reads as a proper category label rather than a counter-style badge.
    component CategoryBadge: Item {
    property real numPx: 96
    property real catScale: 0.34

    // Fixed clearance from the left accent bar to the dot/text, so they
    // never visually collide regardless of implicit-size rounding.
    readonly property int _leftPad:  26
    readonly property int _rightPad: 22

    Layout.alignment: Qt.AlignHCenter
    Layout.preferredWidth:  catRow.implicitWidth + _leftPad + _rightPad
    Layout.preferredHeight: catRow.implicitHeight + 22

    Rectangle {
        id: tagBg
        anchors.fill: parent
        radius: root.radius_card
        color: Qt.rgba(0, 0, 0, 0.34)
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.12)
        clip: true

        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 6
            color: root.accent_gold
            Behavior on color { ColorAnimation { duration: root.dur_full } }
        }
    }

    RowLayout {
        id: catRow
        anchors {
            left: parent.left
            leftMargin: parent._leftPad
            verticalCenter: parent.verticalCenter
        }
        spacing: 8

        Rectangle {
            Layout.alignment: Qt.AlignVCenter
            width: 10
            height: 10
            radius: 5
            color: root.accent_gold
            Behavior on color { ColorAnimation { duration: root.dur_full } }
        }

        Text {
            id: catText
            Layout.maximumWidth: root.width * 0.9
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            text: DisplayState.categoryDisplayName.toUpperCase()
            font.family: DisplayState.categoryFont || DisplayState.numberFont
            font.pixelSize: Math.max(DisplayState.categoryFontSize || (numPx * catScale), 20)
            font.weight: Font.Bold
            font.letterSpacing: 1.5
            color: "#FFFFFF"
            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.65)
        }
    }
}

    // NowServingLabel: still the smallest tier, but now clearly readable —
    // bumped from Font.Light to Font.Bold, higher opacity, and pure white
    // instead of the tinted secondary color so it doesn't wash out against
    // the glass card.
    component NowServingLabel: Text {
        Layout.alignment: Qt.AlignHCenter
        text: "NOW SERVING"
        font.family: DisplayState.nowServingFont || DisplayState.numberFont
        font.pixelSize: Math.max(DisplayState.nowServingFontSize || Math.max(root.height * 0.021, 11), 10)
        font.letterSpacing: 5
        font.weight: Font.Bold
        color: root.text_primary
        opacity: 0.85
        style: Text.Raised
        styleColor: Qt.rgba(0, 0, 0, 0.65)
    }

    // ServingNumber: the dominant element — maximum weight, animated
    component ServingNumber: Item {
        property real layoutMult: 1.0

        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth:  numText.implicitWidth
        Layout.preferredHeight: numText.implicitHeight
        opacity: root._numOpacity
        scale:   root._numScale
        transformOrigin: Item.Center
        transform: Translate { y: root._numTranslateY }

        Text {
            id: numText
            anchors.centerIn: parent
            text: root._shownNumber
            font.family:       DisplayState.numberFont
            font.pixelSize:    Math.max(DisplayState.numberFontSize || (DisplayState.fontSize * root.numScale * layoutMult), 12)
            font.weight:       Font.Black   // heaviest available weight
            font.letterSpacing: root.numLetterSpacing
            renderType:        Text.NativeRendering
            color:             root.text_primary
            style:             Text.Raised
            styleColor:        Qt.rgba(0, 0, 0, 0.70)
        }
    }

    // AccentUnderline ("candy bar"): ties number+category together visually.
    // DESIGN CHANGE: was 4px and could fade to fully transparent on one end
    // via the gradient, making it read as invisible. Now it's thicker (8px),
    // sits on a soft glow layer for extra contrast, and the gradient never
    // drops below a visible minimum opacity — it tapers, it doesn't vanish.
    component AccentUnderline: Item {
        property real layoutMult: 1.0

        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth:  glow.width
        Layout.preferredHeight: glow.height
        opacity: root._numOpacity
        scale:   root._numScale
        transformOrigin: Item.Center
        transform: Translate { y: root._numTranslateY * 0.35 }

        // Soft glow layer behind the bar — wider + softer, boosts perceived
        // contrast without changing the bar's crisp shape.
        Rectangle {
            id: glow
            anchors.centerIn: parent
            width:  bar.width + 24
            height: 14
            radius: height / 2
            color: Qt.rgba(root.accent_gold.r, root.accent_gold.g, root.accent_gold.b, 0.35)
        }

        Rectangle {
            id: bar
            anchors.centerIn: parent
            width:  Math.max(56, DisplayState.fontSize * root.numScale * layoutMult * 0.46)
            height: 8
            radius: 4
            color: DisplayState.accentGradientEnabled ? "transparent" : root.accent_gold
            gradient: DisplayState.accentGradientEnabled ? accentGrad : null
            border.width: 1
            border.color: Qt.rgba(1, 1, 1, 0.35)
            Gradient {
                id: accentGrad
                orientation: DisplayState.accentGradientDirection === "top-to-bottom"
                             ? Gradient.Vertical : Gradient.Horizontal
                // Tapers to a dimmed version of the accent color instead of
                // full transparency, so the bar never has an invisible end.
                GradientStop { position: 0.0; color: root.accent_gold }
                GradientStop { position: 1.0; color: Qt.rgba(root.accent_gold.r, root.accent_gold.g, root.accent_gold.b, 0.35) }
            }
            Behavior on color { ColorAnimation { duration: root.dur_full } }
        }
    }

    // ── Background ───────────────────────────────────────────────────────
    Image {
        anchors.fill: parent
        source:   DisplayState.backgroundImage
        fillMode: Image.PreserveAspectCrop
        asynchronous: false
        cache:  false
        smooth: true
    }

    // Dark scrim — enough for text contrast, not so much it kills the image
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.22)
    }

    // ── Number change animation ──────────────────────────────────────────
    // Phase 1 (exit): lift + shrink + fade  →  150ms InCubic
    // Phase 2 (enter): drop in + grow + fade →  300ms OutQuart
    property string _shownNumber:   DisplayState.currentNumber
    property real   _numOpacity:    1.0
    property real   _numScale:      1.0
    property real   _numTranslateY: 0

    readonly property real _numOutScale:    0.86
    readonly property real _numInFromScale: 0.90
    readonly property real _numOutLift:     Math.max(root.height * 0.022, 8)
    readonly property real _numInDrop:      Math.max(root.height * 0.028, 10)

    function _resetNumberAnim() {
        _numOpacity    = 1.0
        _numScale      = 1.0
        _numTranslateY = 0
    }

    onVisibleChanged: {
        if (visible) {
            _shownNumber = DisplayState.currentNumber
            _resetNumberAnim()
        }
    }

    Connections {
        target: DisplayState
        function onCurrentNumberChanged() {
            if (_shownNumber === DisplayState.currentNumber) return
            num_change_anim.stop()
            num_change_anim.start()
        }
    }

    SequentialAnimation {
        id: num_change_anim
        alwaysRunToEnd: false

        ParallelAnimation {
            NumberAnimation { target: root; property: "_numOpacity";    to: 0;                duration: root.dur_micro; easing.type: Easing.InCubic }
            NumberAnimation { target: root; property: "_numScale";      to: root._numOutScale; duration: root.dur_micro; easing.type: Easing.InCubic }
            NumberAnimation { target: root; property: "_numTranslateY"; to: -root._numOutLift; duration: root.dur_micro; easing.type: Easing.InCubic }
        }
        ScriptAction {
            script: {
                root._shownNumber   = DisplayState.currentNumber
                root._numTranslateY = root._numInDrop
                root._numScale      = root._numInFromScale
                root._numOpacity    = 0
            }
        }
        ParallelAnimation {
            NumberAnimation { target: root; property: "_numOpacity";    to: 1;   duration: root.dur_std; easing.type: Easing.OutQuart }
            NumberAnimation { target: root; property: "_numScale";      to: 1.0; duration: root.dur_std; easing.type: Easing.OutQuart }
            NumberAnimation { target: root; property: "_numTranslateY"; to: 0;   duration: root.dur_std; easing.type: Easing.OutQuart }
        }
    }

    // ── Layout crossfade controller ──────────────────────────────────────
    property real _classicOpacity:  1
    property real _splitOpacity:    0
    property real _centeredOpacity: 0

    Behavior on _classicOpacity  { NumberAnimation { duration: dur_full; easing.type: Easing.OutCubic } }
    Behavior on _splitOpacity    { NumberAnimation { duration: dur_full; easing.type: Easing.OutCubic } }
    Behavior on _centeredOpacity { NumberAnimation { duration: dur_full; easing.type: Easing.OutCubic } }

    function _applyLayout(lt) {
        _classicOpacity  = (lt === "Classic")  ? 1 : 0
        _splitOpacity    = (lt === "Split")    ? 1 : 0
        _centeredOpacity = (lt === "Centered") ? 1 : 0
    }

    Connections {
        target: DisplayState
        function onLayoutTypeChanged() { root._applyLayout(DisplayState.layoutType) }
    }

    Component.onCompleted: _applyLayout(DisplayState.layoutType)

    // ════════════════════════════════════════════════════════════════════
    // CLASSIC LAYOUT
    // Header bar: logo + facility name + clock (all tertiary)
    // Center:     glass card ▸ NowServingLabel → CategoryBadge → Number → Underline
    // Footer:     scrolling banner ticker
    // ════════════════════════════════════════════════════════════════════
    Item {
        id: classic_layout
        anchors.fill: parent
        opacity: root._classicOpacity
        visible: opacity > 0

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── Header bar ───────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(root.height * 0.11, 52)
                color: Qt.rgba(0, 0, 0, 0.52)

                RowLayout {
                    anchors { fill: parent; leftMargin: 24; rightMargin: 24 }
                    spacing: 14

                    // Logo
                    Rectangle {
                        width:  DisplayState.logoSize
                        height: DisplayState.logoSize
                        radius: root.radius_chip
                        color:  root.accent_gold_dim
                        visible: DisplayState.logoVisible
                        Behavior on color { ColorAnimation { duration: root.dur_full } }
                        Image {
                            anchors { fill: parent; margins: Math.max(3, DisplayState.logoSize * 0.07) }
                            source:   DisplayState.logoSource
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                            sourceSize: Qt.size(DisplayState.logoSize * 2, DisplayState.logoSize * 2)
                        }
                    }

                    // Facility name — tertiary, fills remaining header space
                    Text {
                        text:            DisplayState.facilityName
                        font.family:     DisplayState.facilityFont || DisplayState.numberFont
                        font.pixelSize:  Math.max(DisplayState.facilityFontSize || Math.max(root.height * 0.026, 13), 10)
                        font.weight:     Font.Light
                        color:           "#FFFFFF"
                        opacity:         0.55
                        elide:           Text.ElideRight
                        Layout.fillWidth: true
                        style:           Text.Raised
                        styleColor:      Qt.rgba(0, 0, 0, 0.6)
                    }

                    // Clock — tertiary
                    Text {
                        id: clock_classic
                        font.family:    DisplayState.numberFont
                        font.pixelSize: Math.max(root.height * 0.024, 12)
                        font.weight:    Font.Light
                        color:          "#FFFFFF"
                        opacity:        0.38
                        style:          Text.Raised
                        styleColor:     Qt.rgba(0, 0, 0, 0.5)
                    }
                    Timer {
                        interval: 1000; repeat: true; running: classic_layout.visible
                        onTriggered: clock_classic.text = Qt.formatTime(new Date(), "HH:mm")
                    }
                }
            }

            // ── Center stage — the only thing that matters ────────────────
            Item {
                Layout.fillWidth:  true
                Layout.fillHeight: true

                // Glass card wrapper: sized to the content column plus
                // padding, gives the whole stack a stable contrast surface
                // independent of the background photo.
                Item {
                    id: classic_center_wrap
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: root.numOpticalLift
                    width:  classic_content_col.implicitWidth  + 80
                    height: classic_content_col.implicitHeight + 56

                    GlassCard { anchors.fill: parent }

                    ColumnLayout {
                        id: classic_content_col
                        anchors.centerIn: parent
                        spacing: 0

                        // 1. Whisper label
                        NowServingLabel {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: Math.max(root.height * 0.012, 8)
                        }

                        // 2. Category — now a high-contrast badge
                        CategoryBadge {
                            numPx: DisplayState.fontSize * root.numScale * root.numLayoutClassic
                            catScale: root.catScaleClassic
                            Layout.bottomMargin: Math.max(root.height * 0.016, 10)
                        }

                        // 3. NUMBER — dominant
                        ServingNumber {
                            layoutMult: root.numLayoutClassic
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: Math.max(root.height * 0.014, 8)
                        }

                        // 4. Accent underline
                        AccentUnderline {
                            layoutMult: root.numLayoutClassic
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }

            // ── Footer banner ticker ──────────────────────────────────────
            // DESIGN CHANGE: bolder weight + white + much higher opacity so
            // it's actually legible, and the scroll animation now runs
            // unconditionally (not gated on layout visibility) so it never
            // stalls or has to restart — it's always moving.
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(root.height * 0.09, 40)
                color: Qt.rgba(0, 0, 0, 0.42)
                clip: true
                visible: DisplayState.bannerEnabled

                Row {
                    id: ticker_row_classic
                    height: parent.height
                    spacing: 96
                    Repeater {
                        model: 3
                        Text {
                            height:            ticker_row_classic.height
                            verticalAlignment: Text.AlignVCenter
                            text:              "  ·  " + DisplayState.bannerText
                            font.family:       DisplayState.bannerFont || DisplayState.numberFont
                            font.pixelSize:    Math.max(DisplayState.bannerFontSize || Math.max(root.height * 0.025, 12), 10)
                            font.weight:       Font.DemiBold
                            color:             root.text_primary
                            opacity:           0.9
                            style:             Text.Raised
                            styleColor:        Qt.rgba(0, 0, 0, 0.6)
                        }
                    }
                    NumberAnimation on x {
                        from: 0; to: -(ticker_row_classic.width / 3)
                        duration: 16000; loops: Animation.Infinite
                        running: true; easing.type: Easing.Linear
                    }
                }
            }
        }
    }

    // ════════════════════════════════════════════════════════════════════
    // SPLIT LAYOUT
    // Left 55%:  glass card ▸ logo → NowServingLabel → CategoryBadge → Number → Underline
    // Right 45%: "NEXT UP" queue (clearly subordinate)
    // ════════════════════════════════════════════════════════════════════
    Item {
        id: split_layout
        anchors.fill: parent
        opacity: root._splitOpacity
        visible: opacity > 0

        Row {
            anchors.fill: parent

            // ── Left panel — primary content ──────────────────────────────
            Item {
                width:  parent.width * 0.55
                height: parent.height

                Rectangle {
                    anchors.fill: parent
                    color: Qt.rgba(0, 0, 0, 0.10)
                }

                // Glass card behind the stack — same contrast guarantee as Classic
                Item {
                    id: split_center_wrap
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: root.numOpticalLift
                    width:  split_content_col.implicitWidth  + 72
                    height: split_content_col.implicitHeight + 48

                    GlassCard { anchors.fill: parent }

                    ColumnLayout {
                        id: split_content_col
                        anchors.centerIn: parent
                        spacing: 0

                        // Logo — accent badge
                        Rectangle {
                            Layout.alignment:   Qt.AlignHCenter
                            Layout.bottomMargin: Math.max(root.height * 0.020, 12)
                            width:  DisplayState.logoSize
                            height: DisplayState.logoSize
                            radius: root.radius_chip
                            color:  root.accent_gold_dim
                            visible: DisplayState.logoVisible
                            Behavior on color { ColorAnimation { duration: root.dur_full } }
                            Image {
                                anchors { fill: parent; margins: Math.max(3, DisplayState.logoSize * 0.07) }
                                source:   DisplayState.logoSource
                                fillMode: Image.PreserveAspectFit
                                asynchronous: true
                                sourceSize: Qt.size(DisplayState.logoSize * 2, DisplayState.logoSize * 2)
                            }
                        }

                        // Whisper
                        NowServingLabel {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: Math.max(root.height * 0.012, 8)
                        }

                        // Category — badge
                        CategoryBadge {
                            numPx: DisplayState.fontSize * root.numScale * root.numLayoutSplit
                            catScale: root.catScaleSplit
                            Layout.bottomMargin: Math.max(root.height * 0.016, 10)
                        }

                        // Number
                        ServingNumber {
                            layoutMult: root.numLayoutSplit
                            Layout.alignment: Qt.AlignHCenter
                            Layout.bottomMargin: Math.max(root.height * 0.014, 8)
                        }

                        // Underline
                        AccentUnderline {
                            layoutMult: root.numLayoutSplit
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }
                }
            }

            // ── Right panel — next-up queue (subordinate) ─────────────────
            Item {
                width:  parent.width * 0.45
                height: parent.height

                ColumnLayout {
                    anchors { fill: parent; margins: 28; topMargin: 44 }
                    spacing: 0

                    // "NEXT UP" — clearly secondary, small and dim
                    Text {
                        text:           "NEXT UP"
                        font.family:    DisplayState.uiFont
                        font.pixelSize: Math.max(root.height * 0.018, 9)
                        font.letterSpacing: 5
                        font.weight:    Font.Light
                        color:          root.text_secondary
                        opacity:        0.35
                        Layout.bottomMargin: 16
                        style:          Text.Raised
                        styleColor:     Qt.rgba(0, 0, 0, 0.5)
                    }

                    Repeater {
                        model: {
                            var nu = DisplayState.nextUp
                            if (nu && nu.length > 0) return nu.slice(0, 4)
                            var base = parseInt(DisplayState.currentNumber) || 0
                            var arr = []
                            for (var i = 1; i <= 4; i++)
                                arr.push(String(base + i).padStart(3, '0'))
                            return arr
                        }

                        delegate: Item {
                            Layout.fillWidth: true
                            height: 50

                            Text {
                                anchors {
                                    left: parent.left; leftMargin: 12
                                    verticalCenter: parent.verticalCenter
                                }
                                text:           modelData
                                font.family:    DisplayState.numberFont
                                // Queue numbers are noticeably smaller than the main number
                                font.pixelSize: Math.max(root.height * 0.036, 15)
                                font.weight:    Font.Normal
                                color:          root.text_primary
                                // Each successive entry fades more aggressively
                                opacity:        0.38 - index * 0.07
                                style:          Text.Raised
                                styleColor:     Qt.rgba(0, 0, 0, 0.55)
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }

                    // Banner strip at bottom of right panel — converted to
                    // a scrolling ticker (matching Classic) inside its own
                    // contrast pill, since static wrapped text at low
                    // opacity was easy to miss. Always animating.
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(root.height * 0.07, 32)
                        visible: DisplayState.bannerEnabled
                        radius: root.radius_chip
                        color: Qt.rgba(0, 0, 0, 0.42)
                        clip: true

                        Row {
                            id: ticker_row_split
                            height: parent.height
                            spacing: 64
                            Repeater {
                                model: 3
                                Text {
                                    height:            ticker_row_split.height
                                    verticalAlignment: Text.AlignVCenter
                                    text:              "  ·  " + DisplayState.bannerText
                                    font.family:       DisplayState.uiFont
                                    font.pixelSize:    Math.max(root.height * 0.021, 11)
                                    font.weight:       Font.DemiBold
                                    color:             root.text_primary
                                    opacity:           0.9
                                    style:             Text.Raised
                                    styleColor:        Qt.rgba(0, 0, 0, 0.6)
                                }
                            }
                            NumberAnimation on x {
                                from: 0; to: -(ticker_row_split.width / 3)
                                duration: 14000; loops: Animation.Infinite
                                running: true; easing.type: Easing.Linear
                            }
                        }
                    }
                }
            }
        }
    }

    // ════════════════════════════════════════════════════════════════════
    // CENTERED LAYOUT
    // Pure minimal, on a glass card. Logo top, NowServingLabel,
    // CategoryBadge, Number, Underline, facility name. No header bar,
    // no footer ticker. Designed for large rooms where the number must
    // fill the frame — the category badge scales up right alongside it.
    // ════════════════════════════════════════════════════════════════════
    Item {
        id: centered_layout
        anchors.fill: parent
        opacity: root._centeredOpacity
        visible: opacity > 0

        Item {
            id: centered_center_wrap
            anchors.centerIn: parent
            anchors.verticalCenterOffset: root.numOpticalLift
            width:  centered_content_col.implicitWidth  + 96
            height: centered_content_col.implicitHeight + 64

            GlassCard { anchors.fill: parent }

            ColumnLayout {
                id: centered_content_col
                anchors.centerIn: parent
                spacing: 0

                // Logo — larger badge than other layouts
                Rectangle {
                    Layout.alignment:    Qt.AlignHCenter
                    Layout.bottomMargin: Math.max(root.height * 0.034, 16)
                    width:  DisplayState.logoSize * 1.25
                    height: DisplayState.logoSize * 1.25
                    radius: root.radius_card
                    color:  root.accent_gold_dim
                    visible: DisplayState.logoVisible
                    Behavior on color { ColorAnimation { duration: root.dur_full } }
                    Image {
                        anchors { fill: parent; margins: Math.max(4, DisplayState.logoSize * 0.09) }
                        source:   DisplayState.logoSource
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        sourceSize: Qt.size(DisplayState.logoSize * 2.5, DisplayState.logoSize * 2.5)
                    }
                }

                // Whisper
                NowServingLabel {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: Math.max(root.height * 0.012, 8)
                }

                // Category — badge, largest of the three layouts
                CategoryBadge {
                    numPx: DisplayState.fontSize * root.numScale * root.numLayoutCentered
                    catScale: root.catScaleCentered
                    Layout.bottomMargin: Math.max(root.height * 0.018, 12)
                }

                // Number — biggest of all three layouts
                ServingNumber {
                    layoutMult: root.numLayoutCentered
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: Math.max(root.height * 0.016, 10)
                }

                // Underline
                AccentUnderline {
                    layoutMult: root.numLayoutCentered
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: Math.max(root.height * 0.030, 16)
                }

                // Facility name — tertiary, bottom of stack
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text:           DisplayState.facilityName
                    font.family:    DisplayState.facilityFont || DisplayState.numberFont
                    font.pixelSize: Math.max(DisplayState.facilityFontSize || Math.max(root.height * 0.022, 10), 10)
                    font.weight:    Font.Light
                    color:          root.text_primary
                    opacity:        0.35
                    style:          Text.Raised
                    styleColor:     Qt.rgba(0, 0, 0, 0.5)
                }
            }
        }

        // ── Bottom banner ticker ────────────────────────────────────────
        // Centered previously had no banner at all. Added here, docked to
        // the bottom edge, matching the Classic/Split ticker so the banner
        // is always present, always moving, and always legible.
        Rectangle {
            anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
            height: Math.max(root.height * 0.08, 36)
            color: Qt.rgba(0, 0, 0, 0.42)
            clip: true
            visible: DisplayState.bannerEnabled

            Row {
                id: ticker_row_centered
                height: parent.height
                spacing: 96
                Repeater {
                    model: 3
                    Text {
                        height:            ticker_row_centered.height
                        verticalAlignment: Text.AlignVCenter
                        text:              "  ·  " + DisplayState.bannerText
                        font.family:       DisplayState.uiFont
                        font.pixelSize:    Math.max(root.height * 0.023, 11)
                        font.weight:       Font.DemiBold
                        color:             root.text_primary
                        opacity:           0.9
                        style:             Text.Raised
                        styleColor:        Qt.rgba(0, 0, 0, 0.6)
                    }
                }
                NumberAnimation on x {
                    from: 0; to: -(ticker_row_centered.width / 3)
                    duration: 16000; loops: Animation.Infinite
                    running: true; easing.type: Easing.Linear
                }
            }
        }
    }
}
