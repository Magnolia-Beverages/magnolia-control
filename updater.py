#!/home/pi/MagnoliaPackages/bin/python3.11

import json
import os
import subprocess
from datetime import datetime

BASE = "/home/pi"
CONTROL = f"{BASE}/magnolia-control"
APPS = f"{BASE}/magnolia-apps"
ACTIVE = f"{BASE}/magnolia-active"
OVERRIDE = f"{BASE}/magnolia-local/override.conf"
LOG = f"{BASE}/logs/magnolia.log"
MID_FILE = "/etc/magnolia_id"

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")

def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

log("Updater started")

# local override
if os.path.exists(OVERRIDE) and os.path.getsize(OVERRIDE) > 0:
    log("Local override active")
    exit(0)

if not os.path.exists(MID_FILE):
    log("Machine ID missing")
    exit(1)

machine_id = open(MID_FILE).read().strip()

run(["git", "pull"], cwd=CONTROL)

apps = json.load(open(f"{CONTROL}/apps.json"))

cfg_path = f"{CONTROL}/machines/{machine_id}.json"
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else json.load(open(f"{CONTROL}/default.json"))

app = cfg["app"]
repo = apps[app]["repo"]

app_dir = f"{APPS}/{app}"

if not os.path.exists(app_dir):
    log(f"Cloning {app}")
    run(["git", "clone", repo, app_dir])
else:
    log(f"Updating {app}")
    run(["git", "pull"], cwd=app_dir)

if os.path.exists(ACTIVE) or os.path.islink(ACTIVE):
    os.unlink(ACTIVE)

os.symlink(app_dir, ACTIVE)
log(f"Active app set to {app}")
