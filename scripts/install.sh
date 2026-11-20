#!/bin/sh
# Downloads upstream Klippain Shake&Tune next to the plugin (README.md).
set -e
DIR="${OC_PLUGIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
REPO="${SHAKETUNE_REPO:-https://github.com/Frix-x/klippain-shaketune.git}"
BRANCH="${SHAKETUNE_BRANCH:-main}"
export PATH="$PATH:/opt/bin"
if ! command -v git >/dev/null 2>&1; then
    echo "git is needed (on OpenCreator printers: opkg install git)" >&2
    exit 1
fi
if [ -d "$DIR/upstream/.git" ]; then
    git -C "$DIR/upstream" fetch -q origin "$BRANCH"
    git -C "$DIR/upstream" reset -q --hard "origin/$BRANCH"
else
    rm -rf "$DIR/upstream"
    git clone -q --depth 50 --branch "$BRANCH" "$REPO" "$DIR/upstream"
fi
git -C "$DIR/upstream" fetch -q --tags --depth 50 origin 2>/dev/null || true
echo "Shake&Tune $(git -C "$DIR/upstream" describe --tags 2>/dev/null || git -C "$DIR/upstream" rev-parse --short HEAD)"
