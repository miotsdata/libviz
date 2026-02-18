import QtQuick 6.4
import QtQuick.Controls
import QtQuick.Layouts
import Metabolomics.Models 1.0

Page {
    id: testessdhfgaslhbmas
    anchors.fill: parent

    ColumnLayout{
        anchors.fill: parent

        RowLayout {
            height: window.height / 10
            Layout.fillWidth: true
            Text { text: "Library: " + libraryService.name }
            Text { text: "Compounds: " + libraryService.n_compounds }
            Text { text: "Spectra: " + libraryService.n_spectra }
        }

        RowLayout {

            Rectangle {
                width: window.width / 3
                Layout.fillHeight: true
                color: "blue"
            }

            ColumnLayout {
                Layout.fillWidth: true

                TextField {
                    placeholderText: "Filter by name..."
                    onTextChanged: CompoundTableModel.setFilter(text)
                }

                ListModel {
                    id: headerModel
                    ListElement { label: "ID"; column: 0 }
                    ListElement { label: "Name"; column: 1 }
                    ListElement { label: "Formula"; column: 2 }
                    ListElement { label: "Exact Mass"; column: 3 }
                }

                Row {
                    id: headerRow
                    Layout.fillWidth: true
                    height: 40

                    property int lastSortedColumn: -1
                    property bool ascending: true

                    Repeater {
                        model: headerModel

                        Rectangle {
                            width: table.columnWidthProvider(column) // ⭐ key line
                            height: 40
                            color: "#dddddd"
                            border.width: 1

                            required property string label
                            required property int column

                            Text {
                                anchors.fill: parent
                                anchors.margins: 6

                                text: label
                                font.bold: true
                                horizontalAlignment: Text.AlignLeft
                                verticalAlignment: Text.AlignVCenter

                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (headerRow.lastSortedColumn === column)
                                        headerRow.ascending = !headerRow.ascending
                                    else {
                                        headerRow.lastSortedColumn = column
                                        headerRow.ascending = true
                                    }

                                    CompoundTableModel.setSort(
                                                column,
                                                headerRow.ascending ? "asc" : "desc"
                                                )
                                }
                            }
                        }
                    }
                }

                TableView {
                    id: table
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    model: CompoundTableModel

                    clip: true

                    columnSpacing: 1
                    rowSpacing: 1

                    property int selectedRow
                    property int hoveredRow


                    selectionModel: ItemSelectionModel {
                    }

                    selectionBehavior: TableView.SelectRows
                    pointerNavigationEnabled: false

                    columnWidthProvider: function(column) {
                        if (column === 0) return 80
                        if (column === 3) return 120
                        if (column === 2) return 150

                        // Name column fills remaining width
                        var fixed = 80 + 150 + 120
                        return width - fixed
                    }

                    delegate: Rectangle {

                        id: cellRect
                        implicitWidth: 1
                        implicitHeight: 35
                        border.width: 0.5
                        clip: true

                        // Store row index
                        required property bool selected
                        required property bool current

                        // Background for hover
                        Rectangle {
                            anchors.fill: parent
                            color: table.selectedRow === row ? '#e0da20' : (table.hoveredRow === row ? '#a7a7a7' : "#ffffff")
                        }

                        HoverHandler {
                            id: hoverHandler

                            onHoveredChanged: {
                                table.hoveredRow = row
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                table.selectedRow = row
                                // model.id refers to the 'id' column of the compound
                                // var compound_id = CompoundTableModel.idForRow(table.currentRow)
                                // console.log("Clicked compound_id:", compound_id)
                                console.log("Clicked row:", row, "column:", column)
                                var compound_id = CompoundTableModel.idForRow(row)
                                console.log("Clicked compound_id:", compound_id)
                                SpectraTableModel.setFilter(compound_id)
                            }
                        }

                        Text {
                            id: cellText
                            anchors.fill: parent
                            anchors.margins: 6

                            text: model.display
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter

                            elide: Text.ElideRight
                            wrapMode: Text.NoWrap
                        }

                        // ToolTip {
                        //     visible: hoverHandler.hovered &&
                        //                 cellText.implicitWidth > cellText.width
                        //     text: display
                        // }
                    }

                    ScrollBar.vertical: ScrollBar {}

                }
            }
        }

        RowLayout {
            spacing: 10
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Text {
                    text: "Spectra for selected compound"
                    font.bold: true
                    anchors.leftMargin: 6
                }

                ListModel {
                    id: spectraHeaderModel
                    ListElement { label: "ID"; column: 0 }
                    ListElement { label: "Precursor m/z"; column: 1 }
                    ListElement { label: "Precursor Type"; column: 2 }
                    ListElement { label: "Polarity"; column: 3 }
                    ListElement { label: "Collision Energy"; column: 4 }
                    ListElement { label: "Added On"; column: 5 }
                }

                Row {
                    id: spectraHeaderRow
                    Layout.fillWidth: true
                    height: 40

                    property int lastSortedColumn: -1
                    property bool ascending: true

                    Repeater {
                        model: spectraHeaderModel

                        Rectangle {
                            width: spectraTable.columnWidthProvider(column)
                            height: 40
                            color: "#dddddd"
                            border.width: 1

                            required property string label
                            required property int column

                            Text {
                                anchors.fill: parent
                                anchors.margins: 6
                                text: label
                                font.bold: true
                                horizontalAlignment: Text.AlignLeft
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    if (spectraHeaderRow.lastSortedColumn === column)
                                        spectraHeaderRow.ascending = !spectraHeaderRow.ascending
                                    else {
                                        spectraHeaderRow.lastSortedColumn = column
                                        spectraHeaderRow.ascending = true
                                    }

                                    SpectraTableModel.setSort(
                                                column,
                                                spectraHeaderRow.ascending ? "asc" : "desc"
                                                )
                                }
                            }
                        }
                    }
                }

                TableView {
                    id: spectraTable
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    model: SpectraTableModel

                    clip: true

                    columnSpacing: 1
                    rowSpacing: 1

                    property int selectedRow
                    property int hoveredRow

                    columnWidthProvider: function(column) {
                        if (column === 0) return 0
                        if (column === 1) return 120
                        if (column === 2) return 150
                        if (column === 3) return 80
                        if (column === 4) return 120
                        if (column === 5) return 180
                        return 100
                    }

                    delegate: Rectangle {
                        implicitWidth: 1
                        implicitHeight: 35
                        border.width: 0.5
                        clip: true

                        // Store row index
                        required property bool selected
                        required property bool current

                        // Background for hover
                        Rectangle {
                            anchors.fill: parent
                            color: spectraTable.selectedRow === row ? '#e0da20' : (spectraTable.hoveredRow === row ? '#a7a7a7' : "#ffffff")
                        }

                        HoverHandler {
                            id: hoverHandlerSpectra

                            onHoveredChanged: {
                                spectraTable.hoveredRow = row
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                spectraTable.selectedRow = row
                                // model.id refers to the 'id' column of the compound
                                // var compound_id = CompoundTableModel.idForRow(table.currentRow)
                                // console.log("Clicked compound_id:", compound_id)
                                console.log("Clicked row:", row, "column:", column)
                                var spectra_id = SpectraTableModel.idForRow(row)
                                console.log("Clicked spectra_id:", spectra_id)
                                SpectrumPlotModel.setPeakId(spectra_id)
                            }
                        }

                        Text {
                            id: cellTextSpectra
                            anchors.fill: parent
                            anchors.margins: 6
                            text: model.display
                            horizontalAlignment: Text.AlignLeft
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            wrapMode: Text.NoWrap
                        }

                    }

                    ScrollBar.vertical: ScrollBar {}
                }
            }

            ColumnLayout {
                Layout.preferredWidth: window.height / 3
                Layout.fillHeight: true
                spacing: 10

                Label {
                    text: "MS/MS Spectrum"
                    font.bold: true
                }

                Item {
                    id: plotContainer
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    

                    Canvas {
                        id: canvas
                        anchors.fill: parent
                        property var model: SpectrumPlotModel

                        onModelChanged: canvas.requestPaint()

                        onPaint: {
                            const ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)

                            if (!model)
                                return

                            const peaks = model.peaks
                            if (!peaks || peaks.length === 0)
                                return

                            const minMz = model.minMz - 5
                            const maxMz = model.maxMz + 5

                            // ---- Define plotting rectangle ----
                            const marginLeft = 50
                            const marginRight = 20
                            const marginTop = 20
                            const marginBottom = 40

                            const plotX = marginLeft
                            const plotY = marginTop
                            const plotWidth = width - marginLeft - marginRight
                            const plotHeight = height - marginTop - marginBottom

                            if (plotWidth <= 0 || plotHeight <= 0)
                                return

                            // ---- Coordinate transforms ----
                            function xToPixel(mz) {
                                return plotX + ((mz - minMz) / (maxMz - minMz)) * plotWidth
                            }

                            function yToPixel(intensity) {
                                return plotY + plotHeight - (intensity / 100.0) * plotHeight
                            }

                            ctx.strokeStyle = "black"
                            ctx.fillStyle = "black"
                            ctx.lineWidth = 1

                            // ---- Draw axes ----
                            ctx.beginPath()
                            ctx.moveTo(plotX, plotY)
                            ctx.lineTo(plotX, plotY + plotHeight)
                            ctx.lineTo(plotX + plotWidth, plotY + plotHeight)
                            ctx.stroke()

                            // ---- Y ticks (0–100 every 20) ----
                            for (let y = 0; y <= 100; y += 20) {
                                const py = yToPixel(y)

                                ctx.beginPath()
                                ctx.moveTo(plotX - 5, py)
                                ctx.lineTo(plotX, py)
                                ctx.stroke()

                                ctx.fillText(y.toString(), plotX - 35, py + 4)
                            }

                            // ---- X ticks (5 total) ----
                            if (maxMz > minMz) {
                                const step = (maxMz - minMz) / 4.0

                                for (let i = 0; i < 5; i++) {
                                    const mzValue = minMz + i * step
                                    const px = xToPixel(mzValue)

                                    ctx.beginPath()
                                    ctx.moveTo(px, plotY + plotHeight)
                                    ctx.lineTo(px, plotY + plotHeight + 5)
                                    ctx.stroke()

                                    ctx.fillText(
                                                mzValue.toFixed(1),
                                                px - 20,
                                                plotY + plotHeight + 20
                                                )
                                }
                            }

                            ctx.lineWidth = 5;
                            // ---- Draw peaks (stick spectrum) ----
                            for (let i = 0; i < peaks.length; i++) {
                                const px = xToPixel(peaks[i].mz)
                                const py = yToPixel(peaks[i].intensity)

                                ctx.beginPath()
                                ctx.moveTo(px, plotY + plotHeight)
                                ctx.lineTo(px, py)
                                ctx.stroke()
                            }
                        }
                    }
                    Connections {
                        target: SpectrumPlotModel
                        function onDataChanged() {
                            canvas.requestPaint()
                        }
                    }
                }
            }
        }
    }
}
