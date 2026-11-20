#!/bin/sh
# Installs numpy-shaketune on any Klipper/Kalico printer (README.md).
# Usage: ./install.sh [--klipper DIR] [--config DIR] [--no-restart] [--uninstall]
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
KLIPPER="" CONFIG="" RESTART=1 UNINSTALL=0
while [ $# -gt 0 ]; do
    case "$1" in
        --klipper) KLIPPER="$2"; shift 2 ;;
        --config) CONFIG="$2"; shift 2 ;;
        --no-restart) RESTART=0; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        -h|--help) sed -n 3p "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done
first() { for d in "$@"; do [ -d "$d" ] && { echo "$d"; return; }; done; }
[ -n "$KLIPPER" ] || KLIPPER="$(first "$HOME/klipper" "$HOME/kalico" /usr/data/opencreator/klipper/klipper /usr/share/klipper /usr/data/klipper)"
[ -n "$CONFIG" ] || CONFIG="$(first "$HOME/printer_data/config" /usr/data/opencreator/klipper/config /usr/data/printer_data/config "$HOME/klipper_config")"
[ -d "$KLIPPER/klippy" ] || { echo "Klipper not found, use --klipper DIR" >&2; exit 1; }
[ -f "$CONFIG/printer.cfg" ] || { echo "printer.cfg not found, use --config DIR" >&2; exit 1; }
if [ -d "$KLIPPER/klippy/plugins" ]; then MODDIR="$KLIPPER/klippy/plugins"; else MODDIR="$KLIPPER/klippy/extras"; fi
LINK="$MODDIR/shaketune.py"
REL="${MODDIR#"$KLIPPER"/}/shaketune.py"
EXCLUDE="$KLIPPER/.git/info/exclude"

restart() {
    [ "$RESTART" = 1 ] || return 0
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^klipper\.service'; then
        echo "Restarting Klipper"; systemctl restart klipper 2>/dev/null || sudo systemctl restart klipper
    elif [ -x /etc/init.d/S55klipper_service ]; then
        echo "Restarting Klipper"; /etc/init.d/S55klipper_service restart
    else
        echo "Restart Klipper to load Shake&Tune"
    fi
}

if [ "$UNINSTALL" = 1 ]; then
    rm -f "$LINK"
    [ -f "$EXCLUDE" ] && sed -i "\|^$REL\$|d" "$EXCLUDE"
    sed -i '/^\[include shaketune\.cfg\]$/d' "$CONFIG/printer.cfg"
    rm -rf "$DIR/upstream"
    echo "Removed. $CONFIG/shaketune.cfg and the ShakeTune_results folder were kept."
    restart
    exit 0
fi

sh "$DIR/scripts/install.sh"
ln -sfn "$DIR/shaketune.py" "$LINK"
if [ -d "$KLIPPER/.git" ] && ! grep -qxF "$REL" "$EXCLUDE" 2>/dev/null; then
    echo "$REL" >> "$EXCLUDE"
fi
[ -f "$CONFIG/shaketune.cfg" ] || cp "$DIR/shaketune.cfg" "$CONFIG/shaketune.cfg"
if ! grep -q '^\[include shaketune\.cfg\]' "$CONFIG/printer.cfg"; then
    cp "$CONFIG/printer.cfg" "$CONFIG/printer.cfg.before-shaketune"
    if grep -q '^#\*# <-* SAVE_CONFIG' "$CONFIG/printer.cfg"; then
        sed -i '0,/^#\*# <-* SAVE_CONFIG/s//[include shaketune.cfg]\n\n&/' "$CONFIG/printer.cfg"
    else
        printf '\n[include shaketune.cfg]\n' >> "$CONFIG/printer.cfg"
    fi
    echo "Added [include shaketune.cfg] to printer.cfg (backup: printer.cfg.before-shaketune)"
fi
echo "Linked $LINK (numpy-shaketune $(cat "$DIR/VERSION" 2>/dev/null))"
restart
