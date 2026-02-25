import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0
import "utils"

ApplicationWindow {
    id: addSpectraWindow
    visible: true
    width: 800
    height: 600
    minimumWidth: 800
    minimumHeight: 600
    title: "Add spectra from mzML file"

    Pane {
        id: addSpectraPane
        anchors.fill: parent
        padding: 10

        property int adduct_id: -1
        
        ColumnLayout {
            id: allCol
            anchors.fill: parent
            Layout.fillWidth: true

            ColumnLayout {
                id: filterByMzColLayout
                Layout.fillWidth: true

                // 🔹 Central safe updater function
                function safeUpdateMZ() {
                    var formula = molecularFormulaText.text
                    //var adduct_id = addSpectraPane.adduct_id
                    var adduct_id = 1

                    // disable search if formula or adduct not selected
                    if (!formula || adduct_id === -1) {
                        mzText.text = ""
                        filterByMzButton.enabled = false
                        return
                    }

                    try {
                        var mz = AddSpectraBackend.calculate_mz_from_formula_adduct(formula, adduct_id)

                        if (mz === undefined || mz === null || isNaN(mz)) {
                            mzText.text = ""
                            filterByMzButton.enabled = false
                        } else {
                            mzText.text = mz.toFixed(4)
                            filterByMzButton.enabled = true
                        }
                    } catch (e) {
                        console.log("Error calculating m/z:", e)
                        mzText.text = ""
                        filterByMzButton.enabled = false
                    }
                }

                // 🔹 Header
                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Search by m/z")
                }

                // 🔹 Input + button
                RowLayout {
                    Layout.fillWidth: true

                    // m/z TextField
                    TextField {
                        id: mzText
                        placeholderText: qsTr("Search by m/z...")
                        Layout.preferredWidth: addSpectraWindow.width / 4
                        Layout.preferredHeight: 40

                        Keys.onEscapePressed: function(event) {
                            event.accepted = true
                            focus = false
                        }

                        validator: DoubleValidator {
                            bottom: 0.0
                            decimals: 4
                        }
                    }

                    SpinBox { 
                        id: ppmToleranceSpinBox 
                        from: 0 
                        to: 100 
                        value: 5 
                        stepSize: 1 
                        Layout.preferredWidth: 120 
                        Layout.preferredHeight: 40 
                        editable: false 
                        validator: IntValidator { 
                            bottom: 0 
                            top: 100 
                            }
                    }

                    // Search button
                    Timer {
                        id: clickDebounce
                        interval: 400  // milliseconds
                        repeat: false
                        onTriggered: filterByMzButton.enabled = true
                    }

                    Button {
                        id: filterByMzButton
                        text: qsTr("Search")
                        enabled: !AddSpectraTableModel.querying && mzText.acceptableInput
                        onClicked: {
                            if (!enabled || mzText.text === "")
                                return // ignore fast clicks

                            //filterByMzButton.enabled = false
                            AddSpectraTableModel.refresh(parseFloat(mzText.text), ppmToleranceSpinBox.value)
                            //AddSpectraTableModel.refresh(parseFloat(mzText.text), 10)
                            //clickDebounce.start()
                        }
                    }
                }

                // 🔹 Hooks to reactively update m/z when formula or adduct changes
                TextField {
                    id: molecularFormulaText
                    placeholderText: qsTr("Molecular Formula...")
                    Layout.preferredWidth: addSpectraWindow.width / 4
                    Layout.preferredHeight: 40

                    Keys.onEscapePressed: focus = false

                    onEditingFinished: filterByMzColLayout.safeUpdateMZ()
                }

                ComboBox {
                    id: adductCombo
                    Layout.preferredHeight: 40
                    model: AdductListModel
                    textRole: "formula"

                    onCurrentIndexChanged: {
                        if (currentIndex >= 0) {
                            addSpectraPane.adduct_id = AdductListModel.getId(currentIndex);
                        }
                        else
                            addSpectraPane.adduct_id = -1

                        //filterByMzColLayout.safeUpdateMZ()
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: addSpectraWindow.height / 3

                

                ListModel {
                    id: headerModel
                    ListElement { label: "ID"; column: 0 }
                    ListElement { label: "spectrum_index"; column: 1 }
                    ListElement { label: "precursor_mz"; column: 2 }
                    ListElement { label: "retention_time"; column: 3 }
                    ListElement { label: "Polarity"; column: 4 }
                    ListElement { label: "collision_energy"; column: 5 }
                }

                Row {
                    
                    id: headerRow
                    Layout.fillWidth: true
                    height: 40

                    property int lastSortedColumn: -1
                    property bool ascending: true

                    Repeater {
                        model: headerModel

                        Rectangle {
                            width: {
                                if (column === 0) return 100
                                if (column === 1) return 120
                                if (column === 2) return 150
                                if (column === 3) return 80
                                if (column === 4) return 120
                                return 100
                            }
                            height: 40
                            color: "#dddddd"
                            border.width: 1

                            required property string label
                            required property int column

                            Text {
                                anchors.fill: parent
                                anchors.margins: 6

                                text: label
                                font.bold: true
                                horizontalAlignment: Text.AlignLeft
                                verticalAlignment: Text.AlignVCenter

                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }
                        }
                    }
                }   

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TableView {
                        id: addSpectraTable
                        anchors.fill: parent

                        property int selectedRow: -1
                        property int hoveredRow: -1

                        model: AddSpectraTableModel

                        clip: true
                        columnSpacing: 1
                        rowSpacing: 1

                        columnWidthProvider: function(column) {
                            if (column === 0) return 100
                            if (column === 1) return 120
                            if (column === 2) return 150
                            if (column === 3) return 80
                            if (column === 4) return 120
                            return 100
                        }

                        delegate: Rectangle {
                            implicitHeight: 35
                            border.width: 0.5

                            // Store row index
                            required property bool selected
                            required property bool current

                            // Background for hover
                            Rectangle {
                                anchors.fill: parent
                                color: addSpectraTable.selectedRow === row ? '#e0da20' : (addSpectraTable.hoveredRow === row ? '#a7a7a7' : "#ffffff")
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    addSpectraTable.selectedRow = row
                                    // model.id refers to the 'id' column of the compound
                                    // var compound_id = CompoundTableModel.idForRow(table.currentRow)
                                    // console.log("Clicked compound_id:", compound_id)
                                    console.log("Clicked row:", row, "column:", column)
                                    var spectra_id = AddSpectraTableModel.idForRow(row)
                                    console.log("Clicked spectra_id:", spectra_id)
                                    //SpectrumPlotModel.setPeakId(spectra_id)
                                }
                            }

                            HoverHandler {

                                onHoveredChanged: {
                                    addSpectraTable.hoveredRow = row
                                }
                            }

                            Text {
                                anchors.fill: parent
                                anchors.margins: 6
                                text: model.display
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }
                        }

                        ScrollBar.vertical: ScrollBar {}
                    }

                    // 🔹 Overlay message
                    Rectangle {
                        anchors.fill: parent
                        visible: !AddSpectraTableModel.hasRows

                        color: "transparent"

                        Text {
                            anchors.centerIn: parent
                            text: "No spectra found"
                            font.pixelSize: 18
                            color: "#666666"
                        }
                    }
                }
            }
        }
    }
}