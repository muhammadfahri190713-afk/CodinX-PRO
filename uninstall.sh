#!/usr/bin/env bash
set -e
if [ -n "${CODINX_INSTALL_DIR:-}" ]; then
  DEST="$CODINX_INSTALL_DIR"
elif [ "$(id -u)" = "0" ]; then
  DEST=/opt/codinx
else
  DEST="${PREFIX:-$HOME/.local}/share/codinx"
fi
if [ -n "${CODINX_BIN_DIR:-}" ]; then
  BIN_DIR="$CODINX_BIN_DIR"
elif [ "$(id -u)" = "0" ]; then
  BIN_DIR=/usr/local/bin
else
  BIN_DIR="${PREFIX:-$HOME/.local}/bin"
fi
rm -f "$BIN_DIR/codinx"
rm -rf "$DEST"
echo "CodinX dihapus dari $DEST. Data sesi dan kunci di ~/.codinx dipertahankan."
