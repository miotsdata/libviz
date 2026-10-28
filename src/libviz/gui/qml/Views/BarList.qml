import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Horizontal bars for counts per category: one hue (magnitude, not
// identity), label left, value right, hover shows the exact share.
ColumnLayout {
    id: root
    property string title
    property var rows: []  // [[label, count], ...], already sorted
    property int maxRows: 12
    readonly property real total: rows.reduce(function (s, r) { return s + r[1] }, 0)
    readonly property real maxCount: rows.length ? Math.max.apply(null, rows.map(function (r) { return r[1] })) : 1
    spacing: 3

    Label { text: root.title; font.bold: true }
    Repeater {
        model: root.rows.slice(0, root.maxRows)
        delegate: Item {
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: 20
            Label {
                id: lbl
                width: 110
                anchors.verticalCenter: parent.verticalCenter
                text: String(modelData[0])
                elide: Text.ElideRight
                color: Theme.textColor
            }
            Rectangle {
                id: track
                anchors.left: lbl.right
                anchors.leftMargin: 6
                anchors.right: val.left
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                height: 12
                color: "transparent"
                Rectangle {
                    width: Math.max(2, track.width * modelData[1] / root.maxCount)
                    height: parent.height
                    radius: 3
                    color: hov.hovered ? Qt.lighter(Theme.plotAccentColor, 1.2) : Theme.plotAccentColor
                }
            }
            Label {
                id: val
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: 70
                horizontalAlignment: Text.AlignRight
                text: modelData[1].toLocaleString(Qt.locale(), "f", 0)
                color: Theme.mutedTextColor
            }
            HoverHandler { id: hov }
            ToolTip.visible: hov.hovered
            ToolTip.text: "%1: %2 (%3%)".arg(modelData[0]).arg(modelData[1]).arg((100 * modelData[1] / Math.max(1, root.total)).toFixed(1))
        }
    }
    Label {
        visible: root.rows.length > root.maxRows
        text: qsTr("+ %1 more").arg(root.rows.length - root.maxRows)
        color: Theme.mutedTextColor
        font.pixelSize: Theme.captionPixelSize
    }
}
