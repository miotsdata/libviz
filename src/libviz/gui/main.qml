// qml/main.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import Libviz.Pages 1.0

ApplicationWindow {
    id: window
    visible: true
    width: 1024
    height: 680
    minimumWidth: 800
    minimumHeight: 560
    title: "LibViz"

    // =========================
    // MENU BAR
    // =========================

    menuBar: MenuBar {

        Menu {
            title: qsTr("Library")

            MenuItem {
                text: qsTr("Create library")
                onTriggered: { /* TODO */ }
            }

            MenuSeparator {}

            MenuItem {
                text: qsTr("Load from .msp…")
                onTriggered: mspFileDialog.open()
            }

            MenuItem {
                text: qsTr("Load from .db…")
                onTriggered: { /* TODO */ }
            }
        }

        Menu {
            title: qsTr("Insert")

            MenuItem {
                text: qsTr("Spectra from .mzml…")
                enabled: false   // enabled once a library is open
                onTriggered: { /* TODO */ }
            }
        }

        Menu {
            title: qsTr("Save")

            MenuItem {
                text: qsTr("Save as .db…")
                enabled: false   // enabled once a library is open
                onTriggered: { /* TODO */ }
            }
        }
    }

    // =========================
    // MAIN CONTENT
    // =========================

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: WelcomePage {}
    }


    // =========================
    // STATUS BAR
    // =========================

    footer: ToolBar {
        id: statusBar
        visible: statusText.text !== ""
        height: visible ? implicitHeight : 0

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 12

            Text {
                id: statusText
                Layout.fillWidth: true
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
                font.pixelSize: 12
                color: "#444444"
            }

            BusyIndicator {
                id: busyIndicator
                running: statusText.text !== ""
                width: 20
                height: 20
            }
        }
    }

    Connections {
        target: libraryManager

        function onStatusChanged(message) {
            statusText.text = message
        }

        function onErrorOccurred(message) {
            errorDialog.errorText = message
            errorDialog.open()
        }

        function onLibraryLoaded(path) {
            print("Library loaded:", path)
        }
    }

    Dialog {
        id: errorDialog
        property alias errorText: errorLabel.text
        title: "Error"
        Label { id: errorLabel }
        standardButtons: Dialog.Ok
    }

    FileDialog {
        id: mspFileDialog
        title: qsTr("Select .msp file")
        nameFilters: ["MSP files (*.msp)", "All files (*)"]
        onAccepted: libraryManager.loadLibraryFromMsp(selectedFile)
    }
}
