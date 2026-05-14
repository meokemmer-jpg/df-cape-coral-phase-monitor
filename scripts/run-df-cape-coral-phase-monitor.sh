#!/bin/bash
# DF-CAPE-CORAL-PHASE-MONITOR Wrapper [CRUX-MK]
# K16 Mutex + K_0-Sperr-Liste P6 Item-3 (Cape-Coral-Pacing)

set -e

LOCK_DIR="/tmp/df-cape-coral-phase-monitor.lock"
LOCK_AGE_LIMIT_S=21600
DF_DIR="/Users/make/Projects/dark-factories/df-cape-coral-phase-monitor"

if [ -d "$LOCK_DIR" ]; then
  LOCK_AGE_S=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
  [ "$LOCK_AGE_S" -gt "$LOCK_AGE_LIMIT_S" ] && rm -rf "$LOCK_DIR"
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[K16] Lock vorhanden – Spawn abgebrochen" >&2
  exit 3
fi
echo "$$" > "$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

if [ -f "/tmp/df-cape-coral-phase-monitor.stop" ]; then
  echo "[STOP.flag] Aktiv – Run abgebrochen" >&2
  exit 0
fi

cd "$DF_DIR"
exec /usr/bin/env python3 -m src.engine
