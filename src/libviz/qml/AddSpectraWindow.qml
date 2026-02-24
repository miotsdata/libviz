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
        anchors.fill: parent
        padding: 10
        
        ColumnLayout {
            id: allCol
            anchors.fill: parent
            Layout.fillWidth: true

            ColumnLayout {
                id: filterByMzColLayout
                Layout.fillWidth: true
                    Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: qsTr("Search by m/z")

                            DebugRectangle {}
                        }
                    

                    RowLayout {
                        Layout.fillWidth: true
                        
                        TextField {
                            id: mzText
                            placeholderText: qsTr("Search by m/z...")
                            Layout.preferredWidth: addSpectraWindow.width / 4
                            Layout.preferredHeight: 40

                            Keys.onEscapePressed: {
                                focus = false
                            }

                            Keys.onReturnPressed: {
                                print("Searching by m/z: " + mzText.text)
                                filterByMzButton.clicked()
                            }

                            validator: DoubleValidator {
                                bottom: 0.0
                                decimals: 4
                            }
                        }

                        Button {
                            id: filterByMzButton
                            text: qsTr("Search")
                            enabled: mzText.text != ""
                            onClicked: {
                                print("Searching by m/z: " + mzText.text)
                                AddSpectraTableModel.refresh(parseFloat(mzText.text), ppmToleranceSpinBox.value)
                            }
                        }
                    }
            }

            ColumnLayout {
                id: filterByFormulaLayout
                Layout.fillWidth: true

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Search by Molecular formula + Adduct")
                }

                RowLayout {
                    Layout.fillWidth: true
                    
                    TextField {
                        id: molecularFormulaText

                        placeholderText: qsTr("Molecular Formula...")
                        Layout.preferredWidth: addSpectraWindow.width / 4
                        Layout.preferredHeight: 40

                        Keys.onEscapePressed: {
                            focus = false
                        }
                    }

                    TextField {

                        placeholderText: qsTr("Mo capiamo come cazzo fare")
                        Layout.preferredWidth: addSpectraWindow.width / 4
                        Layout.preferredHeight: 40
                        Keys.onEscapePressed: {
                            focus = false
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
                    }

                    Button {
                        text: qsTr("Search")
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: addSpectraWindow.height / 3

                DebugRectangle {}

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
                    DebugRectangle {}
                    id: headerRow
                    Layout.fillWidth: true
                    height: 40

                    property int lastSortedColumn: -1
                    property bool ascending: true

                    Repeater {
                        model: headerModel

                        Rectangle {
                            width: table.columnWidthProvider(column) // ⭐ key line
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