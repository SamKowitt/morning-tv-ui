import QtQuick
import "." as Gallery

Item {
    id: root
    width: 262
    height: 223
    clip: true

    property var cards: []
    property real seconds: 0

    readonly property var info: cards.length ? cards[0] : ({})
    readonly property string weatherMode: info.mode || "clear"
    readonly property string weatherPhase: info.phase || "day"

    Timer {
        interval: 67
        running: root.visible && root.cards.length > 0
        repeat: true
        onTriggered: root.seconds += 0.067
    }

    // Full-card background using the gallery's actual colors.
    Rectangle {
        anchors.fill: parent

        gradient: Gradient {
            GradientStop {
                position: 0
                color: art.topColor()
            }
            GradientStop {
                position: 1
                color: art.bottomColor()
            }
        }
    }

    // One approved V41 scene with original proportions.
    Gallery.V41Card {
        id: art
        dateCardFullBleed: true
        width: 480
        height: 78

        condition: root.weatherMode
        phase: root.weatherPhase
        seconds: root.seconds
        moving: true

        readonly property real fit: Math.max(
            root.width / 480,
            root.height / 78
        )

        transformOrigin: Item.TopLeft
        scale: fit
        x: root.width - width * fit
        y: (root.height - height * fit) / 2
    }
}
