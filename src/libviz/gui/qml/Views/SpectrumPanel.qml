import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Selected compound: its spectra, the selected spectrum's plot, and details.
SplitView {
    id: root
    orientation: Qt.Vertical
    readonly property var compound: Inspector.compound
    readonly property var spectrum: Inspector.spectrum
    readonly property bool hasCompound: compound.id !== undefined

    function fmt(v, digits) { return v === undefined || v === null ? "—" : Number(v).toFixed(digits) }

    // --- compound header + spectra list ---
    ColumnLayout {
        SplitView.preferredHeight: 190
        SplitView.minimumHeight: 110
        spacing: 4

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 8
            Layout.topMargin: 6
            text: root.hasCompound ? root.compound.name : qsTr("Select a compound")
            font.pixelSize: Theme.headingPixelSize
            font.bold: root.hasCompound
            color: root.hasCompound ? Theme.textColor : Theme.placeholderTextColor
            elide: Text.ElideRight
        }
        Label {
            visible: root.hasCompound
            Layout.leftMargin: 8
            text: root.hasCompound ? root.compound.formula + "  ·  " + root.fmt(root.compound.exact_mass, 4) + " Da" : ""
            color: Theme.mutedTextColor
        }

        ListView {
            id: spectraList
            objectName: "spectraList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: Inspector.spectra
            ScrollBar.vertical: ScrollBar {}
            header: Rectangle {
                width: ListView.view.width
                height: 22
                color: Theme.controlColor
                Row {
                    x: 8
                    anchors.verticalCenter: parent.verticalCenter
                    Repeater {
                        model: [[qsTr("Adduct"), 110], [qsTr("Polarity"), 90], [qsTr("CE"), 60], [qsTr("Precursor m/z"), 120], [qsTr("Peaks"), 60], [qsTr("Added"), 160]]
                        Label { width: modelData[1]; text: modelData[0]; font.bold: true; font.pixelSize: Theme.captionPixelSize }
                    }
                }
            }
            delegate: ItemDelegate {
                id: srow
                required property var modelData
                width: ListView.view.width
                height: 24
                highlighted: modelData.id === root.spectrum.id
                onClicked: Inspector.selectSpectrum(modelData.id)
                contentItem: Row {
                    Repeater {
                        model: [[srow.modelData.adduct, 110], [srow.modelData.polarity, 90],
                                [srow.modelData.collision_energy, 60], [root.fmt(srow.modelData.precursor_mz, 4), 120],
                                [srow.modelData.n_peaks, 60], [srow.modelData.added_on.replace("T", " ").slice(0, 16), 160]]
                        Label {
                            width: modelData[1]
                            text: modelData[0]
                            elide: Text.ElideRight
                            color: srow.highlighted ? Theme.highlightedTextColor : Theme.textColor
                        }
                    }
                }
            }
        }
    }

    // --- spectrum plot ---
    ColumnLayout {
        SplitView.fillHeight: true
        SplitView.minimumHeight: 160
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 8
            Layout.rightMargin: 4
            visible: root.spectrum.id !== undefined
            Label {
                Layout.fillWidth: true
                elide: Text.ElideRight
                color: Theme.mutedTextColor
                text: root.spectrum.id !== undefined
                      ? root.spectrum.adduct + "  ·  " + root.spectrum.polarity + "  ·  CE " + root.spectrum.collision_energy
                        + "  ·  precursor m/z " + root.fmt(root.spectrum.precursor_mz, 4)
                        + "  ·  " + (root.spectrum.mz ? root.spectrum.mz.length : 0) + qsTr(" peaks") : ""
            }
            ToolButton { text: qsTr("Copy peaks"); onClicked: Inspector.copyPeaks() }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.plotBackgroundColor
            StickPlot {
                id: plot
                objectName: "spectrumPlot"
                anchors.fill: parent
                anchors.margins: 4
                emptyText: root.hasCompound ? qsTr("No peaks") : qsTr("Select a compound to see its spectra")
                groups: root.spectrum.mz ? [{
                    key: "peaks", name: "",
                    peaks: root.spectrum.mz.map(function (m, i) { return [m, root.spectrum.intensity[i]] })
                }] : []
                colors: ({ peaks: Theme.plotAccentColor })
            }
        }
    }

    // --- details ---
    ScrollView {
        id: details
        SplitView.preferredHeight: 200
        SplitView.minimumHeight: 80
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: details.availableWidth - 16
            x: 8
            spacing: 3

            component Key: Label { color: Theme.mutedTextColor; Layout.preferredWidth: 150; Layout.alignment: Qt.AlignTop; elide: Text.ElideRight }
            component Value: TextEdit {
                Layout.fillWidth: true
                readOnly: true
                selectByMouse: true
                wrapMode: Text.WrapAnywhere
                color: Theme.textColor
                selectionColor: Theme.primaryColor
                font: Qt.application.font
            }

            RowLayout {
                visible: root.hasCompound
                Key { text: qsTr("InChIKey") }
                Value { text: root.compound.inchikey || ""; font.family: "monospace" }
            }
            RowLayout {
                visible: !!root.compound.smiles
                Key { text: qsTr("SMILES") }
                Value { text: root.compound.smiles || ""; font.family: "monospace" }
            }
            RowLayout {
                visible: !!root.compound.pubchem_id
                Key { text: qsTr("PubChem") }
                Label {
                    Layout.fillWidth: true
                    text: "<a href='https://pubchem.ncbi.nlm.nih.gov/compound/%1'>CID %1</a>".arg(root.compound.pubchem_id)
                    linkColor: Theme.primaryColor
                    onLinkActivated: link => Qt.openUrlExternally(link)
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
            }
            Repeater {
                model: root.spectrum.metadata ? Object.keys(root.spectrum.metadata).sort() : []
                delegate: RowLayout {
                    required property string modelData
                    Key { text: parent.modelData; ToolTip.visible: hov.hovered; ToolTip.text: parent.modelData; HoverHandler { id: hov } }
                    Value { text: root.spectrum.metadata[parent.modelData] }
                }
            }
        }
    }
}
