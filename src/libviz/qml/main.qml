// qml/main.qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 800
    height: 600
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
                    var path = loadLibBackend.selectPathMsp();
                    if (path !== "") {
                        loadLibBackend.loadLibraryFromMsp(path);
                    }
                }
            }
        }
    }

    // =========================
    // MAIN LAYOUT
    // =========================
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // -------- Main content --------
        StackView {
            id: stack
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
                    width: 300
                    height: 20
                    indeterminate: true
                    from: 0
                    to: 100
                }
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
        target: loadLibBackend

        function onLibraryLoading(path) {
            statusBar.visible = true;
            statusText.text = "Loading \"" + path + "\"";
        }

        function onSuccessOccurred() {
            statusBar.visible = false;
            statusText.text = "";
            nav.show_library_page();
        }

        function onErrorOccurred(message) {
            statusBar.visible = false;
            statusText.text = "";
            console.log("Error:", message);
        }
    }
}
