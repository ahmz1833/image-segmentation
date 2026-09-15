#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ARCHIVE="${1:-$SCRIPT_DIR/final.tar.zst}"
DEST="${2:-$SCRIPT_DIR/arm-only}"

echo "=================================================="
echo "ARM Architecture Sample Extractor for final.tar.zst"
echo "=================================================="
echo "Archive: $ARCHIVE"
echo "Destination: $DEST"

if [[ ! -f "$ARCHIVE" ]]; then
    echo "ERROR: Archive not found at: $ARCHIVE" >&2
    exit 1
fi

mkdir -p "$DEST"

for cmd in zstd tar; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: Required command not found: $cmd" >&2
        exit 1
    fi
done

echo "Starting extraction of ARM members directly from archive..."
if command -v pv &>/dev/null; then
    pv -ptebar "$ARCHIVE" | zstd -dc | tar --extract --file=- --directory="$DEST" --wildcards './*/arm/*' --no-same-owner
else
    zstd -dc "$ARCHIVE" | tar --extract --file=- --directory="$DEST" --wildcards './*/arm/*' --no-same-owner
fi

echo "Extraction complete! Files are available in: $DEST"
