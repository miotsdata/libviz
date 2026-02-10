// qml/main.qml
import QtQuick
import QtQuick.Controls

ApplicationWindow {
    visible: true
    width: 800
    height: 600
    title: "LibViz"

    menuBar: MenuBar {
        Menu {
            title: "Library"

            MenuItem {
                text: "Create library"
                onTriggered: nav.show_create_library()
            }

            MenuItem {
                text: "Load library"
                onTriggered: nav.show_load_library()
            }
        }
    }

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: HomePage {}
    }

    // Navigation bindings
    Connections {
        target: nav

        function onGoHome() {
            stack.clear()
            stack.push("HomePage.qml")
        }

        function onGoCreateLibrary() {
            stack.push("CreateLibraryPage.qml")
        }

        function onGoLoadLibrary() {
            stack.push("LoadLibraryPage.qml")
        }
    }
}
