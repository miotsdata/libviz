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
                    var adduct_id = addSpectraPane.adduct_id

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

                        Keys.onEscapePressed: focus = false
                        Keys.onReturnPressed: filterByMzButton.clicked()

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
                        editable: true 
                        validator: IntValidator { 
                            bottom: 0 
                            top: 100 
                            }
                        enabled: !AddSpectraTableModel.querying
                    }

                    // Search button
                    Button {
                        id: filterByMzButton
                        text: qsTr("Search")
                        enabled: mzText.text !== ""  // initially disabled
                        onClicked: {
                            AddSpectraTableModel.refresh(parseFloat(mzText.text), ppmToleranceSpinBox.value)
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

                        filterByMzColLayout.safeUpdateMZ()
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

                            // MouseArea {
                            //     anchors.fill: parent
                            //     onClicked: {
                            //         if (headerRow.lastSortedColumn === column)
                            //             headerRow.ascending = !headerRow.ascending
                            //         else {
                            //             headerRow.lastSortedColumn = column
                            //             headerRow.ascending = true
                            //         }

                            //         CompoundTableModel.setSort(
                            //                     column,
                            //                     headerRow.ascending ? "asc" : "desc"
                            //                     )
                            //     }
                            // }
                        }
                    }
                }   

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    TableView {
                        id: table
                        anchors.fill: parent

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
                        visible: AddSpectraTableModel.rowCountProperty === 0

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