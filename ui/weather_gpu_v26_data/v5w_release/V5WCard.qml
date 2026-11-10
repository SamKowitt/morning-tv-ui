// V5W approved weather artwork — standalone test
import QtQuick
import QtQuick.Window
import QtMultimedia
Item {
    id: root
    width: 262
    height: 78
    clip: true
    property string condition: "clear_sky"
    property string phase: "day"
    property string phaseMode: phase
    property bool nighttime: phaseMode === "night"
    property real cloudBandFraction: 0.65
    property int cardW: width
    property int cardH: height
    property double galleryEpochMs: Date.now()
    property var cloudCoverData: ({})
    function galleryPositionMs() {
        return Math.floor((Date.now() - galleryEpochMs) % 200000);
    }

    // V5W_SMOKE_ASSET_BINDING_FIX — staging only
    function particleSprite(layer, i) {
        var c = root.condition;
        var name = "";

        if (layer === "rain") {
            if (c === "light_rain") name = "rain_light_v5t";
            else if (c === "rain") name = "rain_normal_v5p";
            else if (c === "heavy_rain") name = "rain_heavy_v5p";
            else if (c === "thunderstorms") name = "rain_storm_v5p";
            else if (c === "wintry_mix") name = "rain_light_v5l";
        } else if (layer === "near" || layer === "far") {
            if (c === "heavy_snow") {
                name = "snow_" + layer + "_" +
                    (root.phase === "day" ? "heavy_day_v5u" : "heavy_v5t");
            } else if (c === "flurries" || c === "snow" || c === "wintry_mix") {
                name = "snow_" + layer + "_" +
                    (c === "flurries" ? "flurries" : "snow");
            }
        } else if (layer === "hail" && c === "hail") {
            name = "hail";
        }

        return name === "" ? "" : Qt.resolvedUrl(
            "assets/v5v_particle_spawn/" + name + "_g" + i + ".png");
    }

    property var models: ({
  "clear_sky": {
    "key": "clear_sky",
    "name": "Clear Sky",
    "cloud": "",
    "rain": "",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": true
  },
  "mostly_clear": {
    "key": "mostly_clear",
    "name": "Mostly Clear",
    "cloud": "mostly",
    "rain": "",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": true
  },
  "partly_cloudy": {
    "key": "partly_cloudy",
    "name": "Partly Cloudy",
    "cloud": "partly",
    "rain": "",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": true
  },
  "cloudy": {
    "key": "cloudy",
    "name": "Cloudy",
    "cloud": "cloudy",
    "rain": "",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "fog": {
    "key": "fog",
    "name": "Fog",
    "cloud": "",
    "rain": "",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": true,
    "sun": false
  },
  "light_rain": {
    "key": "light_rain",
    "name": "Light Rain",
    "cloud": "cloudy",
    "rain": "rain_light",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "rain": {
    "key": "rain",
    "name": "Rain",
    "cloud": "cloudy",
    "rain": "rain_normal",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "heavy_rain": {
    "key": "heavy_rain",
    "name": "Heavy Rain",
    "cloud": "cloudy",
    "rain": "rain_heavy",
    "snow": "",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "thunderstorms": {
    "key": "thunderstorms",
    "name": "Thunderstorms",
    "cloud": "cloudy",
    "rain": "rain_storm",
    "snow": "",
    "hail": false,
    "storm": true,
    "fog": false,
    "sun": false
  },
  "flurries": {
    "key": "flurries",
    "name": "Light Snow / Flurries",
    "cloud": "cloudy",
    "rain": "",
    "snow": "flurries",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "snow": {
    "key": "snow",
    "name": "Snow",
    "cloud": "cloudy",
    "rain": "",
    "snow": "snow",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "heavy_snow": {
    "key": "heavy_snow",
    "name": "Heavy Snow",
    "cloud": "cloudy",
    "rain": "",
    "snow": "heavy",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "wintry_mix": {
    "key": "wintry_mix",
    "name": "Wintry Mix",
    "cloud": "cloudy",
    "rain": "rain_light",
    "snow": "snow",
    "hail": false,
    "storm": false,
    "fog": false,
    "sun": false
  },
  "hail": {
    "key": "hail",
    "name": "Hail",
    "cloud": "cloudy",
    "rain": "",
    "snow": "",
    "hail": true,
    "storm": false,
    "fog": false,
    "sun": false
  }
})
    // V2_RESTORED_PREVIEW_COLOR_AND_SEAM_V1
    function grayFamily(key) {
        return ["cloudy", "fog", "light_rain", "rain", "heavy_rain", "thunderstorms",
                "flurries", "snow", "heavy_snow", "wintry_mix", "hail"].indexOf(key) >= 0;
    }
    function topSky(key) {
        var g = grayFamily(key);
        if (nighttime) return g ? "#52677d" : "#0b2149";
        if (g) return phaseMode === "dawn" || phaseMode === "dusk" ? "#788fa7" : "#7895ad";
        return "#5e8fc8";
    }
    function bottomSky(key) {
        var g = grayFamily(key);
        if (nighttime) return g ? "#70879b" : "#24487c";
        if (g) return phaseMode === "dawn" || phaseMode === "dusk" ? "#9eb4c6" : "#a0b9ca";
        if (phaseMode === "dawn" || phaseMode === "dusk") return "#c6b9b3";
        return "#9cc4ee";
    }
    function skyColorAt(key, f) {
        var a = topSky(key);
        var b = bottomSky(key);
        function channel(hex, offset) { return parseInt(hex.substr(offset,2),16)/255.0; }
        return Qt.rgba(
            channel(a,1)+(channel(b,1)-channel(a,1))*f,
            channel(a,3)+(channel(b,3)-channel(a,3))*f,
            channel(a,5)+(channel(b,5)-channel(a,5))*f, 1);
    }
    function fadeSkyAt(key, f, alpha) {
        var c = skyColorAt(key, f);
        return Qt.rgba(c.r, c.g, c.b, alpha);
    }
    function timeLabel() {
        return nighttime ? "9pm" : phaseMode === "dawn" ? "6am" : phaseMode === "dusk" ? "6pm" : "4pm";
    }

    Item {
        id: entry
        anchors.fill: parent
        property var modelData: root.models[root.condition] || root.models["cloudy"]
        property bool hasCloud: modelData.cloud.length > 0
        property bool hasRain: modelData.rain.length > 0
        property bool hasSnow: modelData.snow.length > 0
        property bool isStorm: modelData.storm
        property bool isFog: modelData.fog
        property bool isHail: modelData.hail
        property int activeBolt: 0
        property real cloudPosition: cloudMovie.item ? cloudMovie.item.playbackPosition : 0
        property real cloudCover: {
            if (cloudMovie.item && cloudMovie.item.sunOcclusion !== undefined)
                return cloudMovie.item.sunOcclusion;
            if (!entry.hasCloud) return 0;
            if (entry.modelData.cloud === "cloudy") return 1;
            var s = cloudCoverData[entry.modelData.cloud];
            if (!s || s.length < 1) return 0.3;
            var idx = Math.floor(entry.cloudPosition / 1000) % s.length;
            return s[Math.max(0,idx)];
        }
        Rectangle {
            id: card
            x: 0; y: 0
            width: root.cardW; height: root.cardH
            radius: 13
            color: root.bottomSky(entry.modelData.key)
            clip: true
            // Uniform sky gradient across the ENTIRE card. Unlike the old
            // sky PNG, its color is known exactly at the 65% boundary.
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    GradientStop { position: 0.0; color: root.topSky(entry.modelData.key) }
                    GradientStop { position: 1.0; color: root.bottomSky(entry.modelData.key) }
                }
            }

            // Subtle stars only on clear/mostly-clear nighttime.
            Item {
                anchors.fill: parent
                visible: root.nighttime &&
                    (entry.modelData.key === "clear_sky" || entry.modelData.key === "mostly_clear")
                Repeater {
                    model: entry.modelData.key === "clear_sky" ? 22 : 12
                    delegate: Rectangle {
                        id: star
                        property int starIndex: index
                        property real b: 0.9 + (index % 4) * 0.17
                        x: 7 + (index * 97 + 19) % (card.width - 15)
                        y: 5 + (index * 39 + 7) % (card.height * 0.51)
                        width: b; height: b; radius: b/2
                        color: index % 7 === 0 ? "#fff7e4" : "#f7f9ff"
                        opacity: 0.45
                        SequentialAnimation on opacity {
                            running: root.nighttime
                            loops: Animation.Infinite
                            NumberAnimation { from: 0.32; to: 0.69; duration: 13000 + (star.starIndex % 7)*1100 }
                            NumberAnimation { from: 0.69; to: 0.32; duration: 13000 + (star.starIndex % 7)*1100 }
                        }
                    }
                }
            }

            // Exactly the same approved reference frames for PARTLY CLOUDY;
            // its two variants are processed from the same 200s source video.
            // Clouds never appear in the lower 35% of an hourly card.
            Item {
                id: cloudClip
                visible: entry.hasCloud
                width: parent.width
                // V5: precomposited overcast cloud videos include sky below 65%,
                // so the VIDEO spans the card, while cloud DETAIL is only in top 65%.
                height: parent.height * (root.grayFamily(entry.modelData.key) ? 1.0 : root.cloudBandFraction)
                x: 0; y: 0
                clip: true
                Loader {
                    id: cloudMovie
                    anchors.fill: parent
                    active: entry.hasCloud
                    sourceComponent: (entry.modelData.key === "mostly_clear" ||
                                      entry.modelData.key === "partly_cloudy")
                                     ? sparseCloudComponent
                                     : (root.grayFamily(entry.modelData.key) ? smoothCloudComponent : cloudComponent)
                }
                // Cloud footage contains baked-in sky. It MUST be gradually
                // replaced by the *underlying gradient at the same Y*,
                // otherwise a hard color jump appears at the 65% edge.
                // The video is still strictly clipped to the top 65%.
                Rectangle {
                    visible: !root.grayFamily(entry.modelData.key)
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: cloudClip.height * 0.58
                    gradient: Gradient {
                        GradientStop { position: 0.00; color: root.fadeSkyAt(entry.modelData.key, 0.273, 0.00) }
                        GradientStop { position: 0.20; color: root.fadeSkyAt(entry.modelData.key, 0.348, 0.08) }
                        GradientStop { position: 0.40; color: root.fadeSkyAt(entry.modelData.key, 0.423, 0.29) }
                        GradientStop { position: 0.60; color: root.fadeSkyAt(entry.modelData.key, 0.499, 0.61) }
                        GradientStop { position: 0.80; color: root.fadeSkyAt(entry.modelData.key, 0.575, 0.90) }
                        GradientStop { position: 1.00; color: root.fadeSkyAt(entry.modelData.key, 0.650, 1.00) }
                    }
                }
            }

            // MORNINGUI_V5_SMOOTH_GPU_CLOUD_DRIFT
            // Continuous subpixel movement of approved V5 art.
            Component {
                id: smoothCloudComponent

                Item {
                    id: smoothCloudRoot
                    clip: true

                    property real playbackPosition:
                        Math.max(0, Math.round(
                            (-cloudSprite.x / Math.max(1, width))
                            * 200000
                        ))

                    Image {
                        id: cloudSprite
                        x: 0
                        y: 0

                        // Two identical seamless cloud tiles.
                        width: smoothCloudRoot.width * 2
                        height: smoothCloudRoot.height

                        source: Qt.resolvedUrl(
                            "assets/cloud_ref_tile_"
                            + (root.phaseMode === "dawn" ? "dusk" : root.phaseMode) + ".png"
                        )

                        fillMode: Image.Stretch
                        smooth: true
                        mipmap: true
                        cache: true

                        // Continuous translation calculated by Qt.
                        // No stepping through video frames.
                        NumberAnimation on x {
                            from: 0
                            to: -smoothCloudRoot.width
                            duration: 40000
                            easing.type: Easing.Linear
                            loops: Animation.Infinite
                            running: true
                        }
                    }
                }
            }


            // MORNINGUI_V5K_SPARSE_REFERENCE_CLOUDS
            Component {
                id: sparseCloudComponent

                Item {
                    id: sparseRoot
                    clip: true

                    property real playbackPosition:
                        Math.round(
                            (-sparseStrip.x / Math.max(1,width))
                            * 40000
                        )

                    function cloudAt(f) {
                        var u = ((f % 1) + 1) % 1;

                        function blob(c, r) {
                            var d = Math.abs(u - c);
                            d = Math.min(d, 1 - d);
                            return Math.exp(
                                -0.5 * Math.pow(d / r, 2)
                            );
                        }

                        if (entry.modelData.key === "mostly_clear")
                            return blob(0.45, 0.105);

                        return Math.max(
                            blob(0.22, 0.100),
                            blob(0.72, 0.115)
                        );
                    }

                    property real sunOcclusion:
                        cloudAt(
                            (0.72*card.width-sparseStrip.x)
                            / Math.max(1,width)
                        )

                    Image {
                        id: sparseStrip
                        x: 0
                        y: 0

                        width: sparseRoot.width*2
                        height: sparseRoot.height

                        source: Qt.resolvedUrl(
                            "assets/cloud_fair_"
                            + entry.modelData.key
                            + "_" + root.phaseMode + "_v5l.png"
                        )

                        fillMode: Image.Stretch
                        smooth: true
                        mipmap: true
                        cache: true

                        NumberAnimation on x {
                            from: 0
                            to: -sparseRoot.width
                            duration: 40000
                            easing.type: Easing.Linear
                            loops: Animation.Infinite
                            running: true
                        }
                    }
                }
            }

            Component {
                id: cloudComponent
                Item {
                    property real playbackPosition: videoPlayer.position
                    VideoOutput {
                        id: videoDisplay
                        anchors.fill: parent
                        fillMode: VideoOutput.PreserveAspectCrop
                    }
                    MediaPlayer {
                        id: videoPlayer
                        source: root.grayFamily(entry.modelData.key)
                            ? Qt.resolvedUrl("assets/cloud_ref_" + root.phaseMode + "_200s.mp4")
                            : Qt.resolvedUrl("assets/cloud_" + entry.modelData.cloud + "_200s.mp4")
                        loops: MediaPlayer.Infinite
                        videoOutput: videoDisplay
                        audioOutput: AudioOutput { muted: true }
                        // Synchronize video frames across tab changes.
                        property bool resumePending: true

                        function resumeAtClock() {
                            if (!resumePending)
                                return;

                            if (!seekable || duration < 1000) {
                                if (mediaStatus === MediaPlayer.LoadedMedia)
                                    play();
                                return;
                            }

                            var target = root.galleryPositionMs() % duration;

                            resumePending = false;
                            position = Math.floor(target);
                            play();
                        }

                        onSourceChanged: {
                            resumePending = true;
                        }

                        onMediaStatusChanged: {
                            if (mediaStatus === MediaPlayer.LoadedMedia ||
                                mediaStatus === MediaPlayer.BufferedMedia ||
                                mediaStatus === MediaPlayer.BufferingMedia)
                                resumeAtClock();
                        }

                        onSeekableChanged: resumeAtClock()
                        onDurationChanged: resumeAtClock()

                        Component.onCompleted: {
                            play();
                            resumeAtClock();
                        }

                        onErrorOccurred: function(code, msg) {
                            console.warn("CLOUD VIDEO ERROR", entry.modelData.key, msg)
                        }
                    }
                    Rectangle {
                        anchors.fill: parent
                        color: root.grayFamily(entry.modelData.key)
                            ? root.topSky(entry.modelData.key) : "#081b36"
                        // V5 cloud artwork already contains the atmospheric sky.
                        // Don't wash out the actual cloud pixels again.
                        opacity: root.grayFamily(entry.modelData.key)
                            ? 0.0 : (root.nighttime ? 0.45 : 0.0)
                    }
                }
            }

            // Sun and current-phase lunar artwork use the same disk size.
            // The moon PNG is regenerated from the production Moon-phase
            // painter function whenever the gallery launches.

            // V5K transparent halo

            // MORNINGUI_V5L_FAIR_CLOUD_RAIN_HALO
            Image {
                id: sunHaloV5K

                visible: root.phaseMode === "day"
                         && entry.modelData.sun

                width: 116
                height: 116

                x: Math.round(
                    card.width * 0.72 - width / 2
                )
                y: Math.round(22 - height / 2)

                source: Qt.resolvedUrl(
                    "assets/sun_halo_v5l.png"
                )

                smooth: true

                opacity: 0.94 * (
                    1.0 -
                    Math.min(1.0, entry.cloudCover) * 0.91
                )
            }

            Image {
                id: heavenlyBody
                visible: root.nighttime
                    ? (entry.modelData.key === "clear_sky" || entry.modelData.key === "mostly_clear" || entry.modelData.key === "partly_cloudy")
                    : (root.phaseMode === "day" && entry.modelData.sun)
                source: Qt.resolvedUrl(root.nighttime
                    ? "assets/moon_phase_current.png" : "assets/sun_glow.png")
                width: 44; height: 44
                x: Math.round(card.width * 0.72 - width / 2)
                y: 1
                smooth: true
                opacity: entry.modelData.key === "partly_cloudy"
                    ? Math.max(0.12, 1.0 - entry.cloudCover * 0.88)
                    : entry.modelData.key === "mostly_clear"
                      ? Math.max(0.65, 1.0 - entry.cloudCover * 0.30) : 1.0
            }

            // Slow, full-card fog; independent from the cloud height limit.
            Item {
                id: fogClip
                anchors.fill: parent
                visible: entry.isFog
                clip: true
                Item {
                    width: card.width * 2; height: card.height
                    id: fogDrift1
                    x: 0
                    Image {
                        x: 0; y: 0
                        width: card.width; height: card.height
                        source: Qt.resolvedUrl("assets/fog_layer_0.png")
                    }
                    Image {
                        x: card.width; y: 0
                        width: card.width; height: card.height
                        source: Qt.resolvedUrl("assets/fog_layer_0.png")
                    }
                    NumberAnimation on x {
                        running: entry.isFog
                        from: 0; to: -card.width
                        duration: 95000; loops: Animation.Infinite
                        easing.type: Easing.Linear
                    }
                }
                Item {
                    x: -card.width
                    width: card.width * 2; height: card.height
                    opacity: 0.72
                    Image {
                        x: 0; y: 0
                        width: card.width; height: card.height
                        source: Qt.resolvedUrl("assets/fog_layer_1.png")
                    }
                    Image {
                        x: card.width; y: 0
                        width: card.width; height: card.height
                        source: Qt.resolvedUrl("assets/fog_layer_1.png")
                    }
                    NumberAnimation on x {
                        running: entry.isFog
                        from: -card.width; to: 0
                        duration: 79000; loops: Animation.Infinite
                        easing.type: Easing.Linear
                    }
                }
            }

            // Full-height rain; the old accepted precipitation images.
            Item {
                id: rainClip
                // V5S_NIGHT_RAIN_SOFTEN_ONLY
                opacity: root.phaseMode === "night" ? 0.65 : 1.0
                anchors.fill: parent
                clip: true
                visible: entry.hasRain

                property string rainAsset:
                                            entry.modelData.key === "rain" ? "assets/rain_normal_v5p.png" :
                                            entry.modelData.key === "heavy_rain" ? "assets/rain_heavy_v5p.png" :
                                            entry.modelData.key === "thunderstorms" ? "assets/rain_storm_v5p.png" :
                                            ("assets/" +
                                            ((entry.modelData.key === "light_rain" || entry.modelData.key === "wintry_mix")
                                               ? "rain_light_v5l" : entry.modelData.rain) + ".png")

                property string spawnAsset: (entry.modelData.key === "light_rain" ? "assets/rain_light_v5t.png" : rainClip.rainAsset)
                property real scrollY: -card.height

                NumberAnimation on scrollY {
                    running: entry.hasRain
                    from: -card.height
                    to: 0
                    duration: entry.modelData.key === "light_rain" ? 1000 : (entry.modelData.rain === "rain_light" ? 1500 : 890)
                    loops: Animation.Infinite
                    easing.type: Easing.Linear
                }

                Repeater {
                    model: 8

                    delegate: Item {
                        id: rainGate
                        property real entryY:
                            card.height * (0.25 + 0.15 * index / 7)

                        x: 0
                        y: entryY
                        width: card.width
                        height: card.height - entryY
                        clip: true

                        property url sprite: root.particleSprite("rain", index)

                        Image {
                            x: 0
                            y: rainClip.scrollY - rainGate.y
                            width: card.width
                            height: card.height
                            source: rainGate.sprite
                        }

                        Image {
                            x: 0
                            y: rainClip.scrollY + card.height - rainGate.y
                            width: card.width
                            height: card.height
                            source: rainGate.sprite
                        }
                    }
                }
            }
            // Full-height snow: flurries 23%, snow 100% original heavy,
            // and updated heavy snow 150% of original accepted flake count.
            Item {
                id: snowClip
                anchors.fill: parent
                clip: true
                visible: entry.hasSnow

                property string nearAsset: (entry.modelData.key === "heavy_snow" ? (root.phaseMode === "day" ? "assets/snow_near_heavy_day_v5u.png" : "assets/snow_near_heavy_v5t.png") : ("assets/snow_near_" + entry.modelData.snow + ".png"))
                property string farAsset: (entry.modelData.key === "heavy_snow" ? (root.phaseMode === "day" ? "assets/snow_far_heavy_day_v5u.png" : "assets/snow_far_heavy_v5t.png") : ("assets/snow_far_" + entry.modelData.snow + ".png"))

                property real nearScrollY: -card.height
                property real farScrollY: -card.height

                NumberAnimation on nearScrollY {
                    running: entry.hasSnow
                    from: -card.height
                    to: 0
                    duration: 3050
                    loops: Animation.Infinite
                    easing.type: Easing.Linear
                }

                NumberAnimation on farScrollY {
                    running: entry.hasSnow
                    from: -card.height
                    to: 0
                    duration: 5950
                    loops: Animation.Infinite
                    easing.type: Easing.Linear
                }

                Repeater {
                    model: 8

                    delegate: Item {
                        id: nearGate

                        property real entryY:
                            card.height * (0.25 + 0.15 * index / 7)

                        x: 0
                        y: entryY
                        width: card.width
                        height: card.height - entryY
                        clip: true

                        property url sprite: root.particleSprite("near", index)

                        Image {
                            x: 0
                            y: snowClip.nearScrollY - nearGate.y
                            width: card.width
                            height: card.height
                            source: nearGate.sprite
                        }

                        Image {
                            x: 0
                            y: snowClip.nearScrollY + card.height - nearGate.y
                            width: card.width
                            height: card.height
                            source: nearGate.sprite
                        }
                    }
                }

                Repeater {
                    model: 8

                    delegate: Item {
                        id: farGate

                        property real entryY:
                            card.height * (0.25 + 0.15 * index / 7)

                        x: 0
                        y: entryY
                        width: card.width
                        height: card.height - entryY
                        clip: true
                        opacity: 0.70

                        property url sprite: root.particleSprite("far", index)

                        Image {
                            x: 0
                            y: snowClip.farScrollY - farGate.y
                            width: card.width
                            height: card.height
                            source: farGate.sprite
                        }

                        Image {
                            x: 0
                            y: snowClip.farScrollY + card.height - farGate.y
                            width: card.width
                            height: card.height
                            source: farGate.sprite
                        }
                    }
                }
            }
            // Hail pellets use the same fast direction/speed as rain.
            Item {
                id: hailClipV5V
                anchors.fill: parent
                clip: true
                visible: entry.isHail

                property real scrollY: -card.height

                NumberAnimation on scrollY {
                    running: entry.isHail
                    from: -card.height
                    to: 0
                    duration: 880
                    loops: Animation.Infinite
                    easing.type: Easing.Linear
                }

                Repeater {
                    model: 8

                    delegate: Item {
                        id: hailGate

                        property real entryY:
                            card.height * (0.25 + 0.15 * index / 7)

                        x: 0
                        y: entryY
                        width: card.width
                        height: card.height - entryY
                        clip: true

                        property url sprite: root.particleSprite("hail", index)

                        Image {
                            x: 0
                            y: hailClipV5V.scrollY - hailGate.y
                            width: card.width
                            height: card.height
                            source: hailGate.sprite
                        }

                        Image {
                            x: 0
                            y: hailClipV5V.scrollY + card.height - hailGate.y
                            width: card.width
                            height: card.height
                            source: hailGate.sprite
                        }
                    }
                }
            }

            // Twelve bolt sprites based on the approved old lightning;
            // positions across top and nonrepeating variation sequence.

            // MORNINGUI_V5R_REFERENCE_LIGHTNING
            Rectangle {
                id: stormSkyFlash
                anchors.fill: parent
                visible: entry.isStorm
                color: "#e6edf0"
                opacity: 0
            }

            Item {
                id: boltReveal
                width: card.width
                height: card.height
                clip: true
                visible: entry.isStorm

                Image {
                    id: boltImage
                    x: 0
                    y: 0
                    width: card.width
                    height: card.height
                    source: Qt.resolvedUrl(
                        "assets/lightning_v5r_"
                        + ("0" + entry.activeBolt).slice(-2)
                        + ".png"
                    )
                    smooth: true
                    opacity: 0
                }
            }

            SequentialAnimation {
                id: boltSequence
                running: false

                PropertyAction {
                    target: boltReveal
                    property: "height"
                    value: 0
                }
                PropertyAction {
                    target: boltImage
                    property: "opacity"
                    value: 0
                }
                PropertyAction {
                    target: stormSkyFlash
                    property: "opacity"
                    value: 0
                }

                // Rapid downward strike
                ParallelAnimation {
                    NumberAnimation {
                        target: boltReveal
                        property: "height"
                        from: 0
                        to: card.height
                        duration: 105
                    }
                    NumberAnimation {
                        target: boltImage
                        property: "opacity"
                        from: 0
                        to: 1
                        duration: 55
                    }
                    NumberAnimation {
                        target: stormSkyFlash
                        property: "opacity"
                        from: 0
                        to: 0.37
                        duration: 85
                    }
                }

                PauseAnimation { duration: 65 }

                // Cloud illumination subsides
                ParallelAnimation {
                    NumberAnimation {
                        target: boltImage
                        property: "opacity"
                        from: 1
                        to: 0.26
                        duration: 205
                    }
                    NumberAnimation {
                        target: stormSkyFlash
                        property: "opacity"
                        from: 0.37
                        to: 0.025
                        duration: 205
                    }
                }

                PauseAnimation { duration: 65 }

                // Brief secondary flicker
                ParallelAnimation {
                    NumberAnimation {
                        target: boltImage
                        property: "opacity"
                        from: 0.26
                        to: 0.78
                        duration: 33
                    }
                    NumberAnimation {
                        target: stormSkyFlash
                        property: "opacity"
                        from: 0.025
                        to: 0.20
                        duration: 33
                    }
                }

                PauseAnimation { duration: 35 }

                ParallelAnimation {
                    NumberAnimation {
                        target: boltImage
                        property: "opacity"
                        from: 0.78
                        to: 0
                        duration: 190
                    }
                    NumberAnimation {
                        target: stormSkyFlash
                        property: "opacity"
                        from: 0.20
                        to: 0
                        duration: 190
                    }
                }
            }
            Timer {
                interval: 3000
                running: entry.isStorm
                repeat: true
                triggeredOnStart: true
                onTriggered: {
                    entry.activeBolt = (entry.activeBolt + 5) % 12
                    boltSequence.restart()
                }
            }
        }
    }
}
