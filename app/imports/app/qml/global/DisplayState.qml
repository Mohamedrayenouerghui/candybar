pragma Singleton

import QtQuick 2.15

// ── CandyBarV2 DisplayState ──────────────────────────────────────────────
// Single source of truth for all display properties.
// All changes persist to disk immediately via DisplayPersistence.
// applyMqttCommand() is the sole write path.

QtObject {
    id: root

    // ── queue ──────────────────────────────────────────────────────────
    property string currentNumber: "001"
    property var    nextUp: []

    // ── audio / TTS ────────────────────────────────────────────────────
    property bool   audioMuted: false
    property int    audioVolumeStep: 3
    property string ttsLanguage: "en"
    property bool   ttsEnabled: true

    // ── category ────────────────────────────────────────────────────────
    property string category: "A"
    property string categoryDisplayName: "Category A"

    // ── branding ────────────────────────────────────────────────────────
    property string logoSource:   "qrc:/app/res/image/genical.jpg"
    property string facilityName: "CandyBar Service Centre"
    property string bannerText:   "Welcome — please wait for your number to be called"
    property string backgroundImage: "qrc:/app/res/image/ff_burger_pattern.jpg"
    // "landscape" → PreserveAspectCrop normally
    // "portrait"  → rotate 90° then crop to fill (phone wallpapers on a wide screen)
    property string backgroundOrientation: "portrait"
    property string logoPosition: "top-left"   // top-left | top-center | hidden
    property bool   bannerEnabled: true
    property bool   logoVisible: true

    // ── design tokens ──────────────────────────────────────────────────
    property color  bgColor:      "#0b0d10"
    property color  accentColor:  "#FFB84D"
    property bool   accentGradientEnabled: false
    property string accentGradientDirection: "top-to-bottom"  // top-to-bottom | corner-to-edge

    // ── layout ─────────────────────────────────────────────────────────
    property string layoutType: "Classic"   // "Classic" | "Split" | "Centered"

    // ── typography ─────────────────────────────────────────────────────
    // fontSize: continuous 48–200px, set directly via slider — no preset enum
    property string numberFont: "DM Mono"
    property string categoryFont: "DM Mono"
    property string facilityFont: "DM Mono"
    property string bannerFont: "DM Mono"
    property string nowServingFont: "DM Mono"
    property string uiFont:     Qt.application.font.family
    property int    fontSize:   96
    property int    numberFontSize: 96
    property int    categoryFontSize: 34
    property int    facilityFontSize: 24
    property int    bannerFontSize: 24
    property int    nowServingFontSize: 16

    // ── logo ────────────────────────────────────────────────────────────
    // logoSize: logo container height in px, 24–120, aspect ratio preserved
    property int    logoSize:   48

    // ── URLs (set at startup from NetworkHelper) ────────────────────────
    property string publicUrl: "http://localhost:8080/"
    property string adminUrl:  "http://localhost:8080/admin"
    property string siteUrl:   "https://candybarv2.app"

    // ── MQTT / connection state ─────────────────────────────────────────
    property bool   mqttConnected: false
    property string mqttStatus:    "Connecting…"

    property bool   _loaded: false

    function accentAlpha(a) {
        return Qt.rgba(accentColor.r, accentColor.g, accentColor.b, a)
    }

    function _bgSource(path) {
        if (!path || path.length === 0) return "qrc:/app/res/image/ff_burger_pattern.jpg"
        // Migrate old dark defaults to the new burger default
        if (path === "qrc:/app/res/image/0.jpg" ||
            path === "qrc:/app/res/image/pro_abstract.jpg") {
            return "qrc:/app/res/image/ff_burger_pattern.jpg"
        }
        if (path.startsWith("qrc:") || path.startsWith("file://")) return path
        if (path.startsWith("/")) return "file://" + path
        return path
    }

    function _syncAudioEngine() {
        if (typeof AudioEngine === 'undefined') return
        AudioEngine.muted      = audioMuted
        AudioEngine.volumeStep = audioVolumeStep
        AudioEngine.language   = ttsLanguage
        AudioEngine.ttsEnabled = ttsEnabled
        AudioEngine.set_category_display_name(categoryDisplayName)
    }

    function loadFromDisk() {
        if (_loaded) return
        _loaded = true
        var p = DisplayPersistence
        currentNumber         = p.load("currentNumber", "001")
        var nu                = p.get_next_up()
        nextUp                = Array.isArray(nu) ? nu : []
        layoutType            = p.load("layoutType", "Classic")
        accentColor           = p.load("accentColor", "#FFB84D")
        accentGradientEnabled    = p.load("accentGradientEnabled", "false") === "true"
        accentGradientDirection  = p.load("accentGradientDirection", "top-to-bottom")
        bannerText            = p.load("bannerText", "Welcome — please wait for your number to be called")
        facilityName          = p.load("facilityName", "CandyBar Service Centre")
        category              = p.load("category", "A")
        categoryDisplayName   = p.load("categoryDisplayName", "Category A")
        logoPosition          = p.load("logoPosition", "top-left")
        bannerEnabled         = p.load("bannerEnabled", "true") !== "false"
        logoVisible           = p.load("logoVisible", "true") !== "false"
        numberFont            = p.load("numberFont", "DM Mono")
        categoryFont          = p.load("categoryFont", numberFont)
        facilityFont          = p.load("facilityFont", numberFont)
        bannerFont            = p.load("bannerFont", numberFont)
        nowServingFont        = p.load("nowServingFont", numberFont)
        ttsLanguage           = p.load("ttsLanguage", "en")
        ttsEnabled            = p.load("ttsEnabled", "true") !== "false"
        audioMuted            = p.load("audioMuted", "false") === "true"
        audioVolumeStep       = parseInt(p.load("audioVolumeStep", "3")) || 3
        var fs                = parseInt(p.load("fontSize", "96"))
        fontSize              = (fs >= 48 && fs <= 200) ? fs : 96
        numberFontSize        = parseInt(p.load("numberFontSize", fontSize)) || fontSize
        categoryFontSize      = parseInt(p.load("categoryFontSize", 34)) || 34
        facilityFontSize      = parseInt(p.load("facilityFontSize", 24)) || 24
        bannerFontSize        = parseInt(p.load("bannerFontSize", 24)) || 24
        nowServingFontSize    = parseInt(p.load("nowServingFontSize", 16)) || 16
        var ls                = parseInt(p.load("logoSize", "48"))
        logoSize              = (ls >= 24 && ls <= 120) ? ls : 48
        var lp                = p.logo_path()
        if (lp && lp.length > 0)
            logoSource = "file://" + lp
        backgroundImage       = _bgSource(p.load("backgroundImage", "qrc:/app/res/image/ff_burger_pattern.jpg"))
        backgroundOrientation = p.load("backgroundOrientation", "portrait")
        _syncAudioEngine()
    }

    function applyMqttCommand(key, value) {
        var p = DisplayPersistence
        if (key === "currentNumber") {
            var prev = currentNumber
            currentNumber = value
            p.save("currentNumber", value)
            if (ttsEnabled && !audioMuted && prev !== value
                    && typeof AudioEngine !== 'undefined') {
                AudioEngine.announceNumber(value)
            }
        } else if (key === "nextUp") {
            nextUp = value.length > 0 ? value.split(",").map(function(s){ return s.trim() }) : []
            p.save("nextUp", value)
        } else if (key === "layoutType") {
            layoutType = value
            p.save("layoutType", value)
        } else if (key === "accentColor") {
            accentColor = value
            p.save("accentColor", value)
        } else if (key === "accentGradientEnabled") {
            accentGradientEnabled = value === "true" || value === true
            p.save("accentGradientEnabled", accentGradientEnabled ? "true" : "false")
        } else if (key === "accentGradientDirection") {
            accentGradientDirection = value
            p.save("accentGradientDirection", value)
        } else if (key === "bannerText") {
            bannerText = value
            p.save("bannerText", value)
        } else if (key === "facilityName") {
            facilityName = value
            p.save("facilityName", value)
        } else if (key === "fontSize") {
            var fs = parseInt(value)
            if (fs >= 48 && fs <= 200) { fontSize = fs; numberFontSize = fs; p.save("fontSize", fs); p.save("numberFontSize", fs) }
        } else if (key === "numberFontSize") {
            var nfs = parseInt(value)
            if (nfs >= 8 && nfs <= 240) { numberFontSize = nfs; p.save("numberFontSize", nfs) }
        } else if (key === "categoryFontSize") {
            var cfs = parseInt(value)
            if (cfs >= 8 && cfs <= 240) { categoryFontSize = cfs; p.save("categoryFontSize", cfs) }
        } else if (key === "facilityFontSize") {
            var ffs = parseInt(value)
            if (ffs >= 8 && ffs <= 240) { facilityFontSize = ffs; p.save("facilityFontSize", ffs) }
        } else if (key === "bannerFontSize") {
            var bfs = parseInt(value)
            if (bfs >= 8 && bfs <= 240) { bannerFontSize = bfs; p.save("bannerFontSize", bfs) }
        } else if (key === "nowServingFontSize") {
            var sfs = parseInt(value)
            if (sfs >= 8 && sfs <= 240) { nowServingFontSize = sfs; p.save("nowServingFontSize", sfs) }
        } else if (key === "logoSize") {
            var ls = parseInt(value)
            if (ls >= 24 && ls <= 120) { logoSize = ls; p.save("logoSize", ls) }
        } else if (key === "numberFont") {
            numberFont = value
            p.save("numberFont", value)
        } else if (key === "categoryFont") {
            categoryFont = value
            p.save("categoryFont", value)
        } else if (key === "facilityFont") {
            facilityFont = value
            p.save("facilityFont", value)
        } else if (key === "bannerFont") {
            bannerFont = value
            p.save("bannerFont", value)
        } else if (key === "nowServingFont") {
            nowServingFont = value
            p.save("nowServingFont", value)
        } else if (key === "logoSource") {
            logoSource = value.startsWith("file://") ? value : "file://" + value
            p.save("logoPath", value.replace("file://", ""))
        } else if (key === "backgroundImage") {
            backgroundImage = _bgSource(value)
            p.save("backgroundImage", value.replace("file://", ""))
        } else if (key === "backgroundOrientation") {
            backgroundOrientation = value
            p.save("backgroundOrientation", value)
        } else if (key === "adminPin") {
            p.set_pin(value)
        } else if (key === "category") {
            category = value
            p.save("category", value)
        } else if (key === "categoryDisplayName") {
            categoryDisplayName = value
            p.save("categoryDisplayName", value)
            _syncAudioEngine()
        } else if (key === "logoPosition") {
            logoPosition = value
            p.save("logoPosition", value)
        } else if (key === "bannerEnabled") {
            bannerEnabled = value === "true" || value === true
            p.save("bannerEnabled", bannerEnabled ? "true" : "false")
        } else if (key === "logoVisible") {
            logoVisible = value === "true" || value === true
            p.save("logoVisible", logoVisible ? "true" : "false")
        } else if (key === "ttsLanguage") {
            ttsLanguage = value
            p.save("ttsLanguage", value)
            _syncAudioEngine()
        } else if (key === "ttsEnabled") {
            ttsEnabled = value === "true" || value === true
            p.save("ttsEnabled", ttsEnabled ? "true" : "false")
            _syncAudioEngine()
        } else if (key === "audioMuted") {
            audioMuted = value === "true" || value === true
            p.save("audioMuted", audioMuted ? "true" : "false")
            _syncAudioEngine()
        } else if (key === "audioVolumeStep") {
            audioVolumeStep = parseInt(value) || 3
            p.save("audioVolumeStep", audioVolumeStep)
            _syncAudioEngine()
        }
    }
}
