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
    width: root.windowW
    height: root.windowH

    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.margins.left: root.screenX
    LayerShell.Window.margins.top: root.screenY
    LayerShell.Window.margins.right: 0
    LayerShell.Window.margins.bottom: 0
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    property string stateUrl: "file:///home/mrkowitt/.cache/morningui_native_hourly_v1/state.json"
    property int screenX: 18
    property int screenY: 254
    property int windowW: 262
    property int windowH: 808
    property var cards: []
    property int version: -1
    property int selected: -1
    property bool showWeather: false
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
                if (Date.now() - Number(data.epoch_ms) > 3000) {
                    showWeather = false
                    return
                }
                lastFreshMs = Date.now()
                if (version !== Number(data.version)) {
                    cards = data.cards
                    version = Number(data.version)
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
            if (root.lastFreshMs && Date.now() - root.lastFreshMs > 2300)
                root.showWeather = false
        }
    }

    Repeater {
        model: 9
        delegate: Item {
            id: tile
            property var info: root.cards.length === 9 ? root.cards[index] : ({})
            visible: info.w > 0
            opacity: root.showWeather ? 1.0 : 0.0
            x: info.x || 0
            y: info.y || 0
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
        }
    }
}
