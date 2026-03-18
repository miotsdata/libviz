// gui/qml/pages/WelcomePage.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Item {

    Column {
        anchors.centerIn: parent
        spacing: 16

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "LibViz"
            font.pixelSize: 48
            font.weight: Font.Light
            color: Material.foreground
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Open or create a library to get started"
            font.pixelSize: 14
            color: Material.hintTextColor
        }
    }
}
