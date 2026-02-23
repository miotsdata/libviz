import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0
import "utils"

ApplicationWindow {
    id: addSpectraWindow
    visible: true
    width: 800
    height: 600
    minimumWidth: 800
    title: "Add spectra from mzML file"

    Pane {
        anchors.fill: parent
        padding: 10
        
        ColumnLayout {
            id: allCol
            anchors.fill: parent
            Layout.fillWidth: true

            ColumnLayout {
                id: filterByMzColLayout
                Layout.fillWidth: true
                    Text {
                            Layout.fillWidth: true
                            horizontalAlignment: Text.AlignHCenter
                            text: qsTr("Filter by m/z")

                            DebugRectangle {}
                        }
                    

                    RowLayout {
                        Layout.fillWidth: true
                        
                        TextField {
                            id: mzText
                            placeholderText: qsTr("Filter by m/z...")
                            Layout.preferredWidth: addSpectraWindow.width / 4
                            Layout.preferredHeight: 40

                            Keys.onEscapePressed: {
                                focus = false
                            }
                        }

                        Button {
                            text: qsTr("Filter")
                        }
                    }
            }

            ColumnLayout {
                id: filterByFormulaLayout
                Layout.fillWidth: true

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: qsTr("Filter by Molecular formula + Adduct")
                }

                RowLayout {
                    Layout.fillWidth: true
                    
                    TextField {
                        id: molecularFormulaText

                        placeholderText: qsTr("Molecular Formula...")
                        Layout.preferredWidth: addSpectraWindow.width / 4
                        Layout.preferredHeight: 40

                        Keys.onEscapePressed: {
                            focus = false
                        }
                    }

                    TextField {

                        placeholderText: qsTr("Mo capiamo come cazzo fare")
                        Layout.preferredWidth: addSpectraWindow.width / 4
                        Layout.preferredHeight: 40

                        Keys.onEscapePressed: {
                            focus = false
                        }
                    }

                    Button {
                        text: qsTr("Filter")
                    }
                }
            }

            Item {
                Layout.preferredHeight: addSpectraWindow.height / 2
                Layout.fillWidth: true
                
                Rectangle {
                    anchors.fill: parent
                    color: "blue"

                    Text {
                        anchors.centerIn: parent

                        text: "Tabella + plot"
                    }
                }
            }

        }
    }
}