import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Sidebar: the open libraries. Click selects, right-click for actions.
Rectangle {
    id: panel
    color: Theme.secondaryColor
    signal closeRequested(string key)

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Label {
            Layout.fillWidth: true
            Layout.margins: Theme.spacing
            text: qsTr("LIBRARIES")
            font.pixelSize: Theme.captionPixelSize
            font.bold: true
            color: Theme.mutedTextColor
        }

        ListView {
            id: list
            objectName: "librariesList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: Libraries.libraries
            ScrollBar.vertical: ScrollBar {}

            delegate: ItemDelegate {
                id: row
                required property var modelData
                width: ListView.view.width
                highlighted: modelData.key === Libraries.selectedKey
                onClicked: Libraries.selectLibrary(modelData.key)
                ToolTip.visible: hovered
                ToolTip.delay: 600
                ToolTip.text: modelData.isTemp ? qsTr("Imported, not saved yet") : modelData.path

                contentItem: ColumnLayout {
                    spacing: 2
                    RowLayout {
                        Label {
                            Layout.fillWidth: true
                            text: row.modelData.name
                            elide: Text.ElideRight
                            font.bold: row.highlighted
                            color: row.highlighted ? Theme.highlightedTextColor : Theme.textColor
                        }
                        Label {
                            visible: row.modelData.isTemp
                            text: qsTr("unsaved")
                            font.pixelSize: Theme.captionPixelSize
                            color: row.highlighted ? Theme.highlightedTextColor : Theme.warningColor
                        }
                    }
                    Label {
                        text: qsTr("%1 compounds · %2 spectra")
                              .arg(row.modelData.nCompounds.toLocaleString(Qt.locale(), "f", 0))
                              .arg(row.modelData.nSpectra.toLocaleString(Qt.locale(), "f", 0))
                        font.pixelSize: Theme.captionPixelSize
                        color: row.highlighted ? Theme.highlightedTextColor : Theme.mutedTextColor
                    }
                }

                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: { Libraries.selectLibrary(row.modelData.key); menu.popup() }
                }
                Menu {
                    id: menu
                    MenuItem { text: qsTr("Close"); onTriggered: panel.closeRequested(row.modelData.key) }
                }
            }

            Label {
                anchors.centerIn: parent
                visible: list.count === 0
                text: qsTr("No library open")
                color: Theme.placeholderTextColor
            }
        }
    }
}
