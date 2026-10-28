import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Style"

// Build library spectra from mzML: setup (targets, files, parameters) →
// review (one row per compound/adduct/CE, pick the scan) → add to a library.
Item {
    id: page
    signal closeRequested()
    signal newLibraryRequested()  // Main.qml creates it, then calls commitTo()

    readonly property bool review: Builder.stage === "review"
    readonly property var p: Builder.params

    function commitTo(key) { commitDialog.openFor(key) }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // --- header ---
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 10
            ToolButton { text: "‹ " + qsTr("Back"); onClicked: page.closeRequested() }
            Label { text: qsTr("Build library from mzML"); font.pixelSize: Theme.headingPixelSize; font.bold: true }
            Label {
                visible: page.review
                color: Theme.mutedTextColor
                text: page.review ? qsTr("%1 MS2 scans · %2 of %3 targets with spectra · %4 rows chosen")
                                    .arg(Builder.summary.nMs2).arg(Builder.summary.nTargetsFound)
                                    .arg(Builder.summary.nTargets).arg(Builder.summary.nChosen) : ""
            }
            Item { Layout.fillWidth: true }
            Button { visible: page.review; text: qsTr("‹ Setup"); enabled: !Builder.running; onClicked: Builder.backToSetup() }
            Button {
                visible: page.review
                text: qsTr("Add %1 spectra to library…").arg(Builder.summary.nChosen || 0)
                highlighted: true
                enabled: !Builder.running && Builder.summary.nChosen > 0
                onClicked: commitDialog.openFor(Libraries.selectedKey)
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

        Loader {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: page.review ? reviewView : setupView
        }

        // --- run status ---
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 8
            visible: Builder.running
            Label { text: Builder.statusText + "…"; color: Theme.mutedTextColor }
            ProgressBar {
                Layout.fillWidth: true
                indeterminate: Builder.progress < 0
                value: Math.max(0, Builder.progress)
            }
        }
    }

    // =====================================================================
    // SETUP
    // =====================================================================
    Component {
        id: setupView
        SplitView {
            orientation: Qt.Horizontal

            // targets + files
            ColumnLayout {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 360
                spacing: 6

                Label { Layout.leftMargin: 10; Layout.topMargin: 10; text: qsTr("1. Targets"); font.bold: true }
                RowLayout {
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    Button { text: qsTr("Choose target list…"); onClicked: targetsDialog.open() }
                    Label {
                        Layout.fillWidth: true
                        elide: Text.ElideMiddle
                        color: Theme.mutedTextColor
                        text: Builder.targetsPath ? Builder.targetsPath
                              : qsTr("CSV/TSV with name, formula, inchikey; optional smiles, pubchem_id, adducts, rt or rt_min/rt_max")
                    }
                }
                Label {
                    visible: Builder.targetCount > 0
                    Layout.leftMargin: 10
                    text: qsTr("%1 targets").arg(Builder.targetCount)
                    color: Theme.successColor
                }
                ScrollView {
                    visible: Builder.targetsError !== ""
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    TextArea { readOnly: true; text: Builder.targetsError; color: Theme.errorColor; wrapMode: Text.Wrap }
                }
                ListView {
                    visible: Builder.targetCount > 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    clip: true
                    model: Builder.targetsPreview
                    ScrollBar.vertical: ScrollBar {}
                    delegate: RowLayout {
                        required property var modelData
                        width: ListView.view.width
                        Label { text: modelData.name; Layout.preferredWidth: 220; elide: Text.ElideRight }
                        Label { text: modelData.formula; Layout.preferredWidth: 120; color: Theme.mutedTextColor }
                        Label { text: modelData.adducts; Layout.preferredWidth: 140; color: Theme.mutedTextColor; elide: Text.ElideRight }
                        Label { text: modelData.rt ? "RT " + modelData.rt : ""; color: Theme.mutedTextColor }
                    }
                }

                Label { Layout.leftMargin: 10; Layout.topMargin: 10; text: qsTr("2. mzML files (centroided MS2; DDA, DIA or imaging)"); font.bold: true }
                RowLayout {
                    Layout.leftMargin: 10
                    Button { text: qsTr("Add files…"); onClicked: mzmlDialog.open() }
                    Button { text: qsTr("Clear"); enabled: Builder.files.length > 0; onClicked: Builder.clearFiles() }
                }
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 10
                    Layout.rightMargin: 10
                    clip: true
                    model: Builder.files
                    ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        required property var modelData
                        required property int index
                        width: ListView.view.width
                        text: modelData.name
                        ToolTip.visible: hovered
                        ToolTip.delay: 600
                        ToolTip.text: modelData.path
                        ToolButton {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: "✕"
                            onClicked: Builder.removeFile(parent.index)
                        }
                    }
                    Label {
                        anchors.centerIn: parent
                        visible: Builder.files.length === 0
                        text: qsTr("No files")
                        color: Theme.placeholderTextColor
                    }
                }
            }

            // parameters
            ScrollView {
                SplitView.preferredWidth: 380
                SplitView.minimumWidth: 300
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width - 20
                    x: 10
                    spacing: 6
                    Label { Layout.topMargin: 10; text: qsTr("3. Parameters"); font.bold: true }

                    GridLayout {
                        columns: 2
                        columnSpacing: 10
                        rowSpacing: 6
                        Layout.fillWidth: true

                        Label { text: qsTr("Precursor tolerance (ppm)") }
                        TextField { text: page.p.ppm; Layout.fillWidth: true; onEditingFinished: Builder.setParam("ppm", text) }

                        Label { text: qsTr("Default positive adducts") }
                        TextField { text: page.p.positiveAdducts; Layout.fillWidth: true; onEditingFinished: Builder.setParam("positiveAdducts", text) }

                        Label { text: qsTr("Default negative adducts") }
                        TextField { text: page.p.negativeAdducts; Layout.fillWidth: true; onEditingFinished: Builder.setParam("negativeAdducts", text) }

                        Label { text: qsTr("DIA if isolation ≥ (m/z)") }
                        TextField { text: page.p.diaMinWidth; Layout.fillWidth: true; onEditingFinished: Builder.setParam("diaMinWidth", text) }

                        Label { text: qsTr("Min. peak intensity (% base)") }
                        TextField { text: page.p.minRelativeIntensity; Layout.fillWidth: true; onEditingFinished: Builder.setParam("minRelativeIntensity", text) }

                        Label { text: qsTr("Min. peaks per spectrum") }
                        SpinBox { from: 1; to: 100; value: page.p.minPeaks; editable: true; onValueModified: Builder.setParam("minPeaks", value) }

                        Label { text: qsTr("Rank scans by") }
                        ComboBox {
                            Layout.fillWidth: true
                            model: Builder.rankOptions
                            currentIndex: Builder.rankOptions.indexOf(page.p.rankBy)
                            onActivated: Builder.setParam("rankBy", currentText)
                        }
                    }
                    CheckBox { text: qsTr("Remove precursor and peaks above it"); checked: page.p.removePrecursor; onToggled: Builder.setParam("removePrecursor", checked) }
                    CheckBox { text: qsTr("Normalize base peak to 1000"); checked: page.p.normalize; onToggled: Builder.setParam("normalize", checked) }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: Theme.mutedTextColor
                        font.pixelSize: Theme.captionPixelSize
                        text: qsTr("Adducts per target come from its 'adducts' column, otherwise the defaults above. RT is only used when the target list has it.")
                    }
                    Button {
                        Layout.topMargin: 10
                        Layout.fillWidth: true
                        text: qsTr("Find spectra")
                        highlighted: true
                        enabled: Builder.canRun && Builder.files.length > 0 && !Builder.running
                        onClicked: Builder.run()
                    }
                }
            }
        }
    }

    // =====================================================================
    // REVIEW
    // =====================================================================
    Component {
        id: reviewView
        SplitView {
            id: reviewSplit
            orientation: Qt.Horizontal
            property string filter: "all"

            ColumnLayout {
                SplitView.preferredWidth: reviewSplit.width * 0.55
                SplitView.minimumWidth: 420
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: 6
                    Label { text: qsTr("Show") }
                    ComboBox {
                        model: [qsTr("All rows"), qsTr("Chosen"), qsTr("Missing"), qsTr("Multiplexed"), qsTr("Not added")]
                        onActivated: reviewSplit.filter = ["all", "chosen", "missing", "multiplexed", "rejected"][currentIndex]
                    }
                    Item { Layout.fillWidth: true }
                    ToolButton { text: qsTr("Best for all"); onClicked: Builder.chooseBestForAll() }
                    ToolButton { text: qsTr("Reject multiplexed"); enabled: Builder.summary.nMultiplexed > 0; onClicked: Builder.rejectMultiplexed() }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 22
                    color: Theme.controlColor
                    Row {
                        x: 8
                        anchors.verticalCenter: parent.verticalCenter
                        Repeater {
                            model: [[qsTr("Target"), 0.30], [qsTr("Adduct"), 0.13], [qsTr("CE"), 0.07], [qsTr("Scans"), 0.08],
                                    [qsTr("ppm"), 0.08], [qsTr("RT"), 0.08], [qsTr("Status"), 0.12], [qsTr("File"), 0.14]]
                            Label { width: modelData[1] * (reviewList.width - 16); text: modelData[0]; font.bold: true; font.pixelSize: Theme.captionPixelSize }
                        }
                    }
                }

                ListView {
                    id: reviewList
                    objectName: "reviewList"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: Builder.rows
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                    focus: true
                    Keys.onUpPressed: { for (var i = Builder.selectedGroup - 1; i >= 0; i--) if (itemAtIndex(i) && itemAtIndex(i).visible) { Builder.selectGroup(i); positionViewAtIndex(i, ListView.Contain); break } }
                    Keys.onDownPressed: { for (var i = Builder.selectedGroup + 1; i < count; i++) if (itemAtIndex(i) && itemAtIndex(i).visible) { Builder.selectGroup(i); positionViewAtIndex(i, ListView.Contain); break } }

                    delegate: Rectangle {
                        id: rrow
                        required property int index
                        required property string target
                        required property string adduct
                        required property string ce
                        required property int n
                        required property string ppm
                        required property string rt
                        required property string status
                        required property string file
                        readonly property bool shown: reviewSplit.filter === "all"
                            || (reviewSplit.filter === "chosen" && (status === "ok" || status === "multiplexed"))
                            || reviewSplit.filter === status
                        readonly property bool selected: index === Builder.selectedGroup
                        visible: shown
                        width: ListView.view.width
                        height: shown ? 24 : 0
                        color: selected ? Theme.primaryColor : index % 2 ? Theme.fieldColor : Theme.secondaryColor
                        readonly property color fg: selected ? Theme.highlightedTextColor : Theme.textColor
                        readonly property color statusColor: selected ? Theme.highlightedTextColor
                            : status === "ok" ? Theme.successColor : status === "multiplexed" ? Theme.warningColor
                            : status === "missing" ? Theme.errorColor : Theme.mutedTextColor
                        Row {
                            x: 8
                            anchors.verticalCenter: parent.verticalCenter
                            visible: rrow.shown
                            Repeater {
                                model: [[rrow.target, 0.30], [rrow.adduct, 0.13], [rrow.ce || "—", 0.07], [rrow.n, 0.08],
                                        [rrow.ppm, 0.08], [rrow.rt, 0.08], [rrow.status === "rejected" ? qsTr("not added") : rrow.status, 0.12], [rrow.file, 0.14]]
                                Label {
                                    width: modelData[1] * (reviewList.width - 16)
                                    text: modelData[0]
                                    elide: Text.ElideRight
                                    color: index === 6 ? rrow.statusColor : rrow.fg
                                }
                            }
                        }
                        TapHandler { onTapped: { reviewList.forceActiveFocus(); Builder.selectGroup(rrow.index) } }
                    }
                }
            }

            // candidates + preview
            SplitView {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 360
                orientation: Qt.Vertical

                ColumnLayout {
                    SplitView.preferredHeight: 210
                    SplitView.minimumHeight: 120
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: 6
                        Label { text: qsTr("Candidate scans"); font.bold: true }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: qsTr("Use this scan")
                            enabled: Builder.previewIndex >= 0 && !Builder.preview.isChosen
                            onClicked: Builder.choose(Builder.selectedGroup, Builder.previewIndex)
                        }
                        Button {
                            text: qsTr("Don't add")
                            enabled: Builder.selectedGroup >= 0 && Builder.candidates.some(function (c) { return c.chosen })
                            onClicked: Builder.choose(Builder.selectedGroup, -1)
                        }
                    }
                    ListView {
                        id: candidateList
                        objectName: "candidateList"
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: Builder.candidates
                        ScrollBar.vertical: ScrollBar {}
                        header: Rectangle {
                            width: ListView.view.width
                            height: 22
                            color: Theme.controlColor
                            Row {
                                x: 8
                                anchors.verticalCenter: parent.verticalCenter
                                Repeater {
                                    model: [["", 22], [qsTr("File"), 130], [qsTr("Scan"), 90], [qsTr("RT"), 55], [qsTr("ppm"), 55], [qsTr("Prec. int."), 75], [qsTr("Peaks"), 45]]
                                    Label { width: modelData[1]; text: modelData[0]; font.bold: true; font.pixelSize: Theme.captionPixelSize }
                                }
                            }
                        }
                        delegate: ItemDelegate {
                            id: crow
                            required property var modelData
                            width: ListView.view.width
                            height: 24
                            highlighted: modelData.index === Builder.previewIndex
                            onClicked: Builder.previewCandidate(modelData.index)
                            onDoubleClicked: Builder.choose(Builder.selectedGroup, modelData.index)
                            contentItem: Row {
                                Repeater {
                                    model: [[crow.modelData.chosen ? "✓" : "", 22], [crow.modelData.file, 130], [crow.modelData.scanId, 90],
                                            [crow.modelData.rt, 55], [crow.modelData.ppm, 55], [crow.modelData.intensity, 75], [crow.modelData.peaks, 45]]
                                    Label {
                                        width: modelData[1]
                                        text: modelData[0]
                                        elide: Text.ElideMiddle
                                        color: crow.highlighted ? Theme.highlightedTextColor
                                             : crow.modelData.multiplexed && index === 4 ? Theme.warningColor : Theme.textColor
                                    }
                                }
                            }
                        }
                        Label {
                            anchors.centerIn: parent
                            visible: candidateList.count === 0
                            text: Builder.selectedGroup >= 0 ? qsTr("No MS2 scan matched this target ion") : qsTr("Select a row")
                            color: Theme.placeholderTextColor
                        }
                    }
                }

                ColumnLayout {
                    SplitView.fillHeight: true
                    spacing: 0
                    Label {
                        Layout.margins: 6
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                        color: Theme.mutedTextColor
                        text: Builder.preview.title ? Builder.preview.title
                              + (Builder.preview.chosenPeaks.length ? qsTr("  ·  top: this scan, bottom: chosen scan") : "") : ""
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        color: "transparent"
                        StickPlot {
                            anchors.fill: parent
                            anchors.margins: 4
                            readonly property bool compare: !!Builder.preview.chosenPeaks && Builder.preview.chosenPeaks.length > 0
                            emptyText: qsTr("No spectrum")
                            groups: Builder.preview.peaks ? [{ key: "preview", name: qsTr("This scan"), peaks: Builder.preview.peaks },
                                                             { key: "chosen", name: compare ? qsTr("Chosen") : "", peaks: Builder.preview.chosenPeaks }] : []
                            colors: ({ preview: Theme.plotAccentColor, chosen: Theme.plotSecondColor })
                            mirrored: compare
                            yMin: compare ? -1100 : NaN
                            yMax: compare ? 1100 : NaN
                            yTickInterval: compare ? 500 : 0
                            yTitle: qsTr("Relative intensity")
                        }
                    }
                }
            }
        }
    }

    // =====================================================================
    // DIALOGS
    // =====================================================================
    FileDialog {
        id: targetsDialog
        title: qsTr("Target list")
        nameFilters: [qsTr("Tables (*.csv *.tsv *.txt)"), qsTr("All files (*)")]
        onAccepted: Builder.loadTargets(selectedFile)
    }
    FileDialog {
        id: mzmlDialog
        title: qsTr("mzML files")
        fileMode: FileDialog.OpenFiles
        nameFilters: [qsTr("mzML files (*.mzML *.mzml)"), qsTr("All files (*)")]
        onAccepted: Builder.addFiles(selectedFiles)
    }

    Dialog {
        id: commitDialog
        title: qsTr("Add spectra to library")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        property var choices: Libraries.libraries
        function openFor(key) {
            var i = choices.findIndex(function (l) { return l.key === key })
            libraryBox.currentIndex = i >= 0 ? i : (choices.length ? 0 : -1)
            if (libraryBox.currentIndex >= 0) Builder.countConflicts(choices[libraryBox.currentIndex].key)
            open()
        }
        onAccepted: {
            if (libraryBox.currentIndex >= 0)
                Builder.commit(choices[libraryBox.currentIndex].key, replaceBox.checked)
        }
        ColumnLayout {
            spacing: 8
            Label { text: qsTr("%1 spectra will be added to:").arg(Builder.summary.nChosen || 0) }
            RowLayout {
                ComboBox {
                    id: libraryBox
                    Layout.preferredWidth: 280
                    model: commitDialog.choices.map(function (l) { return l.name + (l.isTemp ? qsTr(" (unsaved)") : "") })
                    onActivated: Builder.countConflicts(commitDialog.choices[currentIndex].key)
                }
                Button { text: qsTr("New library…"); onClicked: { commitDialog.close(); page.newLibraryRequested() } }
            }
            Label {
                visible: Builder.conflictCount > 0
                text: qsTr("%1 of them already have a spectrum for the same compound, adduct, polarity and CE.").arg(Builder.conflictCount)
                color: Theme.warningColor
                wrapMode: Text.WordWrap
                Layout.maximumWidth: 420
            }
            CheckBox { id: replaceBox; visible: Builder.conflictCount > 0; text: qsTr("Replace the existing spectra (otherwise keep them)") }
        }
    }
}
