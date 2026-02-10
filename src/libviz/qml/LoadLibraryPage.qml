import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Load Library"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 50
        spacing: 16

        Label {
            text: "Load a Library"
            font.pixelSize: 22
            Layout.alignment: Qt.AlignHCenter
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField {
                id: pathField
                placeholderText: "Library path"
                Layout.fillWidth: true
            }

            Button {
                text: "Browse..."
                onClicked: pathField.text = loadLibBackend.selectPath()
            }
        }

        Text {
            id: errorLabel
            color: "red"
            visible: false
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }

        Button {
            text: "Load"
            enabled: pathField.text !== ""
            Layout.alignment: Qt.AlignHCenter
            onClicked: loadLibBackend.loadLibraryFromDb(pathField.text)
        }
    }

    Connections {
        target: loadLibBackend

        onErrorOccurred: {
            errorLabel.text = message;
            errorLabel.visible = true;
        }

        onSuccessOccurred: {
            errorLabel.visible = false;
            stack.push("LibraryHomePage.qml");
        }
    }
}
