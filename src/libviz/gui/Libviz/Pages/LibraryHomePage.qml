// Libviz/Pages/LibraryHomePage.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Item {
    id: root

    // =========================
    // ROW 1  (40% height)
    // =========================

    SplitView {
        id: topRow
        orientation: Qt.Horizontal
        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }
        height: parent.height * 0.4

        Rectangle {
            SplitView.preferredWidth: topRow.width * 0.3
            SplitView.minimumWidth: 100
            color: "#4CAF50"   // green

            Text {
                anchors.centerIn: parent
                text: "Top Left"
                color: "white"
                font.pixelSize: 14
            }
        }

        Rectangle {
            SplitView.fillWidth: true
            color: "#2196F3"   // blue

            Text {
                anchors.centerIn: parent
                text: "Top Right"
                color: "white"
                font.pixelSize: 14
            }
        }
    }

    // =========================
    // ROW 2  (60% height)
    // =========================

    SplitView {
        id: bottomRow
        orientation: Qt.Horizontal
        anchors {
            top: topRow.bottom
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }

        Rectangle {
            SplitView.preferredWidth: bottomRow.width * 0.3
            SplitView.minimumWidth: 100
            color: "#FF9800"   // orange

            Text {
                anchors.centerIn: parent
                text: "Bottom Left"
                color: "white"
                font.pixelSize: 14
            }
        }

        Rectangle {
            SplitView.fillWidth: true
            color: "#E91E63"   // pink

            Text {
                anchors.centerIn: parent
                text: "Bottom Right"
                color: "white"
                font.pixelSize: 14
            }
        }
    }
}
