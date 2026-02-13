import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0
//import "utils"

Page {
    id: libraryPage

    property var headers: [
        { title: "Name", role: "name", width: 180 },
        { title: "Formula", role: "formula", width: 120 },
        { title: "InChIKey", role: "inchikey", width: 240 },
        { title: "Exact Mass", role: "exact_mass", width: 120 },
        { title: "Added On", role: "added_on", width: 180 }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // --- Info ---
        Text { text: "Library: " + libraryService.name }
        Text { text: "Compounds: " + libraryService.n_compounds }
        Text { text: "Spectra: " + libraryService.n_spectra }

        // --- Header ---
        RowLayout {
            height: 20
            spacing: 0

            Repeater {
                model: headers

                Rectangle {
                    Layout.preferredWidth: modelData.width
                    Layout.fillHeight: false
                    color: "#e8eaf0"
                    border.color: "#c5c9d3"

                    Text {
                        anchors.centerIn: parent
                        text: modelData.title
                        font.bold: true
                    }
                }
            }
        }

        // --- Table ---
        TableView {
            Layout.fillWidth: true
            Layout.preferredHeight: 36 * 5
            clip: true

            model: CompoundTableModel

            delegate: Rectangle {
                implicitWidth: headers[column].width
                implicitHeight: 36

                color: row % 2 === 0 ? "#ffffff" : "#f7f9fc"
                border.color: "#e0e4ec"

                property string roleName: headers[column].role

                Text {
                    anchors.fill: parent
                    anchors.margins: 8
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    text: model[roleName] || ""
                }
            }

            ScrollBar.vertical: ScrollBar {}
        }

        Item {
            Layout.fillHeight: true
        }

        
    }
}
