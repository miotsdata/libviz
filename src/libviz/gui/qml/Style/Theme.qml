pragma Singleton
import QtQuick

// Design tokens — the single source of truth for colors and type scale
// (same scheme as MSIAnalyzer). Main.qml's `palette` reads from here, so
// flipping `isDark` re-themes the whole app live. Persisted by Main.qml.
QtObject {
    property bool isDark: true

    // Surfaces
    readonly property color backgroundColor: isDark ? "#2d2d30" : "#f2f2f5"
    readonly property color secondaryColor: isDark ? "#323234" : "#ffffff"
    readonly property color fieldColor: isDark ? "#252526" : "#e9e9ed"
    readonly property color controlColor: isDark ? "#3c3c3c" : "#e4e4e8"

    // Text
    readonly property color textColor: isDark ? "#e0e0e0" : "#202020"
    readonly property color highlightedTextColor: "#ffffff"
    readonly property color placeholderTextColor: isDark ? "#8a8a8a" : "#767676"
    readonly property color mutedTextColor: isDark ? "#9a9a9a" : "#5a5a5a"
    readonly property color disabledTextColor: isDark ? "#6a6a6a" : "#a8a8a8"
    readonly property color errorColor: isDark ? "#e06c75" : "#c0392b"
    readonly property color warningColor: isDark ? "#e5c07b" : "#9a6700"
    readonly property color successColor: isDark ? "#98c379" : "#2e7d32"

    // Accent / lines
    readonly property color primaryColor: isDark ? "#3d8bd4" : "#2f6fb3"
    readonly property color borderColor: isDark ? "#48484c" : "#c8c8ce"
    readonly property color lightColor: isDark ? "#4a4a4a" : "#ffffff"
    readonly property color midlightColor: isDark ? "#414141" : "#e0e0e6"
    readonly property color darkColor: isDark ? "#1e1e1e" : "#a0a0a8"
    readonly property color shadowColor: "#000000"

    // Plots follow the theme (Qt Graphs, no WebEngine).
    readonly property color plotBackgroundColor: isDark ? "#252526" : "#ffffff"
    readonly property color plotGridColor: isDark ? "#3a3a3d" : "#e5e5e5"
    readonly property color plotTextColor: textColor
    readonly property color plotAccentColor: isDark ? "#5aa9e6" : "#1f77b4"
    readonly property color plotSecondColor: isDark ? "#e5a35a" : "#d62728"
    readonly property color plotMutedColor: isDark ? "#7a7a7a" : "#9a9a9a"

    // Type / spacing
    readonly property int headingPixelSize: 18
    readonly property int captionPixelSize: 11
    readonly property int spacing: 8
}
