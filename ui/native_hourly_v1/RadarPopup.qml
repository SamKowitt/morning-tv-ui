import QtQuick

// MUI_RADAR_DIRECT_V4 — original QWidget positions/style, no dialog grab.
// Weather (all ten scenes) stays alive behind this independently animated
// raster-source radar. All controls are still invoked by the original dialog.
Item {
    id: radar
    property var popupData: ({"show": false})
    property int globalX: 0
    property int globalY: 0
    z: 2000
    visible: popupData.show === true
    x: Number(popupData.x || 0) - globalX
    y: Number(popupData.y || 0) - globalY
    width: Number(popupData.w || 0)
    height: Number(popupData.h || 0)
    clip: true
    property string frontUrl: ""
    property string pendingUrl: ""
    property bool frontB: false

    function updateFrame() {
        var next = String(popupData.image || "")
        if (popupData.show !== true) {
            frontUrl = ""; pendingUrl = ""; frontB = false
            imageA.source = ""; imageB.source = ""
            return
        }
        if (!next || next === frontUrl || next === pendingUrl) return
        pendingUrl = next
        if (frontB) imageA.source = next
        else imageB.source = next
    }
    function acceptFrame(isB, url) {
        if (!url || url !== pendingUrl || popupData.show !== true) return
        frontB = isB; frontUrl = url; pendingUrl = ""
    }
    onPopupDataChanged: updateFrame()

    Rectangle { anchors.fill: parent; color: "#2d2419" }

    // Original masthead is Rockwell 27 px / heavy, and status uses the
    // original Times New Roman 13 px; both positions come from Qt layouts.
    Text {
        x: Number((radar.popupData.masthead && radar.popupData.masthead.x) || 18)
        y: Number((radar.popupData.masthead && radar.popupData.masthead.y) || 16)
        width: Number((radar.popupData.masthead && radar.popupData.masthead.w) || 400)
        height: Number((radar.popupData.masthead && radar.popupData.masthead.h) || 36)
        text: "LOCAL RADAR MAP"
        color: radar.popupData.dark ? "#ead3a3" : "#24170d"
        font.family: "Rockwell"; font.pixelSize: 27
        font.weight: Font.Black
        font.letterSpacing: 1.2
        verticalAlignment: Text.AlignVCenter
    }
    Text {
        x: Number((radar.popupData.status_geom && radar.popupData.status_geom.x) || 18)
        y: Number((radar.popupData.status_geom && radar.popupData.status_geom.y) || 16)
        width: Number((radar.popupData.status_geom && radar.popupData.status_geom.w) || 400)
        height: Number((radar.popupData.status_geom && radar.popupData.status_geom.h) || 34)
        text: radar.popupData.status || ""
        color: "#e8d8b6"
        font.family: "Times New Roman"; font.pixelSize: 13
        font.weight: Font.Black
        font.letterSpacing: 1
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    Rectangle {
        id: paper
        x: Number((radar.popupData.paper && radar.popupData.paper.x) || 18)
        y: Number((radar.popupData.paper && radar.popupData.paper.y) || 63)
        width: Number((radar.popupData.paper && radar.popupData.paper.w) || radar.width - 36)
        height: Number((radar.popupData.paper && radar.popupData.paper.h) || radar.height - 133)
        border.color: "#4b331c"; border.width: 1
        gradient: Gradient {
            GradientStop { position: 0.0; color: radar.popupData.paper_top || "#fff1d3" }
            GradientStop { position: 0.48; color: radar.popupData.paper_middle || "#f6e4bd" }
            GradientStop { position: 0.52; color: radar.popupData.paper_fold || "#ead4a8" }
            GradientStop { position: 1.0; color: radar.popupData.paper_bottom || "#fff0d0" }
        }
        Rectangle {
            x: parent.width / 2 - 10; width: 14; y: 1; height: parent.height - 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#004a2d16" }
                GradientStop { position: 0.55; color: "#5f4a2d16" }
                GradientStop { position: 1.0; color: "#004a2d16" }
            }
        }
        Rectangle {
            x: parent.width / 2 - 1; width: 12; y: 1; height: parent.height - 2
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#00fff9e1" }
                GradientStop { position: 0.45; color: "#78fff9e1" }
                GradientStop { position: 1.0; color: "#00fff9e1" }
            }
        }
        Rectangle {
            x: parent.width / 2 - 0.5; y: 2; width: 1; height: parent.height - 4
            color: "#785b3b1f"
        }
    }

    // Direct source frame (JPEG/PNG/WebP bytes supplied unchanged by Python).
    Item {
        id: mapBox
        x: Number(radar.popupData.map_x || 0)
        y: Number(radar.popupData.map_y || 0)
        width: Number(radar.popupData.map_w || 0)
        height: Number(radar.popupData.map_h || 0)
        clip: true
        Rectangle { anchors.fill: parent; color: "#f6e4bd"; border.color: "#a046321c"; border.width: 1 }
        Image {
            id: imageA
            anchors.fill: parent; anchors.margins: 1
            source: ""; cache: true; asynchronous: true
            fillMode: Image.PreserveAspectCrop; smooth: true
            visible: !radar.frontB && status === Image.Ready
            onStatusChanged: if (status === Image.Ready) radar.acceptFrame(false, source.toString())
        }
        Image {
            id: imageB
            anchors.fill: parent; anchors.margins: 1
            source: ""; cache: true; asynchronous: true
            fillMode: Image.PreserveAspectCrop; smooth: true
            visible: radar.frontB && status === Image.Ready
            onStatusChanged: if (status === Image.Ready) radar.acceptFrame(true, source.toString())
        }
        Text {
            anchors.fill: parent; anchors.margins: 25
            text: radar.popupData.message || "Preparing radar…"
            color: "#263238"; font.family: "American Typewriter"; font.pixelSize: 16
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            visible: !radar.frontUrl
        }
        Canvas {
            anchors.fill: parent
            visible: !!radar.frontUrl && Number(radar.popupData.image_w || 0) > 0
            property real markerX: {
                var w = Math.max(1, Number(radar.popupData.image_w || 1))
                var h = Math.max(1, Number(radar.popupData.image_h || 1))
                var scale = Math.max((width-2) / w, (height-2) / h)
                return 1 + (width-2-w*scale)/2 + Number(radar.popupData.pin_x || w/2)*scale
            }
            property real markerY: {
                var w = Math.max(1, Number(radar.popupData.image_w || 1))
                var h = Math.max(1, Number(radar.popupData.image_h || 1))
                var scale = Math.max((width-2) / w, (height-2) / h)
                return 1 + (height-2-h*scale)/2 + Number(radar.popupData.pin_y || h/2)*scale
            }
            onMarkerXChanged: requestPaint()
            onMarkerYChanged: requestPaint()
            onPaint: {
                var c = getContext("2d"); c.clearRect(0,0,width,height)
                var a = markerX, b = markerY
                c.beginPath(); c.moveTo(a,b)
                c.bezierCurveTo(a-8,b-10,a-7,b-24,a,b-24)
                c.bezierCurveTo(a+7,b-24,a+8,b-10,a,b)
                c.closePath(); c.lineWidth=1.5
                c.fillStyle="rgba(0,0,0,0.45)"; c.strokeStyle="rgba(0,0,0,0.60)"
                c.fill(); c.stroke()
            }
        }
    }

    // Match RadarTimelineView's original line, endpoints, dot sizes, per-hour
    // labels and observed/predicted colors; no QWidget screenshot required.
    Item {
        id: timeline
        x: Number(radar.popupData.timeline_x || 0)
        y: Number(radar.popupData.timeline_y || 0)
        width: Number(radar.popupData.timeline_w || 0)
        height: Number(radar.popupData.timeline_h || 0)
        visible: height > 0
        Rectangle { anchors.fill: parent; color: "#78f6e4bd" }
        property int count: (radar.popupData.times || []).length
        property real endpoint: Math.max(22, timeline.count > 9 ? 27 : 31)
        property real firstX: 10 + endpoint
        property real lastX: width - 11 - endpoint
        Rectangle { x: timeline.firstX; y: 24; width: Math.max(0,timeline.lastX-timeline.firstX); height: 2; color: "#5a3c21" }
        Repeater {
            model: radar.popupData.times || []
            delegate: Item {
                property bool activeFrame: index === Number(radar.popupData.frame_index || 0)
                property real dotX: timeline.count === 1 ? (timeline.firstX+timeline.lastX)/2 :
                                timeline.firstX + (timeline.lastX-timeline.firstX)*index/(timeline.count-1)
                x: dotX; y: 0; width: 1; height: timeline.height
                Rectangle {
                    x: activeFrame ? -6 : -3
                    y: activeFrame ? 19 : 22
                    width: activeFrame ? 12 : 6
                    height: width; radius: width/2
                    color: activeFrame ? (modelData.predicted ? "#1f5dcc" : "#000000") : "#f6e4bd"
                    border.color: activeFrame ? (modelData.predicted ? "#1f5dcc" : "#000000") : "#684723"
                    border.width: activeFrame ? 2 : 1
                }
                Rectangle { x: 0; y: 30; width: 1; height: 5; color: "#684723" }
                Text {
                    x: -60; y: 52; width: 120; height: 29
                    text: modelData.text || ""
                    font.family: "American Typewriter"
                    font.pixelSize: timeline.count <= 9 ? 18 : 14
                    font.bold: activeFrame
                    color: modelData.predicted ? "#1f5dcc" : "#000000"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    Text {
        x: Number(radar.popupData.legend_x || 0)
        y: Number(radar.popupData.legend_y || 0)
        width: Number(radar.popupData.legend_w || 0)
        height: Number(radar.popupData.legend_h || 0)
        text: radar.popupData.legend || ""
        textFormat: Text.RichText
        font.family: "American Typewriter"
        verticalAlignment: Text.AlignVCenter
    }
    Text {
        x: Number((radar.popupData.page_title && radar.popupData.page_title.x) || 0)
        y: Number((radar.popupData.page_title && radar.popupData.page_title.y) || 0)
        width: Number((radar.popupData.page_title && radar.popupData.page_title.w) || 0)
        height: Number((radar.popupData.page_title && radar.popupData.page_title.h) || 0)
        text: "SELECTED FORECAST HOUR"
        color: radar.popupData.dark ? "#ead3a3" : "#1b130c"
        font.family: "Georgia"; font.pixelSize: 19; font.weight: Font.Black
        verticalAlignment: Text.AlignVCenter
    }
    Repeater {
        model: radar.popupData.details || []
        delegate: Text {
            x: Number(modelData.x); y: Number(modelData.y)
            width: Number(modelData.w); height: Number(modelData.h)
            text: modelData.text
            color: radar.popupData.dark ? "#ead3a3" : "#1b130c"; font.family: "American Typewriter"
            font.pixelSize: 15; font.bold: true
            wrapMode: Text.WordWrap; clip: true
            verticalAlignment: Text.AlignTop
        }
    }
    Repeater {
        model: radar.popupData.rules || []
        delegate: Rectangle {
            x: Number(modelData.x); y: Number(modelData.y)
            width: Number(modelData.w); height: Math.max(1, Number(modelData.h))
            color: "#875a4e3f"
        }
    }
    Repeater {
        model: radar.popupData.controls || []
        delegate: Rectangle {
            id: ctl
            z: 100
            x: Number(modelData.x); y: Number(modelData.y)
            width: Number(modelData.w); height: Number(modelData.h)
            radius: modelData.zoom ? 6 : 5
            color: radar.popupData.dark ? "#42596b" : (modelData.enabled ? "#f3e6c9" : "#a67e7567")
            border.width: radar.popupData.focus === modelData.id ? 3 : 2
            border.color: radar.popupData.focus === modelData.id ? "#ffe12e" : "#d246321c"
            Text {
                anchors.fill: parent
                text: modelData.text
                color: radar.popupData.focus === modelData.id ? "#a27c00" : (radar.popupData.dark ? "#ead3a3" : (modelData.enabled ? "#24170d" : "#8050271c"))
                font.family: "Georgia"
                font.pixelSize: modelData.zoom ? 25 : 16
                font.weight: Font.Black
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
