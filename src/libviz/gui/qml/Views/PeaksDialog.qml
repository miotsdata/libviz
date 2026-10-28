import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// The selected spectrum's peak list (m/z, intensity, % of base peak).
// Non-modal, so it stays open and follows the selection.
Dialog {
    id: dialog
    objectName: "peaksDialog"
    property var spectrum: ({})
    property int sortColumn: 0  // 0 m/z, 1 intensity (relative sorts the same)
    property bool ascending: true

    readonly property var rows: {
        var sp = spectrum
        if (!sp || !sp.mz || !sp.mz.length) return []
        var top = Math.max.apply(null, sp.intensity)
        var r = sp.mz.map(function (m, i) { return [m, sp.intensity[i], top > 0 ? sp.intensity[i] / top * 100 : 0] })
        var c = sortColumn, sign = ascending ? 1 : -1
        r.sort(function (a, b) { return sign * (a[c] - b[c]) })
        return r
    }

    title: spectrum.id !== undefined
           ? qsTr("Peaks · %1 · CE %2 · precursor m/z %3").arg(spectrum.adduct).arg(spectrum.collision_energy)
                                                          .arg(Number(spectrum.precursor_mz).toFixed(4))
           : qsTr("Peaks")
    modal: false
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: 420
    height: Math.min(560, parent ? parent.height * 0.8 : 560)
    padding: 8
    standardButtons: Dialog.Close

    readonly property var columns: [[qsTr("m/z"), 0], [qsTr("Intensity"), 1], [qsTr("Relative %"), 2]]

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        Row {
            Layout.fillWidth: true
            Repeater {
                model: dialog.columns
                ItemDelegate {
                    required property var modelData
                    width: 130
                    height: 24
                    // Relative % is intensity / base peak, so it sorts like intensity.
                    readonly property int key: Math.min(modelData[1], 1)
                    text: modelData[0] + (dialog.sortColumn === key ? (dialog.ascending ? " ▲" : " ▼") : "")
                    font.bold: true
                    font.pixelSize: Theme.captionPixelSize
                    onClicked: {
                        if (dialog.sortColumn === key) dialog.ascending = !dialog.ascending
                        else { dialog.sortColumn = key; dialog.ascending = key === 0 }
                    }
                }
            }
        }

        ListView {
            id: list
            objectName: "peaksList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: dialog.rows
            ScrollBar.vertical: ScrollBar {}
            delegate: Rectangle {
                required property var modelData
                required property int index
                width: ListView.view.width
                height: 22
                color: index % 2 ? Theme.fieldColor : "transparent"
                Row {
                    anchors.verticalCenter: parent.verticalCenter
                    Repeater {
                        model: [Number(modelData[0]).toFixed(4), Number(modelData[1]).toPrecision(6) * 1, modelData[2].toFixed(1)]
                        Label {
                            required property var modelData
                            width: 130
                            leftPadding: 12
                            text: modelData
                            font.family: "monospace"
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true
                text: qsTr("%n peak(s)", "", dialog.rows.length)
                color: Theme.mutedTextColor
            }
            Button { text: qsTr("Copy"); onClicked: Inspector.copyPeaks() }
        }
    }
}
