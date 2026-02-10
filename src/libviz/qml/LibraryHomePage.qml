import QtQuick 2.15
import QtQuick.Controls 2.15

Page {
    id: libraryPage
    property string libraryName: ""
    property int numCompounds: 0
    property int numSpectra: 0

    Column {
        spacing: 10
        anchors.centerIn: parent

        Text { text: "Library: " + libraryName; font.pointSize: 18 }
        Text { text: "Compounds: " + numCompounds }
        Text { text: "Spectra: " + numSpectra }

        Row {
            spacing: 10
            Button {
                text: "Refresh"
                onClicked: libraryService.refresh_library()
            }

            Button {
                text: "Home"
                onClicked: nav.show_home()
            }
        }
    }

    Connections {
        target: libraryService
        function onLibraryChanged() {
            libraryName = name
            numCompounds = compounds
            numSpectra = spectra
        }
    }
}
