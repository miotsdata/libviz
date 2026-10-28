import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// Shown when no library is selected: the main actions + recent libraries.
Item {
    id: page
    property var recentLibraries: []
    signal openRecent(string path)

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 560)
        spacing: 16

        Label {
            text: "LibViz"
            font.pixelSize: 40
            font.weight: Font.Light
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: qsTr("Build MS/MS spectral libraries from mzML, import MSP libraries, and inspect them.")
            color: Theme.mutedTextColor
        }

        RowLayout {
            spacing: Theme.spacing
            Button { text: qsTr("New library…"); enabled: !Libraries.busy; onClicked: window.newLibraryDialog() }
            Button { text: qsTr("Open library…"); enabled: !Libraries.busy; onClicked: window.openLibraryDialog() }
            Button { text: qsTr("Import MSP…"); enabled: !Libraries.busy; onClicked: window.importMspDialog() }
        }

        Label {
            visible: page.recentLibraries.length > 0
            Layout.topMargin: 16
            text: qsTr("RECENT")
            font.pixelSize: Theme.captionPixelSize
            font.bold: true
            color: Theme.mutedTextColor
        }
        Repeater {
            model: page.recentLibraries
            delegate: ItemDelegate {
                required property string modelData
                Layout.fillWidth: true
                text: modelData
                enabled: !Libraries.busy
                onClicked: page.openRecent(modelData)
            }
        }
    }
}
