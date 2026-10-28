#!/bin/bash
# packaging/appimage/build.sh — builds the Linux standalone AppImage.
#
# Run from the repo root: packaging/appimage/build.sh
# Output: dist/LibViz-x86_64.AppImage
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

TOOLS_DIR="packaging/.tools"
APPIMAGETOOL="${TOOLS_DIR}/appimagetool-x86_64.AppImage"
APPDIR="packaging/appimage/AppDir"

mkdir -p "${TOOLS_DIR}"
if [ ! -x "${APPIMAGETOOL}" ]; then
    echo "Fetching appimagetool..."
    curl -sL -o "${APPIMAGETOOL}" \
        https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "${APPIMAGETOOL}"
fi

echo "Running PyInstaller..."
pdm run pyinstaller packaging/pyinstaller/libviz-gui.spec --noconfirm

echo "Assembling AppDir..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/opt"
cp -r dist/libviz-gui "${APPDIR}/usr/opt/libviz-gui"
install -m 755 packaging/appimage/AppRun "${APPDIR}/AppRun"
install -m 644 packaging/appimage/libviz.desktop "${APPDIR}/libviz.desktop"
install -m 644 packaging/appimage/libviz-placeholder-icon.png "${APPDIR}/libviz.png"

echo "Running appimagetool..."
# --appimage-extract-and-run: appimagetool is itself an AppImage and would
# need FUSE to mount, which containers/sandboxes may not have.
ARCH=x86_64 "${APPIMAGETOOL}" --appimage-extract-and-run "${APPDIR}" dist/LibViz-x86_64.AppImage

echo "Built dist/LibViz-x86_64.AppImage"
