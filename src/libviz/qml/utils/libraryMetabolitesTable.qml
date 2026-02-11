TableView {
    id: table
    anchors.fill: parent
    clip: true

    // Only bind if model exists
    model: compoundModel !== undefined ? compoundModel : null
    visible: compoundModel !== undefined

    TableViewColumn {
        role: "Name"
        title: "Name"
        width: 200
    }
    TableViewColumn {
        role: "Formula"
        title: "Formula"
        width: 120
    }
    TableViewColumn {
        role: "InChIKey"
        title: "InChIKey"
        width: 180
    }
    TableViewColumn {
        role: "Exact Mass"
        title: "Exact Mass"
        width: 100
    }
    TableViewColumn {
        role: "Added On"
        title: "Added On"
        width: 150
    }

    headerVisible: true
    sortIndicatorVisible: true
}
