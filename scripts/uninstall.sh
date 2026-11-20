#!/bin/sh
DIR="${OC_PLUGIN_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
rm -rf "$DIR/upstream"
