import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Paged compound table (Inspector.compounds, ADR 3). Click or ↑/↓ selects.
Rectangle {
    id: root
    color: Theme.fieldColor
    property int selectedRow: -1
    readonly property var model: Inspector.compounds
    signal editRequested()
    signal exportRequested()
    signal deleteRequested()
    readonly property var widths: [0.27, 0.17, 0.16, 0.29, 0.11]

    function select(row) {
        if (row < 0 || row >= model.count) return
        selectedRow = row
        table.positionViewAtRow(row, TableView.Contain)
        Inspector.selectCompoundRow(row)
    }
    Connections {
        target: root.model
        function onModelReset() { root.selectedRow = -1 }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        HorizontalHeaderView {
            id: header
            Layout.fillWidth: true
            syncView: table
            clip: true
            delegate: Rectangle {
                required property int column
                required property string display
                implicitHeight: 26
                color: Theme.controlColor
                border.color: Theme.borderColor
                Label {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    verticalAlignment: Text.AlignVCenter
                    text: parent.display
                    font.bold: true
                    elide: Text.ElideRight
                }
                TapHandler { onTapped: root.model.sortByColumn(parent.column) }
                HoverHandler { cursorShape: root.model.isSortable(parent.column) ? Qt.PointingHandCursor : Qt.ArrowCursor }
            }
        }

        TableView {
            id: table
            objectName: "compoundTable"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.model
            boundsBehavior: Flickable.StopAtBounds
            columnWidthProvider: column => Math.max(50, root.widths[column] * (table.width - 16))
            onWidthChanged: forceLayout()
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
            focus: true
            Keys.onUpPressed: root.select(root.selectedRow - 1)
            Keys.onDownPressed: root.select(root.selectedRow + 1)
            Keys.onPressed: event => {
                if (event.key === Qt.Key_PageDown) { root.select(Math.min(root.model.count - 1, root.selectedRow + 20)); event.accepted = true }
                else if (event.key === Qt.Key_PageUp) { root.select(Math.max(0, root.selectedRow - 20)); event.accepted = true }
            }

            delegate: Rectangle {
                required property int row
                required property int column
                required property string display
                implicitHeight: 24
                color: row === root.selectedRow ? Theme.primaryColor
                     : row % 2 ? Theme.fieldColor : Theme.secondaryColor
                Label {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 4
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: column >= 2 && column !== 3 ? Text.AlignRight : Text.AlignLeft
                    text: parent.display
                    elide: Text.ElideRight
                    color: parent.row === root.selectedRow ? Theme.highlightedTextColor : Theme.textColor
                    font.family: column === 3 ? "monospace" : Qt.application.font.family
                }
                TapHandler { onTapped: { table.forceActiveFocus(); root.select(parent.row) } }
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: { root.select(parent.row); rowMenu.popup() }
                }
            }
        }
        Menu {
            id: rowMenu
            MenuItem { text: qsTr("Edit compound…"); onTriggered: root.editRequested() }
            MenuItem { text: qsTr("Export as MSP…"); onTriggered: root.exportRequested() }
            MenuSeparator {}
            MenuItem { text: qsTr("Delete compound…"); onTriggered: root.deleteRequested() }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 24
            color: Theme.secondaryColor
            Label {
                anchors.verticalCenter: parent.verticalCenter
                x: 8
                font.pixelSize: Theme.captionPixelSize
                color: Theme.mutedTextColor
                text: root.model.loading ? qsTr("Searching…")
                      : qsTr("%1 compounds").arg(root.model.count.toLocaleString(Qt.locale(), "f", 0))
            }
        }
    }

    Label {
        anchors.centerIn: parent
        visible: !root.model.loading && root.model.count === 0
        text: qsTr("No compounds match")
        color: Theme.placeholderTextColor
    }
}
