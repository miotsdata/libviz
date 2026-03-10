// qml/main.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0

import "qrc:/qml"

ApplicationWindow {
    id: window
    visible: true
    width: 800
    height: 600
    minimumWidth: 800
    title: "LibViz"

    // =========================
    // MENU BAR
    // =========================

    menuBar: MenuBar {
        Menu {
            title: "Library"

            MenuItem {
                text: "Create library"
                onTriggered: nav.show_create_library()
            }

            MenuItem {
                text: "Load library from .msp"
                onTriggered: {
                    var path = LoadLibraryBackend.selectPathMsp();
                    if (path !== "") {
                        LoadLibraryBackend.loadLibraryFromMsp(path);
                    }
                }
            }
        }

        Menu {
            title: "Insert"

            MenuItem {
                text: "Spectra from mzml"
                onTriggered: {
                    var path = LoadMzmlBackend.selectPathMzml();
                    if (path !== "") {
                        LoadMzmlBackend.load(path);
                    }
                }
            }
        }
    }

    // =========================
    // MAIN LAYOUT
    // =========================

        // -------- Main content --------
    StackView {
        id: stack
        anchors.fill: parent
        Layout.fillWidth: true
        Layout.fillHeight: true
        initialItem: HomePage {}
    }

        // -------- Status bar --------
    Rectangle {
        id: statusBar
        Layout.fillWidth: true
        height: visible ? 32 : 0
        visible: false
        color: "#e8e8e8"
        border.color: "#d0d0d0"

        RowLayout {
            anchors.fill: parent
            anchors.margins: 8
            spacing: 12

            Text {
                id: statusText
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }

            ProgressBar {
                id: progressBar
                width: 200
                height: 20
                indeterminate: true
                from: 0
                to: 100
            }
        }
    }

    // =========================
    // NAVIGATION CONNECTIONS
    // =========================
    Connections {
        target: nav

        function onGoHome() {
            stack.clear();
            stack.push("HomePage.qml");
        }

        function onGoCreateLibrary() {
            stack.push("CreateLibraryPage.qml");
        }

        function onGoLibraryHomePage() {
            stack.push("LibraryHomePage.qml");
        }
    }

    // =========================
    // LOAD LIBRARY CONNECTIONS
    // =========================
    Connections {
        target: LoadLibraryBackend

        function onLibraryLoading(path) {
            statusBar.visible = true;
            statusText.text = "Loading \"" + path + "\"";
        }

        function onLoadedLibrarySuccessfully(connection_name, db_path) {
            statusBar.visible = false;
            statusText.text = "";
            console.log("SUCCESS SIGNAL RECEIVED");
            nav.show_library_page();
        }

        function onErrorOccurred(message) {
            statusBar.visible = false;
            statusText.text = "";
            console.log("Error:", message);
        }
    }

    Connections {
        target: LoadMzmlBackend

        function onMzmlLoading(path) {
            statusBar.visible = true;
            statusText.text = "Loading \"" + path + "\"";
        }

        function onSuccessOccurred(path) {
            statusBar.visible = false;
            statusText.text = "";
            var component = Qt.createComponent("qrc:/qml/AddSpectraWindow.qml")
            var window    = component.createObject()
            window.show()
        }
    }
}
