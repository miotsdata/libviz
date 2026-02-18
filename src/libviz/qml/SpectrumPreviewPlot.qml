import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0

Item {
    anchors.fill: parent
    anchors.margins: 20

    property var model: SpectrumPlotModel

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Label {
            text: "MS/MS Spectrum"
            font.bold: true
        }

        Item {
            id: plotContainer
            Layout.fillWidth: true
            Layout.fillHeight: true

            Canvas {
                id: canvas
                anchors.fill: parent

                onPaint: {
                    const ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)

                    if (!model)
                        return

                    const peaks = model.peaks
                    if (!peaks || peaks.length === 0)
                        return

                    const minMz = model.minMz - 5
                    const maxMz = model.maxMz + 5

                    // ---- Define plotting rectangle ----
                    const marginLeft = 50
                    const marginRight = 20
                    const marginTop = 20
                    const marginBottom = 40

                    const plotX = marginLeft
                    const plotY = marginTop
                    const plotWidth = width - marginLeft - marginRight
                    const plotHeight = height - marginTop - marginBottom

                    if (plotWidth <= 0 || plotHeight <= 0)
                        return

                    // ---- Coordinate transforms ----
                    function xToPixel(mz) {
                        return plotX + ((mz - minMz) / (maxMz - minMz)) * plotWidth
                    }

                    function yToPixel(intensity) {
                        return plotY + plotHeight - (intensity / 100.0) * plotHeight
                    }

                    ctx.strokeStyle = "black"
                    ctx.fillStyle = "black"
                    ctx.lineWidth = 1

                    // ---- Draw axes ----
                    ctx.beginPath()
                    ctx.moveTo(plotX, plotY)
                    ctx.lineTo(plotX, plotY + plotHeight)
                    ctx.lineTo(plotX + plotWidth, plotY + plotHeight)
                    ctx.stroke()

                    // ---- Y ticks (0–100 every 20) ----
                    for (let y = 0; y <= 100; y += 20) {
                        const py = yToPixel(y)

                        ctx.beginPath()
                        ctx.moveTo(plotX - 5, py)
                        ctx.lineTo(plotX, py)
                        ctx.stroke()

                        ctx.fillText(y.toString(), plotX - 35, py + 4)
                    }

                    // ---- X ticks (5 total) ----
                    if (maxMz > minMz) {
                        const step = (maxMz - minMz) / 4.0

                        for (let i = 0; i < 5; i++) {
                            const mzValue = minMz + i * step
                            const px = xToPixel(mzValue)

                            ctx.beginPath()
                            ctx.moveTo(px, plotY + plotHeight)
                            ctx.lineTo(px, plotY + plotHeight + 5)
                            ctx.stroke()

                            ctx.fillText(
                                        mzValue.toFixed(1),
                                        px - 20,
                                        plotY + plotHeight + 20
                                        )
                        }
                    }

                    ctx.lineWidth = 5;
                    // ---- Draw peaks (stick spectrum) ----
                    for (let i = 0; i < peaks.length; i++) {
                        const px = xToPixel(peaks[i].mz)
                        const py = yToPixel(peaks[i].intensity)

                        ctx.beginPath()
                        ctx.moveTo(px, plotY + plotHeight)
                        ctx.lineTo(px, py)
                        ctx.stroke()
                    }
                }
            }

            Connections {
                target: model
                function onDataChanged() {
                    canvas.requestPaint()
                }
            }
        }
    }
}
