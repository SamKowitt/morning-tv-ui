import QtQuick

// OLED_FOCUS_V6_STAGED_DIM
// Approved Suggested Colors + 15% dim, presentation only.

Item {
    id: root
    property bool active: false
    property string condition: "clear_sky"
    property string phase: "day"
    visible: active

    function gray() {
        return ["cloudy", "fog", "light_rain", "rain",
                "heavy_rain", "thunderstorms", "flurries",
                "snow", "heavy_snow", "wintry_mix", "hail"]
                .indexOf(condition) >= 0
    }

    function proposedSkyTop() {
        if (phase === "night")
            return gray() ? "#172634" : "#09172c"
        if (phase === "dawn")
            return gray() ? "#303a4a" : "#292b47"
        if (phase === "dusk")
            return gray() ? "#283548" : "#222941"
        return gray() ? "#293e50" : "#1a3152"
    }

    function proposedSkyBottom() {
        if (phase === "night")
            return gray() ? "#293c4e" : "#1b3353"
        if (phase === "dawn")
            return gray() ? "#555463" : "#664d64"
        if (phase === "dusk")
            return gray() ? "#4d4a5d" : "#5e455b"
        return gray() ? "#455e70" : "#436584"
    }

    Rectangle {
        anchors.fill: parent
        opacity: root.phase === "night" ? 0.22 : 0.45
        gradient: Gradient {
            GradientStop { position: 0; color: root.proposedSkyTop() }
            GradientStop { position: 1; color: root.proposedSkyBottom() }
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 13
        color: "transparent"
        border.width: 2
        border.color: "#5b78a8"
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.15
    }
}
