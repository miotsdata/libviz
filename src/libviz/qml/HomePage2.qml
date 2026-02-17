// Main.qml

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0

Page {
    ColumnLayout {
        anchors.fill: parent

        TextField {
            placeholderText: "Filter by name..."
            onTextChanged: MockCompoundModel.setFilter(text)
        }

        
        ListModel {
            id: headerModel
            ListElement { label: "ID"; column: 0 }
            ListElement { label: "Name"; column: 1 }
            ListElement { label: "Formula"; column: 2 }
            ListElement { label: "Exact Mass"; column: 3 }
        }

        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            height: 40

            property int lastSortedColumn: -1
            property bool ascending: true

            Repeater {
                model: headerModel

                Rectangle {
                    Layout.fillWidth: true
                    height: 40
                    color: "#dddddd"
                    border.width: 1

                    required property string label
                    required property int column

                    Text {
                        anchors.centerIn: parent
                        text: label
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (headerRow.lastSortedColumn === column)
                                headerRow.ascending = !headerRow.ascending
                            else {
                                headerRow.lastSortedColumn = column
                                headerRow.ascending = true
                            }

                            MockCompoundModel.setSort(
                                        column,
                                        headerRow.ascending ? "asc" : "desc"
                                        )
                        }
                    }
                }
            }
        }

        TableView {
            id: table
            Layout.fillWidth: true
            Layout.fillHeight: true

            model: MockCompoundModel

            clip: true

            columnSpacing: 1
            rowSpacing: 1

            columnWidthProvider: function(column) {
                return width / 4 // 4 columns
            }

            delegate: Rectangle {
                implicitWidth: 1
                implicitHeight: 35
                border.width: 0.5

                Text {
                    anchors.centerIn: parent
                    text: model.display
                }
            }

            ScrollBar.vertical: ScrollBar {}

        }
    }
}
