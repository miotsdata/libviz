import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Style"

// The selected library's inspector: filters, compound table, spectrum panel.
Item {
    id: page
    readonly property var info: Libraries.selected
    readonly property var options: Inspector.filterOptions

    function applyFilters() {
        Inspector.setFilters(searchField.text, massField.text, ppmField.text,
                             polarityBox.currentIndex > 0 ? polarityBox.currentText : "",
                             adductBox.currentIndex > 0 ? adductBox.currentText : "",
                             ceBox.currentIndex > 0 ? ceBox.currentText : "")
    }
    function clearFilters() {
        searchField.text = ""; massField.text = ""
        polarityBox.currentIndex = 0; adductBox.currentIndex = 0; ceBox.currentIndex = 0
        applyFilters()
    }
    // Show the filters Inspector keeps for this library (empty for a new one,
    // the previous ones when switching back, or when this page is reloaded).
    function showView() {
        var v = Inspector.view
        searchField.text = v.text || ""; massField.text = v.mass || ""; ppmField.text = v.ppm || "10"
        showCombos()
    }
    // The combo lists load asynchronously: re-pick the values once they are there.
    function showCombos() {
        var v = Inspector.view
        function pick(box, value) { box.currentIndex = value ? Math.max(0, box.find(value)) : 0 }
        pick(polarityBox, v.polarity); pick(adductBox, v.adduct); pick(ceBox, v.collision_energy)
    }
    Component.onCompleted: showView()
    Connections {
        target: Inspector
        function onViewChanged() { debounce.stop(); tabs.currentIndex = 0; page.showView() }
        function onFilterOptionsChanged() { Qt.callLater(page.showCombos) }
    }
    Timer { id: debounce; interval: 300; onTriggered: page.applyFilters() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // --- header ---
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 10
            Label { text: page.info.name || ""; font.pixelSize: Theme.headingPixelSize; font.bold: true; elide: Text.ElideRight; Layout.maximumWidth: 400 }
            Label {
                visible: page.info.isTemp === true
                text: qsTr("unsaved — File › Save as… to keep it")
                color: Theme.warningColor
            }
            Item { Layout.fillWidth: true }
            Label {
                text: qsTr("%1 compounds · %2 spectra")
                      .arg((page.info.nCompounds || 0).toLocaleString(Qt.locale(), "f", 0))
                      .arg((page.info.nSpectra || 0).toLocaleString(Qt.locale(), "f", 0))
                color: Theme.mutedTextColor
            }
        }

        TabBar {
            id: tabs
            objectName: "libraryTabs"
            Layout.leftMargin: 10
            TabButton { text: qsTr("Browse"); width: implicitWidth + 20 }
            TabButton { text: qsTr("Overview"); width: implicitWidth + 20 }
            onCurrentIndexChanged: if (currentIndex === 1) Inspector.loadOverview()
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

        // --- filter bar ---
        RowLayout {
            visible: tabs.currentIndex === 0
            Layout.topMargin: 8
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 8
            spacing: 6
            TextField {
                id: searchField
                objectName: "searchField"
                Layout.fillWidth: true
                Layout.minimumWidth: 160
                placeholderText: qsTr("Search name, formula or InChIKey")
                selectByMouse: true
                onTextEdited: debounce.restart()
            }
            TextField {
                id: massField
                Layout.preferredWidth: 110
                placeholderText: qsTr("Mass or m/z")
                validator: RegularExpressionValidator { regularExpression: /^\d*[.,]?\d*$/ }
                onTextEdited: debounce.restart()
                ToolTip.visible: hovered
                ToolTip.delay: 600
                ToolTip.text: qsTr("Matches the neutral exact mass or any precursor m/z")
            }
            TextField {
                id: ppmField
                Layout.preferredWidth: 50
                text: "10"
                validator: RegularExpressionValidator { regularExpression: /^\d*[.,]?\d*$/ }
                onTextEdited: debounce.restart()
            }
            Label { text: qsTr("ppm"); color: Theme.mutedTextColor }
            ComboBox {
                id: polarityBox
                Layout.preferredWidth: 120
                model: [qsTr("Any polarity")].concat(page.options.polarities || [])
                onActivated: page.applyFilters()
            }
            ComboBox {
                id: adductBox
                Layout.preferredWidth: 130
                model: [qsTr("Any adduct")].concat(page.options.adducts || [])
                onActivated: page.applyFilters()
            }
            ComboBox {
                id: ceBox
                Layout.preferredWidth: 100
                model: [qsTr("Any CE")].concat(page.options.collision_energies || [])
                onActivated: page.applyFilters()
            }
            ToolButton { text: qsTr("Clear"); onClicked: { Inspector.setIssue(""); page.clearFilters() } }
        }
        RowLayout {
            visible: tabs.currentIndex === 0 && Inspector.issue !== ""
            Layout.leftMargin: 10
            Layout.bottomMargin: 6
            Label { text: "⚠ " + qsTr("Only %1").arg(Inspector.issueLabel); color: Theme.warningColor }
            ToolButton { text: "✕"; onClicked: Inspector.setIssue("") }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

        OverviewPanel {
            visible: tabs.currentIndex === 1
            Layout.fillWidth: true
            Layout.fillHeight: true
            onShowIssue: key => { Inspector.setIssue(key); tabs.currentIndex = 0 }
        }

        SplitView {
            visible: tabs.currentIndex === 0
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            CompoundTable {
                SplitView.preferredWidth: page.width * 0.45
                SplitView.minimumWidth: 300
                onEditRequested: compoundDialog.openFor(Inspector.compound)
                onExportRequested: exportDialog.open()
                onDeleteRequested: confirmDialog.ask(qsTr("Delete compound “%1” and all its spectra?").arg(Inspector.compound.name),
                                                     function () { Inspector.deleteCompound() })
            }
            SpectrumPanel {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 320
                onEditCompoundRequested: compoundDialog.openFor(Inspector.compound)
                onExportCompoundRequested: exportDialog.open()
                onDeleteCompoundRequested: confirmDialog.ask(qsTr("Delete compound “%1” and all its spectra?").arg(Inspector.compound.name),
                                                             function () { Inspector.deleteCompound() })
                onDeleteSpectrumRequested: id => confirmDialog.ask(qsTr("Delete this spectrum?"), function () { Inspector.deleteSpectrum(id) })
                onEditMetadataRequested: (key, value) => metadataDialog.openFor(key, value)
                onDeleteMetadataRequested: key => Inspector.deleteMetadata(key)
                onSearchSimilarRequested: { Search.useSpectrum(Inspector.spectrum, Inspector.compound.name); window.page = "search" }
            }
        }
    }

    // =========================
    // EDIT DIALOGS (ADR 5)
    // =========================
    Dialog {
        id: compoundDialog
        objectName: "compoundDialog"
        title: qsTr("Edit compound")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        function openFor(c) {
            nameEdit.text = c.name || ""; formulaEdit.text = c.formula || ""
            smilesEdit.text = c.smiles || ""; pubchemEdit.text = c.pubchem_id ? String(c.pubchem_id) : ""
            inchikeyLabel.text = c.inchikey || ""
            open()
        }
        onAccepted: Inspector.updateCompound(nameEdit.text, formulaEdit.text, smilesEdit.text, pubchemEdit.text)
        GridLayout {
            columns: 2
            columnSpacing: 10
            Label { text: qsTr("InChIKey") }
            Label { id: inchikeyLabel; color: Theme.mutedTextColor; font.family: "monospace" }
            Label { text: qsTr("Name") }
            TextField { id: nameEdit; Layout.preferredWidth: 360 }
            Label { text: qsTr("Formula") }
            TextField { id: formulaEdit; Layout.fillWidth: true }
            Label { text: qsTr("SMILES") }
            TextField { id: smilesEdit; Layout.fillWidth: true }
            Label { text: qsTr("PubChem CID") }
            TextField { id: pubchemEdit; Layout.fillWidth: true; validator: RegularExpressionValidator { regularExpression: /^\d*$/ } }
        }
    }

    Dialog {
        id: metadataDialog
        title: originalKey ? qsTr("Edit metadata field") : qsTr("Add metadata field")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        property string originalKey
        function openFor(key, value) { originalKey = key; keyEdit.text = key; valueEdit.text = value; open(); keyEdit.forceActiveFocus() }
        onAccepted: {
            if (!keyEdit.text.trim()) return
            if (originalKey && originalKey !== keyEdit.text.trim()) Inspector.deleteMetadata(originalKey)
            Inspector.setMetadata(keyEdit.text, valueEdit.text)
        }
        GridLayout {
            columns: 2
            Label { text: qsTr("Key") }
            TextField { id: keyEdit; Layout.preferredWidth: 320 }
            Label { text: qsTr("Value") }
            TextField { id: valueEdit; Layout.fillWidth: true }
        }
    }

    MessageDialog {
        id: confirmDialog
        title: qsTr("Delete")
        property var action
        function ask(question, fn) { text = question; action = fn; open() }
        buttons: MessageDialog.Yes | MessageDialog.Cancel
        onButtonClicked: (button, role) => { if (button === MessageDialog.Yes && action) action() }
    }

    FileDialog {
        id: exportDialog
        title: qsTr("Export compound as MSP")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "msp"
        nameFilters: [qsTr("MSP files (*.msp)")]
        onAccepted: Inspector.exportCompoundMsp(selectedFile)
    }
}
