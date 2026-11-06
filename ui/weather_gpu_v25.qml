import QtQuick

Item {
    id: root
    property var cards: []
    clip: true

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

            Image {
                anchors.fill: parent
                source: tile.info.image
                cache: false
                asynchronous: false
                smooth: true
                fillMode: Image.Stretch
            }

            Item {
                id: driftingClouds
                width: tile.width * 2
                height: tile.height
                visible: tile.info.condition === 'cloud' || tile.info.condition === 'fog'
                Image {
                    width: tile.width; height: tile.height
                    source: 'weather_gpu_assets_v25/cloud_overlay.png'
                    opacity: 0.24
                    smooth: true
                }
                Image {
                    x: tile.width; width: tile.width; height: tile.height
                    source: 'weather_gpu_assets_v25/cloud_overlay.png'
                    opacity: 0.24
                    smooth: true
                }
                XAnimator on x {
                    from: -tile.width
                    to: 0
                    duration: 9000
                    loops: Animation.Infinite
                    running: driftingClouds.visible
                }
            }

            Item {
                id: fallingRain
                width: tile.width
                height: tile.height * 2
                visible: tile.info.condition === 'rain' || tile.info.condition === 'storm'
                Image {
                    width: tile.width; height: tile.height
                    source: 'weather_gpu_assets_v25/rain_overlay.png'
                    opacity: 0.45
                    smooth: true
                }
                Image {
                    y: tile.height; width: tile.width; height: tile.height
                    source: 'weather_gpu_assets_v25/rain_overlay.png'
                    opacity: 0.45
                    smooth: true
                }
                YAnimator on y {
                    from: -tile.height
                    to: 0
                    duration: 1200
                    loops: Animation.Infinite
                    running: fallingRain.visible
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: gpuBridge.choose(tile.info.index)
            }
        }
    }
}
