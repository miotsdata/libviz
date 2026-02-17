// Main.qml

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0

Page {
    id: testessdhfgaslhbmas
    anchors.fill: parent

    ColumnLayout{
        anchors.fill: parent
        
        RowLayout {
                
            Rectangle {
                width: window.width / 3
                Layout.fillHeight: true
                color: "blue"
            }

            ColumnLayout {
                Layout.fillWidth: true

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

                Row {
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
                        if (column === 0) return 80
                        if (column === 3) return 120
                        if (column === 2) return 150

                        // Name column fills remaining width
                        var fixed = 80 + 150 + 120
                        return width - fixed
                    }

                    delegate: Rectangle {
                        implicitWidth: 1
                        implicitHeight: 35
                        border.width: 0.5
                        clip: true

                        HoverHandler {
                            id: hoverHandler
                        }

                        Text {
                            id: cellText
                            anchors.fill: parent
                            anchors.margins: 6

                            text: model.display
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter

                            elide: Text.ElideRight
                            wrapMode: Text.NoWrap
                        }

                        ToolTip {
                            visible: hoverHandler.hovered &&
                                    cellText.implicitWidth > cellText.width
                            text: display
                        }
                    }

                    ScrollBar.vertical: ScrollBar {}

                }
            }
        }

        Rectangle {
            height: window.height / 3
            color: "red"
            Layout.fillWidth: true
        }
    }
}
