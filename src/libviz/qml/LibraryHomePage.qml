import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

//import "utils"

Page {
    id: libraryPage

    ColumnLayout {
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

        ScrollView {
            
            TableView {

                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredWidth: 300
                Layout.preferredHeight: 300

                model: compoundModel
                delegate: TableViewDelegate {
                }

                Component.onCompleted: {
                    console.log("Init done");
                }
            }
        }

        // TableView {
        //     id: table
        //     Layout.fillWidth: true
        //     Layout.fillHeight: true

        //     // Only bind if model exists
        //     model: compoundModel !== undefined ? compoundModel : null
        //     visible: compoundModel !== undefined

        //     // headerVisible: true
        //     // sortIndicatorVisible: true
        // }

        // libraryMetabolitesTable {
        //     Layout.fillWidth: true
        //     Layout.fillHeight: true
        // }
    }
}
