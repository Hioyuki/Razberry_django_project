#!/usr/bin/env bash
set -euo pipefail

# Raspberry Pi camera test (CLI only).
# Usage:
#   ./rpi_camera_test.sh
#   ./rpi_camera_test.sh output.jpg 2000

OUTPUT_FILE="${1:-rpi_camera_test.jpg}"
TIMEOUT_MS="${2:-1500}"

echo "Capturing with rpicam-still..."
echo "output=${OUTPUT_FILE}, timeout_ms=${TIMEOUT_MS}"

rpicam-still \
  --timeout "${TIMEOUT_MS}" \
  --nopreview \
  --output "${OUTPUT_FILE}"

echo "OK: saved ${OUTPUT_FILE}"
