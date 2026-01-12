#!/bin/bash

export DISPLAY=:0

LOG="/home/pi/logs/magnolia.log"
PY="/home/pi/MagnoliaPackages/bin/python3.11"
APP="/home/pi/magnolia-active/App/main.py"

mkdir -p /home/pi/logs

while true
do
  echo "$(date) Starting Magnolia UI" >> "$LOG"
  "$PY" "$APP" >> "$LOG" 2>&1
  echo "$(date) Magnolia UI exited, restarting..." >> "$LOG"
  sleep 2
done
