import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Library statistics and QC checks (Inspector.overview, ADR 6).
ScrollView {
    id: root
    signal showIssue(string key)
    readonly property var o: Inspector.overview
    readonly property bool ready: o.n_spectra !== undefined
    contentWidth: availableWidth
    clip: true

    BusyIndicator { anchors.centerIn: parent; running: !root.ready; visible: running }

    ColumnLayout {
        visible: root.ready
        width: root.availableWidth - 32
        x: 16
        spacing: 18

        // --- headline numbers ---
        RowLayout {
            Layout.topMargin: 16
            spacing: 12
            Repeater {
                model: root.ready ? [[qsTr("Compounds"), root.o.n_compounds], [qsTr("Spectra"), root.o.n_spectra],
                                     [qsTr("Adducts"), root.o.adduct.length], [qsTr("Collision energies"), root.o.collision_energy.length]] : []
                delegate: Rectangle {
                    required property var modelData
                    implicitWidth: 170
                    implicitHeight: 70
                    radius: 4
                    color: Theme.secondaryColor
                    border.color: Theme.borderColor
                    Column {
                        anchors.left: parent.left
                        anchors.leftMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        Label { text: modelData[0]; color: Theme.mutedTextColor; font.pixelSize: Theme.captionPixelSize }
                        Label { text: modelData[1].toLocaleString(Qt.locale(), "f", 0); font.pixelSize: 24 }
                    }
                }
            }
        }

        // --- QC ---
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4
            Label { text: qsTr("Quality checks"); font.bold: true }
            Repeater {
                model: root.ready ? root.o.issues : []
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Label {
                        // icon + text, never color alone
                        text: modelData.count > 0 ? "⚠" : "✓"
                        color: modelData.count > 0 ? Theme.warningColor : Theme.successColor
                        Layout.preferredWidth: 18
                    }
                    Label { text: modelData.label; Layout.fillWidth: true }
                    Label {
                        text: modelData.count.toLocaleString(Qt.locale(), "f", 0)
                        color: Theme.mutedTextColor
                        Layout.preferredWidth: 80
                        horizontalAlignment: Text.AlignRight
                    }
                    Button {
                        text: qsTr("Show")
                        enabled: modelData.count > 0
                        flat: true
                        onClicked: root.showIssue(modelData.key)
                    }
                }
            }
        }

        // --- distributions ---
        GridLayout {
            Layout.fillWidth: true
            columns: root.availableWidth > 900 ? 2 : 1
            columnSpacing: 32
            rowSpacing: 18
            BarList { Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; title: qsTr("Spectra by polarity"); rows: root.ready ? root.o.polarity : [] }
            BarList { Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; title: qsTr("Spectra by adduct"); rows: root.ready ? root.o.adduct : [] }
            BarList {
                Layout.alignment: Qt.AlignTop
                Layout.fillWidth: true
                title: qsTr("Spectra by collision energy")
                rows: root.ready ? root.o.collision_energy.map(function (r) { return [r[0] + " eV", r[1]] }) : []
            }
            BarList { Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; title: qsTr("Peaks per spectrum"); rows: root.ready ? root.o.peaks : [] }
        }

        // --- precursor m/z histogram ---
        ColumnLayout {
            Layout.fillWidth: true
            Layout.bottomMargin: 16
            spacing: 4
            Label { text: qsTr("Precursor m/z (50 Da bins)"); font.bold: true }
            Item {
                id: hist
                Layout.fillWidth: true
                implicitHeight: 160
                readonly property var bins: root.ready ? root.o.precursor_mz : []
                readonly property real maxCount: bins.length ? Math.max.apply(null, bins.map(function (b) { return b[1] })) : 1
                readonly property real barWidth: bins.length ? (width - 2 * (bins.length - 1)) / bins.length : 0
                Rectangle { anchors.bottom: parent.bottom; anchors.bottomMargin: 18; width: parent.width; height: 1; color: Theme.borderColor }
                Repeater {
                    model: hist.bins
                    delegate: Item {
                        required property var modelData
                        required property int index
                        x: index * (hist.barWidth + 2)
                        width: hist.barWidth
                        height: hist.height
                        Rectangle {
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 18
                            width: parent.width
                            height: Math.max(1, (hist.height - 22) * modelData[1] / hist.maxCount)
                            radius: Math.min(3, width / 2)
                            color: hb.hovered ? Qt.lighter(Theme.plotAccentColor, 1.2) : Theme.plotAccentColor
                        }
                        Label {
                            visible: index % Math.max(1, Math.ceil(hist.bins.length / 12)) === 0
                            anchors.bottom: parent.bottom
                            text: modelData[0]
                            font.pixelSize: Theme.captionPixelSize
                            color: Theme.mutedTextColor
                        }
                        HoverHandler { id: hb }
                        ToolTip.visible: hb.hovered
                        ToolTip.text: "m/z %1–%2: %3".arg(modelData[0]).arg(modelData[0] + 50).arg(modelData[1])
                    }
                }
            }
        }
    }
}
