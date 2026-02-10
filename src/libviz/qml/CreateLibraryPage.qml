import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Page {
    id: root
    title: "Create Library"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 50
        spacing: 16

        Label {
            text: "Create a new Library"
            font.pixelSize: 22
            Layout.alignment: Qt.AlignHCenter
        }

        TextField { id: nameField; placeholderText: "Library name"; Layout.fillWidth: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            TextField { id: pathField; placeholderText: "Library path"; Layout.fillWidth: true }

            Button { text: "Browse..."; onClicked: pathField.text = createLibBackend.selectPath() }
        }

        Text { id: errorLabel; color: "red"; visible: false; wrapMode: Text.Wrap; Layout.fillWidth: true }

        Button {
            text: "Create"
            enabled: nameField.text !== "" && pathField.text !== ""
            Layout.alignment: Qt.AlignHCenter
            onClicked: createLibBackend.createLibrary(nameField.text, pathField.text)
        }
    }
}
