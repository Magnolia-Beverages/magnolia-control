#!/bin/bash

BASE="/home/pi"
PYTHON="$BASE/MagnoliaPackages/bin/python3.11"
ACTIVE="$BASE/magnolia-active"
LOG="$BASE/logs/magnolia.log"

while true
do
  if [ -L "$ACTIVE" ]; then
    APP_DIR=$(readlink -f "$ACTIVE")
    if [ -f "$APP_DIR/App/main.py" ]; then
      echo "$(date '+%Y-%m-%d %H:%M:%S') Starting UI" >> "$LOG"
      "$PYTHON" "$APP_DIR/App/main.py" >> "$LOG" 2>&1
    fi
  fi
  sleep 2
done
