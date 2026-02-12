TableView {
    id: table
    anchors.fill: parent
    clip: true

    // Only bind if model exists
    model: compoundModel !== undefined ? compoundModel : null
    visible: compoundModel !== undefined

    TableModelColumn {
        role: "Name"
        title: "Name"
        width: 200
    }
    TableModelColumn {
        role: "Formula"
        title: "Formula"
        width: 120
    }
    TableModelColumn {
        role: "InChIKey"
        title: "InChIKey"
        width: 180
    }
    TableModelColumn {
        role: "Exact Mass"
        title: "Exact Mass"
        width: 100
    }
    TableModelColumn {
        role: "Added On"
        title: "Added On"
        width: 150
    }

    headerVisible: true
    sortIndicatorVisible: true
}
