import QtQuick
import "v41_release" as Gallery
import "v5w_release" as V5W

Item {
    id: root
    width: 260
    height: 760
    property var cards: []
    property bool oledWeatherPalette: false // OLED_FOCUS_V6_STAGED_DIM
    property int selectedIndex: -1 // MORNINGUI_GPU_FOCUS_V27
    property real v41Seconds: 0
    clip: true

    Timer {
        interval: 67
        repeat: true
        running: root.cards.length > 0 && root.visible
        onTriggered: root.v41Seconds += 0.067
    }

    Repeater {
        model: root.cards

        delegate: Item {
            id: tile
            property var info: modelData

            x: info.x
            y: info.y
            width: info.w
            height: info.h
            clip: true

            // MORNINGUI_V5W_HOURLY_OPTIONAL
            Loader {
                anchors.fill: parent
                sourceComponent: tile.info.useV5W === true
                    ? v5wArtwork : v41Artwork
            }

            Component {
                id: v41Artwork
                Gallery.V41Card {
                    property real fit: Math.max(
                        tile.width / 480, tile.height / 78
                    )
                    x: tile.width - width * fit
                    y: (tile.height - height * fit) / 2
                    width: 480
                    height: 78
                    transformOrigin: Item.TopLeft
                    scale: fit
                    condition: tile.info.mode
                    phase: tile.info.phase
                    windMultiplier: tile.info.windMultiplier === undefined ? 1.0 : tile.info.windMultiplier
                    seconds: root.v41Seconds
                    moving: true
                }
            }

            Component {
                id: v5wArtwork
                V5W.V5WCard {
                    property real fit: Math.max(
                        tile.width / 262, tile.height / 78
                    )
                    x: tile.width - width * fit
                    y: (tile.height - height * fit) / 2
                    width: 262
                    height: 78
                    transformOrigin: Item.TopLeft
                    scale: fit
                    condition: tile.info.v5w_mode
                    phase: tile.info.phase
                    windMultiplier: tile.info.windMultiplier === undefined ? 1.0 : tile.info.windMultiplier
                }
            }

            Gallery.OLEDWeatherPalette {
                objectName: "OLEDWeatherPaletteHourly"
                anchors.fill: parent
                z: 9
                active: root.oledWeatherPalette
                condition: tile.info.v5w_mode || tile.info.mode || "cloudy"
                phase: tile.info.phase || "day"
            }

            // Existing real weather text, drawn transparently.
            Image {
                z: 10
                anchors.fill: parent
                source: tile.info.url
                fillMode: Image.Stretch
                cache: false
                asynchronous: false
                smooth: true
            }

            // Existing V29 external focus logic remains active.
            Rectangle {
                z: 999
                anchors.fill: parent
                anchors.margins: 5
                radius: 12
                color: "transparent"
                border.width: 3.2
                border.color: "#FFEC89"
                visible: false // V29_OUTER_HOURLY_FOCUS
            }
        }
    }
}
