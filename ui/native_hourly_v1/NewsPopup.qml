import QtQuick

Item {
    id: news
    property var popupData: ({"show": false})
    property int globalX: 0
    property int globalY: 0
    z: 1000
    visible: news.popupData.show === true
    x: Number(news.popupData.x || 0) - news.globalX
    y: Number(news.popupData.y || 0) - news.globalY
    width: Number(news.popupData.w || 0)
    height: Number(news.popupData.h || 0)
    clip: true

    Rectangle { anchors.fill: parent; color: "#2d2419" }

    Text {
        x: 18; y: 18
        width: parent.width * 0.70; height: 35
        text: news.popupData.source || "News"
        color: "#f3e6c9"
        font.family: "Georgia"; font.pixelSize: 27; font.bold: true
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    Text {
        x: parent.width * 0.64; y: 24
        width: parent.width * 0.34; height: 27
        text: news.popupData.counter || ""
        color: "#e8d8b6"
        font.family: "Georgia"; font.pixelSize: 14; font.bold: true
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
    }

    Rectangle {
        id: paper
        x: 18; y: 62
        width: parent.width - 36
        height: parent.height - 135
        border.width: 1
        border.color: "#4b331c"
        gradient: Gradient {
            GradientStop { position: 0.00; color: news.popupData.dark ? "#354959" : "#fff1d3" }
            GradientStop { position: 0.48; color: news.popupData.dark ? "#405667" : "#f6e4bd" }
            GradientStop { position: 0.52; color: news.popupData.dark ? "#364b5b" : "#ead4a8" }
            GradientStop { position: 1.00; color: news.popupData.dark ? "#364b5b" : "#fff0d0" }
        }

        property real pageWidth: (width - 54) / 2
        TextEdit {
            x: 20; y: 14
            width: paper.pageWidth; height: paper.height - 26
            clip: true
            readOnly: true
            selectByMouse: false
            textFormat: TextEdit.RichText
            wrapMode: TextEdit.Wrap
            text: news.popupData.left_html || ""
            font.family: "Courier New"
            font.pixelSize: 21
            color: news.popupData.dark ? "#f6e6c9" : "#1b130c"
        }
        Rectangle {
            x: parent.width / 2 - 6
            y: 1; width: 13; height: parent.height - 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#004b301c" }
                GradientStop { position: 0.45; color: "#664b301c" }
                GradientStop { position: 0.6; color: "#66fff9e1" }
                GradientStop { position: 1.0; color: "#00fff9e1" }
            }
        }
        TextEdit {
            x: parent.width / 2 + 12; y: 14
            width: paper.pageWidth; height: paper.height - 26
            clip: true
            readOnly: true
            selectByMouse: false
            textFormat: TextEdit.RichText
            wrapMode: TextEdit.Wrap
            text: news.popupData.right_html || ""
            font.family: "Courier New"
            font.pixelSize: 21
            color: news.popupData.dark ? "#f6e6c9" : "#1b130c"
        }
    }
    Repeater {
        model: news.popupData.buttons || []
        delegate: Rectangle {
            z: 2
            x: modelData.x; y: modelData.y
            width: modelData.w; height: modelData.h
            radius: 6
            color: modelData.enabled ? "#f3e6c9" : "#b0a58f"
            border.width: news.popupData.focus === modelData.id ? 3 : 2
            border.color: news.popupData.focus === modelData.id ? "#ffd600" : "#46321c"
            Text {
                anchors.fill: parent
                text: modelData.text
                color: modelData.enabled ? "#24170d" : "#706153"
                font.family: "Georgia"; font.pixelSize: 16; font.bold: true
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
