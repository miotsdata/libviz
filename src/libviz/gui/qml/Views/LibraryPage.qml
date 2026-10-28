import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../Style"

// The selected library's inspector: filters, compound table, spectrum panel.
Item {
    id: page
    readonly property var info: Libraries.selected
    readonly property var options: Inspector.filterOptions

    function applyFilters() {
        Inspector.setFilters(searchField.text, massField.text, ppmField.text,
                             polarityBox.currentIndex > 0 ? polarityBox.currentText : "",
                             adductBox.currentIndex > 0 ? adductBox.currentText : "",
                             ceBox.currentIndex > 0 ? ceBox.currentText : "")
    }
    function clearFilters() {
        searchField.text = ""; massField.text = ""
        polarityBox.currentIndex = 0; adductBox.currentIndex = 0; ceBox.currentIndex = 0
        applyFilters()
    }
    // A different library: its filters start empty (the model already cleared them).
    Connections {
        target: Libraries
        function onSelectedChanged() {
            searchField.text = ""; massField.text = ""
            polarityBox.currentIndex = 0; adductBox.currentIndex = 0; ceBox.currentIndex = 0
            debounce.stop()
        }
    }
    Timer { id: debounce; interval: 300; onTriggered: page.applyFilters() }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // --- header ---
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 10
            Label { text: page.info.name || ""; font.pixelSize: Theme.headingPixelSize; font.bold: true; elide: Text.ElideRight; Layout.maximumWidth: 400 }
            Label {
                visible: page.info.isTemp === true
                text: qsTr("unsaved — File › Save as… to keep it")
                color: Theme.warningColor
            }
            Item { Layout.fillWidth: true }
            Label {
                text: qsTr("%1 compounds · %2 spectra")
                      .arg((page.info.nCompounds || 0).toLocaleString(Qt.locale(), "f", 0))
                      .arg((page.info.nSpectra || 0).toLocaleString(Qt.locale(), "f", 0))
                color: Theme.mutedTextColor
            }
        }

        // --- filter bar ---
        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 10
            Layout.rightMargin: 10
            Layout.bottomMargin: 8
            spacing: 6
            TextField {
                id: searchField
                objectName: "searchField"
                Layout.fillWidth: true
                Layout.minimumWidth: 160
                placeholderText: qsTr("Search name, formula or InChIKey")
                selectByMouse: true
                onTextEdited: debounce.restart()
            }
            TextField {
                id: massField
                Layout.preferredWidth: 110
                placeholderText: qsTr("Mass or m/z")
                validator: RegularExpressionValidator { regularExpression: /^\d*[.,]?\d*$/ }
                onTextEdited: debounce.restart()
                ToolTip.visible: hovered
                ToolTip.delay: 600
                ToolTip.text: qsTr("Matches the neutral exact mass or any precursor m/z")
            }
            TextField {
                id: ppmField
                Layout.preferredWidth: 50
                text: "10"
                validator: RegularExpressionValidator { regularExpression: /^\d*[.,]?\d*$/ }
                onTextEdited: debounce.restart()
            }
            Label { text: qsTr("ppm"); color: Theme.mutedTextColor }
            ComboBox {
                id: polarityBox
                Layout.preferredWidth: 120
                model: [qsTr("Any polarity")].concat(page.options.polarities || [])
                onActivated: page.applyFilters()
            }
            ComboBox {
                id: adductBox
                Layout.preferredWidth: 130
                model: [qsTr("Any adduct")].concat(page.options.adducts || [])
                onActivated: page.applyFilters()
            }
            ComboBox {
                id: ceBox
                Layout.preferredWidth: 100
                model: [qsTr("Any CE")].concat(page.options.collision_energies || [])
                onActivated: page.applyFilters()
            }
            ToolButton { text: qsTr("Clear"); onClicked: page.clearFilters() }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.borderColor }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal

            CompoundTable {
                SplitView.preferredWidth: page.width * 0.45
                SplitView.minimumWidth: 300
            }
            SpectrumPanel {
                SplitView.fillWidth: true
                SplitView.minimumWidth: 320
            }
        }
    }
}
