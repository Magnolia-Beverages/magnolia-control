#!/home/pi/MagnoliaPackages/bin/python3.11

import json
import os
import subprocess
from datetime import datetime, time

BASE = "/home/pi"
CONTROL = f"{BASE}/magnolia-control"
APPS = f"{BASE}/magnolia-apps"
ACTIVE = f"{BASE}/magnolia-active"
OVERRIDE = f"{BASE}/magnolia-local/override.conf"
LOG = f"{BASE}/logs/magnolia.log"
MID_FILE = "/etc/magnolia_id"

def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")

def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=False)

def within_update_window(cfg):
    window = cfg.get("update_window")
    if not window:
        return True

    now = datetime.now().time()
    start = datetime.strptime(window["start"], "%H:%M").time()
    end = datetime.strptime(window["end"], "%H:%M").time()

    if start <= end:
        return start <= now <= end
    else:
        return now >= start or now <= end

log("Updater started")

# Local override
if os.path.exists(OVERRIDE) and os.path.getsize(OVERRIDE) > 0:
    log("Local override active")
    exit(0)

if not os.path.exists(MID_FILE):
    log("Machine ID missing")
    exit(1)

machine_id = open(MID_FILE).read().strip()

# Force control repo to match GitHub exactly
run(["git", "fetch"], cwd=CONTROL)
run(["git", "reset", "--hard", "origin/main"], cwd=CONTROL)
run(["git", "pull"], cwd=CONTROL)

apps = json.load(open(f"{CONTROL}/apps.json"))

cfg_path = f"{CONTROL}/machines/{machine_id}.json"
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else json.load(open(f"{CONTROL}/default.json"))

# Auto update gate
if not cfg.get("auto_update", True):
    log("Auto update disabled by GitHub")
    exit(0)

# Time window gate
if not within_update_window(cfg):
    log("Outside update window, skipping")
    exit(0)

app = cfg["app"]
log(f"Config app value = {app}")

repo = apps[app]["repo"]
branch = apps[app].get("branch")

app_dir = f"{APPS}/{app}"

if not os.path.exists(app_dir):
    log(f"Cloning {app}")
    if branch:
        run(["git", "clone", "-b", branch, repo, app_dir])
    else:
        run(["git", "clone", repo, app_dir])
else:
    log(f"Updating {app}")
    run(["git", "pull"], cwd=app_dir)

if os.path.islink(ACTIVE) or os.path.exists(ACTIVE):
    os.unlink(ACTIVE)

os.symlink(app_dir, ACTIVE)
log(f"Active app set to {app}")

# Restart request
if cfg.get("force_restart"):
    log("Force restart requested from GitHub")
    run(["sudo", "systemctl", "restart", "magnolia.service"])
