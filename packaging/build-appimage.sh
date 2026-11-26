#!/bin/sh
set -eu
project=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
appdir="$project/build/RustTutor.AppDir"
destination="$appdir/usr/share/rust-tutor"
version=$(/usr/bin/python3 "$project/main.py" --version)
icon="/usr/share/icons/Yaru/256x256/apps/accessories-text-editor.png"

if [ ! -f "$icon" ]; then
    icon="/usr/share/icons/HighContrast/256x256/apps/accessories-text-editor.png"
fi
if [ ! -f "$icon" ]; then
    printf '%s\n' "A stock editor icon from Ubuntu's Yaru or HighContrast theme is required." >&2
    exit 1
fi

install -d "$destination/rust_tutor" "$appdir/usr/bin"
install -m 755 "$project/packaging/AppRun" "$appdir/AppRun"
ln -sfn ../../AppRun "$appdir/usr/bin/rust-tutor"
install -m 644 "$project/packaging/local.rusttutor.Learn.desktop" "$appdir/local.rusttutor.Learn.desktop"
printf 'X-AppImage-Version=%s\n' "$version" >> "$appdir/local.rusttutor.Learn.desktop"
install -m 644 "$icon" "$appdir/accessories-text-editor.png"
install -m 644 "$project/main.py" "$destination/main.py"
install -m 644 "$project/rust_tutor/"*.py "$destination/rust_tutor/"
if [ -f /usr/share/doc/yaru-theme-icon/copyright ] && [ "${icon#*/Yaru/}" != "$icon" ]; then
    install -m 644 /usr/share/doc/yaru-theme-icon/copyright "$destination/icon-copyright.txt"
fi

if [ "${1:-}" = "--appdir-only" ]; then
    printf '%s\n' "$appdir"
    exit 0
fi
tool=${APPIMAGETOOL:-appimagetool}
if ! command -v "$tool" >/dev/null 2>&1; then
    printf '%s\n' 'AppDir is staged. Set APPIMAGETOOL to a downloaded executable or put appimagetool on PATH.' >&2
    exit 1
fi
architecture=$(uname -m)
ARCH="$architecture" "$tool" "$appdir" "$project/build/RustTutor-v$version-$architecture.AppImage"
