import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// The selected library. P1: summary header; the inspector lands in P2.
Item {
    id: page
    readonly property var info: Libraries.selected

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: Theme.spacing

        RowLayout {
            Label { text: page.info.name || ""; font.pixelSize: Theme.headingPixelSize; font.bold: true }
            Label {
                visible: page.info.isTemp === true
                text: qsTr("unsaved — File › Save as… to keep it")
                color: Theme.warningColor
            }
            Item { Layout.fillWidth: true }
        }
        Label {
            text: qsTr("%1 compounds · %2 spectra").arg(page.info.nCompounds).arg(page.info.nSpectra)
            color: Theme.mutedTextColor
        }
        Item { Layout.fillHeight: true }
    }
}
