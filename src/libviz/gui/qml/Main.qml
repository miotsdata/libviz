import QtCore
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "Style"
import "Views"

ApplicationWindow {
    id: window
    objectName: "mainWindow"
    visible: true
    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    title: Libraries.selected.name ? Libraries.selected.name + " — LibViz" : "LibViz"
    color: palette.window

    // Explicit palette, every role from Theme (otherwise Fusion inherits the
    // desktop's, possibly dark, palette — see MSIAnalyzer ADR 15).
    palette {
        window: Theme.backgroundColor
        windowText: Theme.textColor
        base: Theme.fieldColor
        alternateBase: Theme.secondaryColor
        text: Theme.textColor
        button: Theme.controlColor
        buttonText: Theme.textColor
        toolTipBase: Theme.controlColor
        toolTipText: Theme.textColor
        placeholderText: Theme.placeholderTextColor
        highlight: Theme.primaryColor
        highlightedText: Theme.highlightedTextColor
        light: Theme.lightColor
        midlight: Theme.midlightColor
        mid: Theme.borderColor
        dark: Theme.darkColor
        shadow: Theme.shadowColor
        disabled.windowText: Theme.disabledTextColor
        disabled.buttonText: Theme.disabledTextColor
        disabled.text: Theme.disabledTextColor
    }

    Settings {
        id: settings
        category: "ui"
        property bool isDark: true
        property var recentLibraries: []
        property alias windowWidth: window.width
        property alias windowHeight: window.height
    }
    Component.onCompleted: Theme.isDark = settings.isDark

    readonly property bool hasSelection: Libraries.selectedKey !== ""
    // "" = the selected library (or welcome), "builder", "search"
    property string page: ""
    // "New library…" from the builder's commit dialog: commit once it's created.
    property bool commitAfterCreate: false
    // Pages call these to drive the shared dialogs.
    function openLibraryDialog() { openDbDialog.open() }
    function importMspDialog() { mspDialog.open() }
    function newLibraryDialog() { newDbDialog.open() }
    function openBuilder() { page = "builder" }

    function addRecent(path) {
        var list = settings.recentLibraries.filter(function (p) { return p !== path })
        list.unshift(path)
        settings.recentLibraries = list.slice(0, 10)
    }
    function removeRecent(path) {
        settings.recentLibraries = settings.recentLibraries.filter(function (p) { return p !== path })
    }
    function openRecent(path) {
        if (!Libraries.fileExists(path)) {
            removeRecent(path)
            showError(path + " no longer exists.")
            return
        }
        Libraries.openLibrary(path)
    }
    function showInfo(message, details) {
        infoDialog.text = message
        infoDialog.detailedText = details || ""  // "Show Details…" only when set
        infoDialog.open()
    }
    function showError(message) {
        errorDialog.text = message
        errorDialog.open()
    }

    // =========================
    // MENU BAR
    // =========================
    menuBar: MenuBar {
        Menu {
            title: qsTr("&File")
            Action { text: qsTr("&New library…"); shortcut: StandardKey.New; enabled: !Libraries.busy; onTriggered: newDbDialog.open() }
            Action { text: qsTr("&Open library…"); shortcut: StandardKey.Open; enabled: !Libraries.busy; onTriggered: openDbDialog.open() }
            Action { text: qsTr("&Import MSP…"); shortcut: "Ctrl+I"; enabled: !Libraries.busy; onTriggered: mspDialog.open() }
            Menu {
                id: recentMenu
                title: qsTr("Open &recent")
                enabled: settings.recentLibraries.length > 0
                Instantiator {
                    model: settings.recentLibraries
                    delegate: MenuItem {
                        required property string modelData
                        text: modelData
                        onTriggered: window.openRecent(modelData)
                    }
                    onObjectAdded: (index, object) => recentMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => recentMenu.removeItem(object)
                }
            }
            MenuSeparator {}
            Action { text: qsTr("&Save as…"); shortcut: StandardKey.SaveAs; enabled: window.hasSelection && !Libraries.busy; onTriggered: saveAsDialog.open() }
            Action { text: qsTr("&Export as MSP…"); shortcut: "Ctrl+E"; enabled: window.hasSelection && !Libraries.busy; onTriggered: exportMspDialog.open() }
            Action { text: qsTr("&Close library"); shortcut: StandardKey.Close; enabled: window.hasSelection && !Libraries.busy; onTriggered: window.requestClose(Libraries.selectedKey) }
            MenuSeparator {}
            Action { text: qsTr("&Quit"); shortcut: StandardKey.Quit; onTriggered: window.close() }
        }
        Menu {
            title: qsTr("&Library")
            Action { text: qsTr("&Build from mzML…"); shortcut: "Ctrl+B"; onTriggered: window.openBuilder() }
            Action { text: qsTr("&Spectral search…"); shortcut: "Ctrl+F"; onTriggered: window.page = "search" }
            MenuSeparator {}
            Action { text: qsTr("&Rename…"); enabled: window.hasSelection && !Libraries.busy; onTriggered: renameDialog.openWith(Libraries.selected.name) }
            Action { text: qsTr("Import &compounds (Excel/CSV)…"); enabled: window.hasSelection && !Libraries.busy; onTriggered: importCompoundsDialog.openForSelected() }
            Action { text: qsTr("&Merge another library into this…"); enabled: window.hasSelection && !Libraries.busy; onTriggered: mergeDialog.open() }
        }
        Menu {
            title: qsTr("&View")
            Action { text: qsTr("&Dark theme"); checkable: true; checked: Theme.isDark; onTriggered: { Theme.isDark = checked; settings.isDark = checked } }
        }
        Menu {
            title: qsTr("&Help")
            Action { text: qsTr("&About LibViz"); onTriggered: aboutDialog.open() }
        }
    }

    // =========================
    // MAIN CONTENT
    // =========================
    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        LibrariesPanel {
            SplitView.preferredWidth: 240
            SplitView.minimumWidth: 180
            onCloseRequested: key => window.requestClose(key)
        }

        Loader {
            id: contentLoader
            SplitView.fillWidth: true
            sourceComponent: window.page === "builder" ? builderPage : window.page === "search" ? searchPage
                           : window.hasSelection ? libraryPage : welcomePage
        }
    }

    Component {
        id: searchPage
        SearchPage {
            onCloseRequested: window.page = ""
            onOpenHit: (path, compoundId) => { window.page = ""; Libraries.selectLibrary(path); Inspector.selectCompound(compoundId) }
        }
    }

    // The builder keeps its state while hidden (it lives in the bridge).
    Component {
        id: builderPage
        BuilderPage {
            onCloseRequested: window.page = ""
            onNewLibraryRequested: { window.commitAfterCreate = true; newDbDialog.open() }
        }
    }

    Component { id: welcomePage; WelcomePage { recentLibraries: settings.recentLibraries; onOpenRecent: path => window.openRecent(path) } }
    Component { id: libraryPage; LibraryPage {} }

    // =========================
    // STATUS BAR
    // =========================
    footer: ToolBar {
        objectName: "statusBar"
        height: 26
        background: Rectangle { color: Theme.secondaryColor; Rectangle { width: parent.width; height: 1; color: Theme.borderColor } }
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 10
            Label {
                Layout.fillWidth: true
                elide: Text.ElideMiddle
                font.pixelSize: Theme.captionPixelSize
                color: Theme.mutedTextColor
                text: Libraries.busy ? Libraries.statusText + "…"
                     : !window.hasSelection ? qsTr("Ready")
                     : Libraries.selected.isTemp ? qsTr("Imported, not saved yet")
                     : Libraries.selected.path
            }
            ProgressBar {
                visible: Libraries.busy
                Layout.preferredWidth: 200
                indeterminate: Libraries.progress < 0
                value: Math.max(0, Libraries.progress)
            }
        }
    }

    Connections {
        target: Inspector
        function onErrorOccurred(message) { window.showError(message) }
    }
    Connections {
        target: Search
        function onErrorOccurred(message) { window.showError(message) }
    }
    Connections {
        target: CompoundImport
        function onErrorOccurred(message) { window.showError(message) }
        function onImported(key, message, details) {
            window.page = ""
            Libraries.selectLibrary(key)
            window.showInfo(message, details)
        }
    }
    Connections {
        target: Builder
        function onErrorOccurred(message) { window.showError(message) }
        function onCommitted(key, message) {
            window.page = ""
            Libraries.selectLibrary(key)
            window.showInfo(message, "")
        }
    }
    Connections {
        target: Libraries
        function onLibraryOpened(key) {
            if (window.commitAfterCreate && window.page === "builder" && contentLoader.item)
                contentLoader.item.commitTo(key)
            window.commitAfterCreate = false
        }
        function onErrorOccurred(message) { window.showError(message); window.commitAfterCreate = false }
        function onInfoMessage(message) { window.showInfo(message, "") }
        function onSelectedChanged() {
            if (window.hasSelection && !Libraries.selected.isTemp && Libraries.selected.path)
                window.addRecent(Libraries.selected.path)
        }
    }

    // =========================
    // CLOSE / QUIT CONFIRMATION
    // =========================
    function requestClose(key) {
        var info = Libraries.libraries.find(function (l) { return l.key === key })
        if (info && info.isTemp) {
            discardDialog.key = key
            discardDialog.open()
        } else {
            Libraries.closeLibrary(key)
        }
    }

    property bool quitConfirmed: false
    onClosing: close => {
        if (!quitConfirmed && (Libraries.hasUnsaved || Libraries.busy)) {
            close.accepted = false
            quitDialog.open()
        }
    }

    MessageDialog {
        id: discardDialog
        property string key
        title: qsTr("Discard unsaved library?")
        text: qsTr("This imported library has not been saved. Close it and discard its contents?")
        buttons: MessageDialog.Discard | MessageDialog.Cancel
        onButtonClicked: (button, role) => { if (button === MessageDialog.Discard) Libraries.closeLibrary(key) }
    }
    MessageDialog {
        id: quitDialog
        title: qsTr("Quit LibViz?")
        text: Libraries.busy ? qsTr("A task is still running and will be aborted.")
                             : qsTr("Some imported libraries have not been saved and will be discarded.")
        buttons: MessageDialog.Discard | MessageDialog.Cancel
        onButtonClicked: (button, role) => { if (button === MessageDialog.Discard) { window.quitConfirmed = true; window.close() } }
    }

    // =========================
    // DIALOGS
    // =========================
    FileDialog {
        id: openDbDialog
        title: qsTr("Open library")
        nameFilters: [qsTr("LibViz libraries (*.db)"), qsTr("All files (*)")]
        onAccepted: Libraries.openLibrary(selectedFile)
    }
    FileDialog {
        id: mspDialog
        title: qsTr("Import MSP file")
        nameFilters: [qsTr("MSP files (*.msp *.MSP)"), qsTr("All files (*)")]
        onAccepted: Libraries.importMsp(selectedFile)
    }
    FileDialog {
        id: newDbDialog
        title: qsTr("New library")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "db"
        nameFilters: [qsTr("LibViz libraries (*.db)")]
        onAccepted: Libraries.createLibrary(selectedFile, "")
        onRejected: window.commitAfterCreate = false
    }
    FileDialog {
        id: saveAsDialog
        title: qsTr("Save library as")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "db"
        nameFilters: [qsTr("LibViz libraries (*.db)")]
        onAccepted: Libraries.saveSelectedAs(selectedFile)
    }

    FileDialog {
        id: exportMspDialog
        title: qsTr("Export library as MSP")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "msp"
        nameFilters: [qsTr("MSP files (*.msp)")]
        onAccepted: Libraries.exportSelectedMsp(selectedFile)
    }
    FileDialog {
        id: mergeDialog
        title: qsTr("Merge library into “%1”").arg(Libraries.selected.name || "")
        nameFilters: [qsTr("LibViz libraries (*.db)"), qsTr("All files (*)")]
        onAccepted: { mergeConfirm.source = selectedFile; mergeConfirm.open() }
    }
    MessageDialog {
        id: mergeConfirm
        property string source
        title: qsTr("Merge libraries")
        text: qsTr("Copy all compounds and spectra of %1 into “%2”? Identical spectra are skipped.")
              .arg(Libraries.toLocalPath(source)).arg(Libraries.selected.name || "")
        informativeText: Libraries.selected.isTemp ? "" : qsTr("The library file is changed directly.")
        buttons: MessageDialog.Ok | MessageDialog.Cancel
        onButtonClicked: (button, role) => { if (button === MessageDialog.Ok) Libraries.mergeIntoSelected(source) }
    }

    ImportCompoundsDialog { id: importCompoundsDialog }

    Dialog {
        id: renameDialog
        title: qsTr("Rename library")
        anchors.centerIn: parent
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        function openWith(name) { nameField.text = name; open(); nameField.selectAll(); nameField.forceActiveFocus() }
        TextField { id: nameField; implicitWidth: 320; onAccepted: renameDialog.accept() }
        onAccepted: Libraries.renameSelected(nameField.text)
    }

    MessageDialog {
        id: infoDialog
        title: qsTr("LibViz")
        buttons: MessageDialog.Ok
    }

    MessageDialog {
        id: errorDialog
        title: qsTr("Error")
        buttons: MessageDialog.Ok
    }

    MessageDialog {
        id: aboutDialog
        title: qsTr("About LibViz")
        text: "LibViz " + AppVersion
        informativeText: qsTr("Build, inspect and curate MS/MS spectral libraries.")
        buttons: MessageDialog.Ok
    }
}
