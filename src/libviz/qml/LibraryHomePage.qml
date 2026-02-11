import QtQuick 2.15
import QtQuick.Controls 2.15

Page {
    id: libraryPage

    Column {
        spacing: 10
        anchors.centerIn: parent

        Text {
            text: "Library: " + libraryService.name
            font.pointSize: 18
        }
        Text {
            text: "Compounds: " + libraryService.n_compounds
        }
        Text {
            text: "Spectra: " + libraryService.n_spectra
        }

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
}
