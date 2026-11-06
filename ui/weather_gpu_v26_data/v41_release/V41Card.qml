import QtQuick

Item {
    id: root
    width: 480
    height: 78
    property bool dateCardFullBleed: false

    property string condition: "clear"   // clear, partly, cloudy, fog, snow, heavysnow
    property string phase: "day"         // dawn, day, dusk, night
    property bool moving: true
    property real seconds: 0
    property double startedAt: Date.now()

    property var smallWidths: [52.3, 42.3, 55.3, 45.3, 49.7]
    property var smallHeights: [37, 30, 39, 32, 35]

    property real bigWidth: 180
    property real bigHeight: 81

    onMovingChanged: {
        if (moving)
            startedAt = Date.now() - seconds * 1000
    }

    Timer {
        interval: 67
        repeat: true
        running: false
        onTriggered: root.seconds = (Date.now() - root.startedAt) / 1000.0
    }

    function posmod(value, length) {
        return ((value % length) + length) % length;
    }

    function topColor() {
        if (["lightrain", "rain", "heavyrain", "storm"].indexOf(root.condition) >= 0)
            return root.phase === "night" ? "#536978" :
                (root.phase === "dawn" ? "#927C79" :
                (root.phase === "dusk" ? "#85737C" : "#6F8794"))

        if (root.phase === "night")
            return "#1F2E40"
        if (root.phase === "dawn") {
            if (root.condition === "clear" || root.condition === "partly")
                return "#F8A66E"
            return "#BDB2AA"
        }
        if (root.phase === "dusk") {
            if (root.condition === "clear" || root.condition === "partly")
                return "#F2A067"
            return "#AEA39B"
        }
        if (root.condition === "clear" || root.condition === "partly")
            return "#7FC7F8"
        if (root.condition === "cloudy")
            return "#91ADB9"
        if (root.condition === "snow" || root.condition === "heavysnow")
            return "#9EBAC6"
        return "#C6CBC2"
    }

    function bottomColor() {
        if (["lightrain", "rain", "heavyrain", "storm"].indexOf(root.condition) >= 0)
            return root.phase === "night" ? "#30455A" :
                (root.phase === "dawn" ? "#665966" :
                (root.phase === "dusk" ? "#62525F" : "#394F5B"))

        if (root.phase === "night")
            return "#172536"
        if (root.phase === "dawn") {
            if (root.condition === "clear" || root.condition === "partly")
                return "#FFE2B2"
            return "#D2CAC2"
        }
        if (root.phase === "dusk") {
            if (root.condition === "clear" || root.condition === "partly")
                return "#FFD49F"
            return "#C6BCB4"
        }
        if (root.condition === "clear" || root.condition === "partly")
            return "#CBEFFF"
        if (root.condition === "cloudy")
            return "#C3D3D8"
        if (root.condition === "snow" || root.condition === "heavysnow")
            return "#D2E1E5"
        return "#BAC4C0"
    }

    function showNightBackground() {
        return root.phase === "night";
    }

    function showSun() {
        return root.phase !== "night";
    }

    function showBigClouds() {
        return root.condition === "cloudy"; // V41_NIGHT_CLOUDS_V2
    }

    function showSmallClouds() {
        return root.condition === "partly" || root.condition === "cloudy";
    }

    function showPartlyCloud(i) {
        return true; // all 5 clouds visible for partly cloudy
    }

    function smallX(i) {
        var speeds = [4.2, 5.2, 6.8, 8.0, 9.1];
        return -80 + posmod(speeds[i] * seconds + i * 116, 700);
    }

    function smallY(i) {
        if (root.condition === "partly")
            return [11, 23, 7, 20, 14][i];
        return [12, 39, 9, 34, 18][i];
    }

    function bigX(offset) {
        return -root.bigWidth - 18 + posmod(2.6 * seconds + offset, 960);
    }

    function snowCount() {
        if (root.condition === "heavysnow")
            return 27;
        if (root.condition === "snow")
            return 18;
        return 0;
    }

    function snowX(i) {
        return 10 + posmod(i * 31 + seconds * (8 + (i % 3)), 458);
    }

    function snowY(i) {
        return -10 + posmod(seconds * (18 + (i % 4) * 4) + i * 13, 108);
    }

    function snowSize(i) {
        return 9 + (i % 3) * 2.5;
    }

    function fogX() {
        return -180 + posmod(seconds * 4.0, 700);
    }

    Item {
        width: 480
        height: 78
        scale: 1
        transform: Scale {
            origin.x: 0
            origin.y: 0
            xScale: root.width / 480
            yScale: root.height / 78
        }
        transformOrigin: Item.TopLeft
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: root.dateCardFullBleed ? 0 : 14
            gradient: Gradient {
                GradientStop { position: 0; color: root.topColor() }
                GradientStop { position: 1; color: root.bottomColor() }
            }
            border.color: "#D5C690"
            border.width: 1
        }

        Image {
            anchors.fill: parent
            visible: root.showNightBackground()
            source: Qt.resolvedUrl("assets/original_night.png")
            fillMode: Image.Stretch
            cache: true
            smooth: true
        }

        // Realer sun with halo + rays, shifted right and 25% out of frame.
        Item {
            visible: root.showSun() &&
                     (root.condition === "clear" || root.condition === "partly")
            x: 414
            y: -15
            width: 64
            height: 64
            scale: 0.5

            Rectangle {
                anchors.centerIn: parent
                width: 96
                height: 96
                radius: 48
                color: root.phase === "dawn" ? "#FFD598" :
                       root.phase === "dusk" ? "#FFC97B" :
                       "#FFF2A6"
                opacity: 0.16
            }

            Rectangle {
                anchors.centerIn: parent
                width: 78
                height: 78
                radius: 39
                color: root.phase === "dawn" ? "#FFD088" :
                       root.phase === "dusk" ? "#FFC36A" :
                       "#FFE884"
                opacity: 0.24
            }

            Repeater {
                model: 10
                delegate: Rectangle {
                    property real angle:
                        index * Math.PI * 2 / 10

                    x: 32 + Math.cos(angle) * 39 - width / 2
                    y: 32 + Math.sin(angle) * 39 - height / 2

                    width: 14
                    height: 2.4
                    radius: 1.2
                    rotation: angle * 180 / Math.PI
                    color: root.phase === "dawn" ? "#FFE1A8" :
                           root.phase === "dusk" ? "#FFD38A" :
                           "#FFF6B8"
                    opacity: 0.60 + 0.16 * Math.sin(root.seconds * 0.55 + index * 0.5)
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 54
                height: 54
                radius: 27
                color: root.phase === "dawn" ? "#FFD487" :
                       root.phase === "dusk" ? "#FFC263" :
                       "#FFE36F"
                opacity: 0.98
            }

            Rectangle {
                anchors.centerIn: parent
                width: 42
                height: 42
                radius: 21
                color: root.phase === "dawn" ? "#FFE8B8" :
                       root.phase === "dusk" ? "#FFD58E" :
                       "#FFF0A0"
                opacity: 0.22
            }
        }

        // Approved V39 cloudy large clouds
        Image {
            visible: root.showBigClouds()
            opacity: root.phase === "night" ? 0.63 : 1.0
            source: Qt.resolvedUrl("assets/large_A.png")
            width: root.bigWidth
            height: root.bigHeight
            x: root.bigX(0)
            y: -4
            fillMode: Image.PreserveAspectFit
            smooth: true
            cache: true
        }

        Image {
            visible: root.showBigClouds()
            opacity: root.phase === "night" ? 0.63 : 1.0
            source: Qt.resolvedUrl("assets/large_B.png")
            width: root.bigWidth
            height: root.bigHeight
            x: root.bigX(480)
            y: -4
            fillMode: Image.PreserveAspectFit
            smooth: true
            cache: true
        }

        // Small cloud layer
        Repeater {
            model: 5
            delegate: Image {
                visible: root.showSmallClouds() &&
                         (root.condition !== "partly" || root.showPartlyCloud(index))
                source: Qt.resolvedUrl("assets/small_" + (index + 1) + ".png")
                width: root.smallWidths[index]
                height: root.smallHeights[index]
                x: root.smallX(index)
                y: root.smallY(index)
                fillMode: Image.PreserveAspectFit
                smooth: true
                cache: true
                opacity: root.phase === "night" ? 0.66 : (root.condition === "partly" ? 0.97 : 1.0)
            }
        }

        // Curvier single fog blob
        Item {
            visible: root.condition === "fog"
            x: -22
            y: -3 + 2.5 * Math.sin(root.seconds * 0.46)
            width: 524
            height: 84
            opacity: 0.87

            Canvas {
                anchors.fill: parent
                onPaint: {
                    var c = getContext("2d");
                    c.clearRect(0, 0, width, height);
                    c.save();
                    c.scale(width / 430, height / 64);

                    c.fillStyle = "rgba(244,248,251,0.85)";
                    c.beginPath();
                    c.moveTo(0, 48);
                    c.bezierCurveTo(24, 26, 54, 20, 90, 28);
                    c.bezierCurveTo(110, 6, 148, 4, 174, 18);
                    c.bezierCurveTo(198, -2, 244, 2, 268, 20);
                    c.bezierCurveTo(296, 6, 334, 10, 356, 26);
                    c.bezierCurveTo(386, 18, 410, 24, 418, 40);
                    c.bezierCurveTo(430, 54, 414, 60, 374, 58);
                    c.lineTo(28, 62);
                    c.bezierCurveTo(9, 62, 0, 56, 0, 48);
                    c.closePath();
                    c.fill();

                    c.fillStyle = "rgba(255,255,255,0.30)";
                    c.beginPath();
                    c.moveTo(82, 30);
                    c.bezierCurveTo(118, 18, 172, 18, 214, 26);
                    c.bezierCurveTo(252, 16, 312, 18, 346, 30);
                    c.bezierCurveTo(326, 20, 282, 18, 238, 24);
                    c.bezierCurveTo(188, 14, 124, 16, 82, 30);
                    c.closePath();
                    c.fill();
                    c.restore();
                }
            }
        }


        Item {
            id: v41Rain
            anchors.fill: parent
            clip: true
            visible: ["lightrain", "rain", "heavyrain", "storm"]
                .indexOf(root.condition) >= 0

            readonly property string kind:
                root.condition === "storm" ? "rain" : root.condition
            readonly property real shift:
                root.posmod(root.seconds * 13.0, 160)

            Image {
                source: v41Rain.visible ? Qt.resolvedUrl("assets/" + v41Rain.kind + ".png") : ""
                width: 480
                height: 160
                y: v41Rain.shift - 160
                cache: true
            }
            Image {
                source: v41Rain.visible ? Qt.resolvedUrl("assets/" + v41Rain.kind + ".png") : ""
                width: 480
                height: 160
                y: v41Rain.shift
                cache: true
            }
        }

        Item {
            id: v41Bolt
            anchors.fill: parent
            clip: true
            visible: root.condition === "storm" && growth > 0

            readonly property real t:
                root.posmod(root.seconds * 24, 120)

            readonly property bool first: t >= 18 && t < 27
            readonly property bool second: t >= 66 && t < 72.5

            readonly property real growth:
                first ? (t < 24 ? (t - 18) / 6 : 1) :
                (second ? (t < 70 ? (t - 66) / 4 : 1) : 0)

            readonly property int variant:
                (Math.floor(root.seconds / 5) * 2 +
                (t >= 50 ? 1 : 0)) % 10

            Item {
                width: 480
                height: v41Bolt.growth * 78
                clip: true

                Image {
                    source: Qt.resolvedUrl(
                        "assets/lightning_" + v41Bolt.variant + ".png"
                    )
                    width: 480
                    height: 78
                    cache: true
                }
            }

            Rectangle {
                anchors.fill: parent
                color: "white"
                opacity: v41Bolt.first ? 0.14 :
                    (v41Bolt.second ? 0.07 : 0)
            }
        }

        // Snowflakes
        Repeater {
            model: root.snowCount()
            delegate: Item {
                x: root.snowX(index)
                y: root.snowY(index)
                width: root.snowSize(index)
                height: width
                opacity: 0.94

                Canvas {
                    anchors.fill: parent
                    onPaint: {
                        var c = getContext("2d");
                        c.clearRect(0, 0, width, height);

                        var cx = width / 2;
                        var cy = height / 2;
                        var r = width * 0.46;

                        c.strokeStyle = "#F8FCFF";
                        c.lineWidth = 0.9;
                        c.lineCap = "round";
                        c.beginPath();

                        for (var a = 0; a < 6; a++) {
                            var t = a * Math.PI / 3;
                            var ex = cx + Math.cos(t) * r;
                            var ey = cy + Math.sin(t) * r;
                            c.moveTo(cx, cy);
                            c.lineTo(ex, ey);

                            var jx = cx + Math.cos(t) * r * 0.66;
                            var jy = cy + Math.sin(t) * r * 0.66;

                            for (var sign = -1; sign <= 1; sign += 2) {
                                var ang = t + sign * Math.PI / 3;
                                c.moveTo(jx, jy);
                                c.lineTo(
                                    jx - Math.cos(ang) * r * 0.30,
                                    jy - Math.sin(ang) * r * 0.30
                                );
                            }
                        }
                        c.stroke();
                    }
                }
            }
        }

    }
}
