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
                onTriggered: { /* TODO */ }
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
        visible: false
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
                running: statusBar.visible
                width: 20
                height: 20
            }
        }
    }
}
