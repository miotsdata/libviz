import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Style"

// Spectral search of one query spectrum against every open library (ADR 6).
Item {
    id: page
    signal closeRequested()
    signal openHit(string libraryPath, int compoundId)
    readonly property var q: Search.query

    function run() {
        Search.search(peaksArea.text, precursorField.text, polarityBox.currentIndex > 0 ? polarityBox.currentText : "",
                      ppmField.text, analogBox.checked ? windowField.text : "0", tolField.text, minField.text)
    }
    Connections {
        target: Search
        function onQueryChanged() {
            peaksArea.text = page.q.peaks
            precursorField.text = page.q.precursor
            polarityBox.currentIndex = Math.max(0, polarityBox.model.indexOf(page.q.polarity))
        }
    }
    Component.onCompleted: Search.queryChanged()

    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 10
            ToolButton { text: "‹ " + qsTr("Back"); onClicked: page.closeRequested() }
            Label { text: qsTr("Spectral search"); font.pixelSize: Theme.headingPixelSize; font.bold: true }
            Label {
                text: Libraries.libraries.length === 1 ? qsTr("in 1 open library")
                      : qsTr("in %1 open libraries").arg(Libraries.libraries.length)
                color: Theme.mutedTextColor
            }
            Item { Layout.fillWidth: true }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            // --- query ---
            ColumnLayout {
                SplitView.preferredWidth: 340
                SplitView.minimumWidth: 280
                spacing: 6
                Label { Layout.margins: 10; Layout.bottomMargin: 0; text: qsTr("Query"); font.bold: true }
                Label {
                    visible: page.q.title !== ""
                    Layout.leftMargin: 10
                    Layout.fillWidth: true
                    text: page.q.title
                    elide: Text.ElideRight
                    color: Theme.mutedTextColor
                }
                RowLayout {
                    Layout.leftMargin: 10
                    Button { text: qsTr("Load mzML scan…"); onClicked: scanFileDialog.open() }
                }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    TextArea {
                        id: peaksArea
                        objectName: "peaksArea"
                        placeholderText: qsTr("Paste peaks: one 'm/z intensity' per line")
                        font.family: "monospace"
                        selectByMouse: true
                    }
                }
                GridLayout {
                    Layout.margins: 10
                    columns: 2
                    columnSpacing: 8
                    Label { text: qsTr("Precursor m/z") }
                    TextField { id: precursorField; Layout.fillWidth: true }
                    Label { text: qsTr("Polarity") }
                    ComboBox { id: polarityBox; Layout.fillWidth: true; model: [qsTr("Any"), "POSITIVE", "NEGATIVE"] }
                    Label { text: qsTr("Precursor tolerance (ppm)") }
                    TextField { id: ppmField; text: "10"; Layout.fillWidth: true; enabled: !analogBox.checked }
                    CheckBox { id: analogBox; text: qsTr("Analog search ± (Da)"); ToolTip.visible: hovered; ToolTip.text: qsTr("Modified cosine over precursors within this window") }
                    TextField { id: windowField; text: "100"; Layout.fillWidth: true; enabled: analogBox.checked }
                    Label { text: qsTr("Fragment tolerance (Da)") }
                    TextField { id: tolField; text: "0.01"; Layout.fillWidth: true }
                    Label { text: qsTr("Min. matched peaks") }
                    TextField { id: minField; text: "2"; Layout.fillWidth: true }
                }
                Button {
                    Layout.fillWidth: true
                    Layout.margins: 10
                    text: Search.running ? qsTr("Searching…") : qsTr("Search")
                    highlighted: true
                    enabled: !Search.running && Libraries.libraries.length > 0
                    onClicked: page.run()
                }
            }

            // --- results ---
            SplitView {
                SplitView.fillWidth: true
                orientation: Qt.Vertical
                ListView {
                    id: hits
                    objectName: "hitList"
                    SplitView.preferredHeight: 260
                    clip: true
                    model: Search.results
                    ScrollBar.vertical: ScrollBar {}
                    header: Rectangle {
                        width: ListView.view.width
                        height: 22
                        color: Theme.controlColor
                        Row {
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            Repeater {
                                model: [[qsTr("Score"), 60], [qsTr("Matched"), 65], [qsTr("Compound"), 220], [qsTr("Adduct"), 90],
                                        [qsTr("CE"), 45], [qsTr("Precursor"), 90], [qsTr("Δ m/z"), 70], [qsTr("Library"), 140]]
                                Label { width: modelData[1]; text: modelData[0]; font.bold: true; font.pixelSize: Theme.captionPixelSize }
                            }
                        }
                    }
                    delegate: ItemDelegate {
                        id: hrow
                        required property var modelData
                        width: ListView.view.width
                        height: 24
                        highlighted: modelData.index === Search.selectedHit
                        onClicked: Search.selectHit(modelData.index)
                        onDoubleClicked: page.openHit(modelData.libraryPath, modelData.compound_id)
                        ToolTip.visible: hovered
                        ToolTip.delay: 800
                        ToolTip.text: qsTr("Double-click to open in the library")
                        contentItem: Row {
                            Repeater {
                                model: [[hrow.modelData.score.toFixed(3), 60], [hrow.modelData.n_matched, 65], [hrow.modelData.name, 220],
                                        [hrow.modelData.adduct, 90], [hrow.modelData.collision_energy, 45], [hrow.modelData.precursor_mz.toFixed(4), 90],
                                        [(hrow.modelData.delta_mz >= 0 ? "+" : "") + hrow.modelData.delta_mz.toFixed(4), 70], [hrow.modelData.library, 140]]
                                Label { width: modelData[1]; text: modelData[0]; elide: Text.ElideRight; color: hrow.highlighted ? Theme.highlightedTextColor : Theme.textColor }
                            }
                        }
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: hits.count === 0 && !Search.running
                        text: qsTr("No hits yet")
                        color: Theme.placeholderTextColor
                    }
                }
                ColumnLayout {
                    spacing: 0
                    Label {
                        Layout.margins: 6
                        text: Search.mirror.title ? Search.mirror.title + qsTr("  ·  top: query, bottom: library") : ""
                        color: Theme.mutedTextColor
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "transparent"
                        StickPlot {
                            anchors.fill: parent
                            anchors.margins: 4
                            emptyText: qsTr("Select a hit")
                            groups: Search.mirror.query ? [{ key: "query", name: qsTr("Query"), peaks: Search.mirror.query },
                                                           { key: "hit", name: qsTr("Library"), peaks: Search.mirror.hit }] : []
                            colors: ({ query: Theme.plotAccentColor, hit: Theme.plotSecondColor })
                            mirrored: true
                            yMin: -1100
                            yMax: 1100
                            yTickInterval: 500
                            yTitle: qsTr("Relative intensity")
                        }
                    }
                }
            }
        }
    }

    FileDialog {
        id: scanFileDialog
        title: qsTr("mzML file")
        nameFilters: [qsTr("mzML files (*.mzML *.mzml)"), qsTr("All files (*)")]
        onAccepted: { scanDialog.file = selectedFile; scanDialog.open() }
    }
    Dialog {
        id: scanDialog
        property string file
        title: qsTr("Scan number")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        TextField { id: scanField; implicitWidth: 200; placeholderText: qsTr("e.g. 10428"); onAccepted: scanDialog.accept() }
        onAccepted: Search.loadScan(file, scanField.text)
    }
}
