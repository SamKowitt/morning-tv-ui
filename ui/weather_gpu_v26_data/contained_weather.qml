import QtQuick
import "v41_release" as Gallery

Item {
    id: root
    width: 260
    height: 760
    property var cards: []
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

            // Uniform scale. Crop the left side rather than
            // stretching V41 artwork horizontally.
            Gallery.V41Card {
                id: art
                property real fit: Math.max(
                    tile.width / 480,
                    tile.height / 78
                )

                x: tile.width - width * fit
                y: (tile.height - height * fit) / 2

                width: 480
                height: 78
                transformOrigin: Item.TopLeft
                scale: fit

                condition: tile.info.mode
                phase: tile.info.phase
                seconds: root.v41Seconds
                moving: true
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
