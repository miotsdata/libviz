import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs

ApplicationWindow {
    width: 640
    height: 480
    visible: true

    Column {
        anchors.centerIn: parent
        spacing: 20

        ComboBox {
            id: adductCombo
            width: 200
            model: adductListModel
            textRole: "formula"
            onCurrentIndexChanged: {
                if (currentIndex >= 0) {
                    console.log("Selected:", adductListModel.getId(currentIndex))
                }
            }
        }

        TextField {
            id: testTextField
            width: 200
            placeholderText: "Enter something..."
            onEditingFinished: {
                console.log("TextField editing finished:", text)
            }
        }
    }

    header: ToolBar {
        Button {
            text: qsTr("Choose Image...")
            onClicked: fileDialog.open()
        }
    }

    Image {
        id: image
        anchors.fill: parent
        fillMode: Image.PreserveAspectFit
    }

    FileDialog {
        id: fileDialog
        currentFolder: StandardPaths.standardLocations(StandardPaths.PicturesLocation)[0]
        onAccepted: image.source = selectedFile
    }
}