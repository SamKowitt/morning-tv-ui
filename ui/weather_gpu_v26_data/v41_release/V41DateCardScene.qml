import QtQuick
import "." as Gallery
import "../v5w_release" as V5W

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
        visible: root.info.useV5W !== true
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
        visible: root.info.useV5W !== true
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
    // MORNINGUI_V5W_DATE_OPTIONAL
    Loader {
        anchors.fill: parent
        active: root.info.useV5W === true

        sourceComponent: Component {
            V5W.V5WCard {
                objectName: "V5YDateArtwork"
                x: 0
                y: 0
                width: root.width
                height: root.height
                dateCardPresentation: true

                condition: root.info.v5w_mode
                phase: root.weatherPhase
            }
        }
    }

    // MORNINGUI_V5X_FIXED_STARS_DATE_MOON
    Image {
        objectName: "V5XDateMoon"

        visible: root.info.useV5W === true &&
                 root.weatherPhase === "night" &&
                 (root.info.v5w_mode === "clear_sky" ||
                  root.info.v5w_mode === "mostly_clear" ||
                  root.info.v5w_mode === "partly_cloudy")

        source: Qt.resolvedUrl(
            "../v5w_release/assets/moon_date_v5x.png"
        )

width: 32
height: 32
        x: root.width - width - 25
        y: 12
        z: 30

        smooth: true
        fillMode: Image.PreserveAspectFit
    }

}
