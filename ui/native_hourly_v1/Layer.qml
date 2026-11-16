import QtQuick
import QtQuick.Window
import QtQuick.Effects
import org.kde.layershell 1.0 as LayerShell
import "Weather" as Weather

Window {
    id: root
    title: "MorningUI Native Hourly Weather"
    visible: true // transparent surface stays alive so policy polling runs during popups
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.WindowTransparentForInput
    width: root.displayW
    height: root.displayH

    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.margins.left: root.displayX
    LayerShell.Window.margins.top: root.displayY
    LayerShell.Window.margins.right: 0
    LayerShell.Window.margins.bottom: 0
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    property string stateUrl: "file:///home/mrkowitt/.cache/morningui_native_hourly_v1/state.json"
    property int screenX: 18
    property int screenY: 254
    property int windowW: 262
    property int windowH: 808
    property int displayX: 0
    property int displayY: 0
    property int displayW: 1920
    property int displayH: 1080
    // MUI_NATIVE_CURRENT_HOUR_V1 — actual current-hour scene, not a PNG popup.
    property var currentHour: ({"show": false})
    property int currentHourRevision: -1
    property bool currentSelected: false
    property var radar: ({"show": false})
    property int radarRevision: -1
    property var newspaper: ({"show": false})
    property int newspaperRevision: -1
    property var cards: []
    property int version: -1
    property int selected: -1
    property bool showWeather: false
    // MUI_NATIVE_OLED_FOCUS_V5: same stages and dim levels as Qt OLEDProtection.
    property var oledFocus: ({"level": 0, "dim": 0.0})
    property int oledLevel: Number(oledFocus.level || 0)
    property real oledDim: oledLevel === 2 ? Number(oledFocus.dim || 0) : 0.0
    property bool loading: false
    property bool reported: false
    property double lastFreshMs: 0

    function updateState() {
        if (loading) return
        loading = true
        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            loading = false
            try {
                if (xhr.status !== 0 && xhr.status !== 200) return
                var data = JSON.parse(xhr.responseText)
                if (!data || !data.cards || data.cards.length !== 9) return
                // MUI_OLED_WEATHER_HOLD_V62: allow Qt time to restyle
                // without blanking independent QML animations.
                if (Date.now() - Number(data.epoch_ms) > 45000) {
                    showWeather = false
                    return
                }
                lastFreshMs = Date.now()
                if (version !== Number(data.version)) {
                    cards = data.cards
                    version = Number(data.version)
                }
                if (data.display_x !== undefined) displayX = data.display_x
                if (data.display_y !== undefined) displayY = data.display_y
                if (data.display_w !== undefined) displayW = data.display_w
                if (data.display_h !== undefined) displayH = data.display_h
                if (data.oled_focus !== undefined) {
                    // Do not churn all ten animated QML items every poll.
                    var nextOled = data.oled_focus
                    if (Number(oledFocus.level || 0) !== Number(nextOled.level || 0)
                            || Number(oledFocus.dim || 0) !== Number(nextOled.dim || 0)
                            || Number(oledFocus.shift_x || 0) !== Number(nextOled.shift_x || 0)
                            || Number(oledFocus.shift_y || 0) !== Number(nextOled.shift_y || 0))
                        oledFocus = nextOled
                }
                if (currentHourRevision !== Number(data.current_hour_revision || 0)) {
                    currentHour = data.current_hour || ({"show": false})
                    currentHourRevision = Number(data.current_hour_revision || 0)
                }
                currentSelected = data.current_selected === true
                if (radarRevision !== Number(data.radar_revision || 0)) {
                    radar = data.radar || ({"show": false})
                    radarRevision = Number(data.radar_revision || 0)
                }
                if (newspaperRevision !== Number(data.newspaper_revision || 0)) {
                    newspaper = data.newspaper || ({"show": false})
                    newspaperRevision = Number(data.newspaper_revision || 0)
                }
                if (screenX !== data.x) screenX = data.x
                if (screenY !== data.y) screenY = data.y
                if (windowW !== data.w) windowW = data.w
                if (windowH !== data.h) windowH = data.h
                if (selected !== data.selected) selected = data.selected
                showWeather = data.show === true
                if (!reported && showWeather) {
                    reported = true
                    console.log("NATIVE_HOURLY_CARDS_READY")
                }
            } catch(e) {
                console.log("NATIVE_HOURLY_STATE_ERROR", e)
            }
        }
        xhr.open("GET", stateUrl + "?r=" + Date.now(), true)
        xhr.send()
    }

    Timer {
        interval: root.showWeather ? 80 : 16
        repeat: true
        running: true
        triggeredOnStart: true
        onTriggered: {
            root.updateState()
            // A temporary main-thread stall is not a weather hide command.
            if (root.lastFreshMs && Date.now() - root.lastFreshMs > 45000)
                root.showWeather = false
        }
    }

    Repeater {
        model: 9
        delegate: Item {
            id: tile
            property var info: root.cards.length === 9 ? root.cards[index] : ({})
            visible: info.w > 0
            opacity: root.showWeather && root.oledLevel < 3 ? 1.0 : 0.0
            x: (info.x || 0) + root.screenX - root.displayX
            y: (info.y || 0) + root.screenY - root.displayY
            width: info.w || 262
            height: info.h || 78

            Item {
                id: originalContent
                anchors.fill: parent
                visible: false
                layer.enabled: true

                Weather.V5WCard {
                    anchors.fill: parent
                    condition: tile.info.v5w_mode || "clear_sky"
                    phase: tile.info.phase || "day"
                    windMultiplier: tile.info.wind || 1.0
                }
                // OLED contrast: darken animated artwork behind tan text;
                // original OLED text and section layout remain authoritative.
                Rectangle {
                    anchors.fill: parent
                    color: "#1b2733"
                    opacity: root.oledLevel >= 1 ? 0.25 : 0.0
                    visible: opacity > 0
                }
                Image {
                    anchors.fill: parent
                    source: tile.info.url || ""
                    fillMode: Image.Stretch
                    smooth: true
                    cache: false
                }
            }

            Item {
                id: roundedAlphaMask
                anchors.fill: parent
                visible: false
                layer.enabled: true
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 2
                    radius: 15
                    color: "white"
                }
            }

            MultiEffect {
                anchors.fill: parent
                source: originalContent
                maskEnabled: true
                maskSource: roundedAlphaMask
                autoPaddingEnabled: false
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 1
                color: "transparent"
                radius: 16
                border.width: 3.2
                border.color: "#FFEC89"
                visible: root.selected === index
            }
            // Qt's Shade is below this separate layer-shell window.
            // Dim native pixels individually, not the full QML window,
            // or the rest of the Qt dashboard would be dimmed twice.
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: 15
                color: "black"
                opacity: root.oledDim
                visible: opacity > 0
            }
        }
    }
    // MUI_CURRENT_HOUR_V4: render exactly like the proven nine hourly
    // GPU cards, using the SAME V5WCard and its larger dateCardPresentation.
    // The original DateCard Qt foreground supplies the live clock and text.
    Item {
        id: nativeCurrent
        z: 10
        property var info: root.currentHour
        property bool reported: false
        // MUI_NATIVE_CURRENT_MOTION_GATE_V7
        // Keep original V27 visible until native cloud motion starts.
        property real firstCloudPosition: -1
        visible: info.show === true && root.showWeather && root.oledLevel < 3
        opacity: reported ? 1.0 : 0.0
        x: Number(info.x || 0) - root.displayX
        y: Number(info.y || 0) - root.displayY
        width: Number(info.w || 0)
        height: Number(info.h || 0)
        onVisibleChanged: {
            if (!visible && info.show !== true) {
                reported = false
                firstCloudPosition = -1
            }
        }
        Timer {
            interval: 400
            repeat: true
            running: nativeCurrent.visible && !nativeCurrent.reported
            onTriggered: {
                if (foreground.status !== Image.Ready || nativeCurrent.width <= 100
                        || nativeCurrent.height <= 80 || nativeSky.width <= 100)
                    return

                // V5WCard's visual child exposes the cloud animation position.
                var entry = nativeSky.children.length ? nativeSky.children[0] : null
                if (!entry || typeof entry.hasCloud !== "boolean") return

                if (entry.hasCloud) {
                    var pos = Number(entry.cloudPosition)
                    if (!isFinite(pos) || pos < 0) return

                    if (nativeCurrent.firstCloudPosition < 0) {
                        nativeCurrent.firstCloudPosition = pos
                        return
                    }

                    var sparse = (entry.modelData.key === "mostly_clear"
                                  || entry.modelData.key === "partly_cloudy")
                    var range = sparse ? 40000 : 200000
                    var movedPx = Math.abs(pos - nativeCurrent.firstCloudPosition)
                                  * nativeSky.width / range

                    // Require at least four pixels of animation travel.
                    if (movedPx < 4.0) return

                    console.log("NATIVE_CURRENT_HOUR_ANIMATING V7 pixels="
                                + movedPx.toFixed(2))
                } else {
                    // No clouds to track: allow the native sky to take over.
                    console.log("NATIVE_CURRENT_HOUR_ANIMATING V7 no_cloud_mode")
                }

                nativeCurrent.reported = true
                console.log("NATIVE_CURRENT_HOUR_READY V5W_DIRECT")
            }
        }
        Item {
            id: currentContent
            anchors.fill: parent
            visible: false
            layer.enabled: true
            // Identical offscreen-layer technique used by the nine hourly
            // cards. Native V5W animations keep advancing behind popups.
            Weather.V5WCurrentHQ {
                id: nativeSky
                anchors.fill: parent
                condition: nativeCurrent.info.condition || "clear_sky"
                phase: nativeCurrent.info.phase || "day"
                windMultiplier: Number(nativeCurrent.info.wind || 1.0)
                dateCardPresentation: true
            }
            Rectangle {
                anchors.fill: parent
                color: "#1b2733"
                opacity: root.oledLevel >= 1 ? 0.25 : 0.0
                visible: opacity > 0
            }
            Image {
                id: foreground
                anchors.fill: parent
                source: nativeCurrent.info.url || ""
                fillMode: Image.Stretch
                asynchronous: false
                cache: false
                smooth: true
            }
        }
        Item {
            id: currentMask
            anchors.fill: parent
            visible: false
            layer.enabled: true
            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: 14
                color: "white"
            }
        }
        MultiEffect {
            anchors.fill: parent
            source: currentContent
            maskEnabled: true
            maskSource: currentMask
            autoPaddingEnabled: false
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            radius: 20
            border.width: 2.3
            border.color: "#FFE12E"
            visible: root.currentSelected
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: 14
            color: "black"
            opacity: root.oledDim
            visible: opacity > 0
        }
    }

    // Native QML newspaper above all weather elements.
    NewsPopup {
        id: nativeNewsPopup
        z: 1000
        popupData: root.newspaper
        globalX: root.displayX
        globalY: root.displayY
    }

    // The radar popup is a native QML item in the SAME window,
    // above weather and newspaper. No weather hide/reveal is required.
    // Match the Shade Qt applies to its underlying newspaper dialog.
    Rectangle {
        z: 1001
        x: nativeNewsPopup.x; y: nativeNewsPopup.y
        width: nativeNewsPopup.width; height: nativeNewsPopup.height
        color: "black"; opacity: root.oledDim
        visible: nativeNewsPopup.visible && opacity > 0
    }

    RadarPopup {
        id: nativeRadarPopup
        z: 2000
        popupData: root.radar
        globalX: root.displayX
        globalY: root.displayY
    }
    Rectangle {
        z: 2001
        x: nativeRadarPopup.x; y: nativeRadarPopup.y
        width: nativeRadarPopup.width; height: nativeRadarPopup.height
        color: "black"; opacity: root.oledDim
        visible: nativeRadarPopup.visible && opacity > 0
    }

    // OLED Focus stage 3: truly opaque full-display blackout, including
    // the otherwise topmost native weather/newspaper/radar window.
    Rectangle {
        anchors.fill: parent
        z: 9000
        color: "black"
        visible: root.oledLevel === 3
    }
}
