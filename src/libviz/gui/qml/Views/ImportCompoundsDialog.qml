import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "../Style"

// Library › Import compounds… (ADR 10): a CSV/TSV or Excel sheet of compounds,
// no spectra, into the selected library. Rows with warnings are imported;
// rows with errors are not.
Dialog {
    id: root
    objectName: "importCompoundsDialog"
    title: qsTr("Import compounds into “%1”").arg(Libraries.selected.name || "")
    anchors.centerIn: parent
    width: Math.min(parent.width - 40, 1000)
    height: Math.min(parent.height - 40, 680)
    modal: true

    property string libraryKey
    readonly property var summary: CompoundImport.summary

    function openForSelected() {
        libraryKey = Libraries.selectedKey
        fileDialog.open()
    }

    footer: DialogButtonBox {
        Button {
            text: qsTr("Import %1 compounds").arg(root.summary.importable || 0)
            enabled: !CompoundImport.busy && (root.summary.importable || 0) > 0
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
        }
        Button { text: qsTr("Cancel"); DialogButtonBox.buttonRole: DialogButtonBox.RejectRole }
    }
    onAccepted: CompoundImport.importInto(libraryKey)

    FileDialog {
        id: fileDialog
        title: qsTr("Compound table")
        nameFilters: [qsTr("Tables (*.xlsx *.xlsm *.csv *.tsv *.txt)"), qsTr("All files (*)")]
        onAccepted: { CompoundImport.load(selectedFile); root.open() }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            Button { text: qsTr("Choose file…"); onClicked: fileDialog.open() }
            Label { text: CompoundImport.fileName; elide: Text.ElideMiddle; Layout.fillWidth: true; Layout.preferredWidth: 100 }
            Label { text: qsTr("Sheet"); visible: CompoundImport.sheets.length > 0 }
            ComboBox {
                visible: CompoundImport.sheets.length > 0
                Layout.preferredWidth: 220
                model: CompoundImport.sheets
                currentIndex: CompoundImport.sheets.indexOf(CompoundImport.sheet)
                onActivated: index => CompoundImport.setSheet(CompoundImport.sheets[index])
            }
            BusyIndicator { running: CompoundImport.busy; visible: running; Layout.preferredHeight: 28 }
        }

        Label {
            visible: CompoundImport.error !== ""
            text: CompoundImport.error
            color: Theme.errorColor
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        // field -> column
        GridLayout {
            visible: CompoundImport.columns.length > 1
            columns: 3
            columnSpacing: 10
            rowSpacing: 4
            Repeater {
                model: CompoundImport.fields
                delegate: RowLayout {
                    required property var modelData
                    Label { text: modelData.label; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                    ComboBox {
                        Layout.preferredWidth: 170
                        model: CompoundImport.columns
                        currentIndex: Math.max(0, CompoundImport.columns.indexOf(modelData.column))
                        displayText: currentText || qsTr("(not used)")
                        onActivated: index => CompoundImport.setMapping(modelData.key, CompoundImport.columns[index])
                    }
                }
            }
        }
        Label {
            visible: CompoundImport.columns.length > 1
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            color: Theme.mutedTextColor
            font.pixelSize: Theme.captionPixelSize
            text: qsTr("Name and a formula or mass are required. The formula wins over the mass (a difference over 0.01 Da is a warning); D is deuterium. "
                       + "A missing or invalid InChIKey is a warning: the cell's value (or NOKEY:name) becomes the key. "
                       + "Compounds already in the library are kept; their missing SMILES/PubChem are filled in.")
        }

        Label {
            visible: root.summary.total > 0
            text: qsTr("%1 rows: %2 ok · %3 with warnings (imported) · %4 with errors (skipped)")
                  .arg(root.summary.total).arg(root.summary.ok).arg(root.summary.warning).arg(root.summary.error)
            font.bold: true
        }

        // preview
        Frame {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 0
            ListView {
                id: preview
                anchors.fill: parent
                clip: true
                model: CompoundImport.rows
                ScrollBar.vertical: ScrollBar {}
                header: RowLayout {
                    width: preview.width
                    spacing: 6
                    Repeater {
                        model: [[qsTr("Row"), 40], ["", 18], [qsTr("Name"), 200], [qsTr("Formula"), 130],
                                [qsTr("Mass"), 80], [qsTr("Key"), 200], [qsTr("Message"), -1]]
                        Label {
                            required property var modelData
                            text: modelData[0]
                            font.bold: true
                            Layout.preferredWidth: modelData[1] > 0 ? modelData[1] : -1
                            Layout.fillWidth: modelData[1] < 0
                        }
                    }
                }
                delegate: RowLayout {
                    required property var modelData
                    width: preview.width
                    spacing: 6
                    readonly property color statusColor: modelData.status === "error" ? Theme.errorColor
                                                       : modelData.status === "warning" ? Theme.warningColor : Theme.successColor
                    Label { text: modelData.line; Layout.preferredWidth: 40; color: Theme.mutedTextColor }
                    // icon + text, never color alone
                    Label { text: modelData.status === "ok" ? "✓" : modelData.status === "warning" ? "⚠" : "✕"; color: statusColor; Layout.preferredWidth: 18 }
                    Label { text: modelData.name; Layout.preferredWidth: 200; elide: Text.ElideRight }
                    Label { text: modelData.formula; Layout.preferredWidth: 130; elide: Text.ElideRight }
                    Label { text: modelData.mass; Layout.preferredWidth: 80 }
                    Label { text: modelData.inchikey; Layout.preferredWidth: 200; elide: Text.ElideRight; font.family: "monospace" }
                    Label { text: modelData.message; Layout.fillWidth: true; elide: Text.ElideRight; color: statusColor
                            ToolTip.visible: messageArea.containsMouse && modelData.message !== ""; ToolTip.text: modelData.message
                            MouseArea { id: messageArea; anchors.fill: parent; hoverEnabled: true } }
                }
            }
        }
    }
}
