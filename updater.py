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
    subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def inside_update_window(cfg):
    window = cfg.get("update_window")
    if not window:
        return True
    now = datetime.now().time()
    start = time.fromisoformat(window["start"])
    end = time.fromisoformat(window["end"])
    return start <= now <= end

log("Updater started")

# ─── LOCAL OVERRIDE ─────────────────────────────────────
if os.path.exists(OVERRIDE) and os.path.getsize(OVERRIDE) > 0:
    log("Local override active, skipping all updates")
    exit(0)

# ─── MACHINE ID ─────────────────────────────────────────
if not os.path.exists(MID_FILE):
    log("Machine ID missing")
    exit(1)

machine_id = open(MID_FILE).read().strip()

# ─── CONTROL REPO SYNC (ALWAYS HARD SYNC) ───────────────
log("Syncing control repo")
run(["git", "fetch"], cwd=CONTROL)
run(["git", "reset", "--hard", "origin/main"], cwd=CONTROL)

# Reload config AFTER sync
apps = json.load(open(f"{CONTROL}/apps.json"))

cfg_path = f"{CONTROL}/machines/{machine_id}.json"
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else json.load(open(f"{CONTROL}/default.json"))

# ─── AUTO UPDATE MASTER SWITCH ──────────────────────────
if not cfg.get("auto_update", True):
    log("Auto update disabled by config")
    exit(0)

# ─── UPDATE WINDOW ──────────────────────────────────────
if not inside_update_window(cfg):
    log("Outside update window, skipping")
    exit(0)

# ─── APP CONFIG ─────────────────────────────────────────
app = cfg["app"]
repo = apps[app]["repo"]
branch = apps[app].get("branch", "main")
app_dir = f"{APPS}/{app}"

restart_required = False

# ─── APP REPO SYNC (FORCE, NO DIFF) ─────────────────────
if not os.path.exists(app_dir):
    log(f"Cloning app {app}")
    run(["git", "clone", "-b", branch, repo, app_dir])
    restart_required = True
else:
    log(f"Force syncing app {app}")
    run(["git", "fetch"], cwd=app_dir)
    run(["git", "reset", "--hard", f"origin/{branch}"], cwd=app_dir)
    restart_required = True

# ─── ACTIVE SYMLINK ─────────────────────────────────────
if not os.path.islink(ACTIVE) or os.readlink(ACTIVE) != app_dir:
    if os.path.exists(ACTIVE):
        os.unlink(ACTIVE)
    os.symlink(app_dir, ACTIVE)
    log(f"Active app switched to {app}")
    restart_required = True

# ─── RESTART DECISION ───────────────────────────────────
if restart_required or cfg.get("force_restart", False):
    log("Restarting Magnolia service")
    run(["sudo", "systemctl", "restart", "magnolia.service"])
else:
    log("No restart needed")
