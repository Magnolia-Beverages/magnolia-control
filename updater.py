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
    return subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def head_differs_from_origin(path, branch):
    subprocess.run(
        ["git", "fetch", "--all", "--prune"],
        cwd=path,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    local = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=path
    ).strip()

    remote = subprocess.check_output(
        ["git", "rev-parse", f"origin/{branch}"],
        cwd=path
    ).strip()

    return local != remote

def inside_update_window(cfg):
    window = cfg.get("update_window")
    if not window:
        return True

    now = datetime.now().time()
    start = time.fromisoformat(window["start"])
    end = time.fromisoformat(window["end"])

    return start <= now <= end

log("Updater started")

# LOCAL OVERRIDE
if os.path.exists(OVERRIDE) and os.path.getsize(OVERRIDE) > 0:
    log("Local override active, exiting")
    exit(0)

# MACHINE ID
if not os.path.exists(MID_FILE):
    log("Machine ID missing, exiting")
    exit(1)

machine_id = open(MID_FILE).read().strip()

# CONTROL REPO
if head_differs_from_origin(CONTROL, "main"):
    log("Control repo changed, resetting")
    run(["git", "reset", "--hard", "origin/main"], cwd=CONTROL)
    control_changed = True
else:
    log("Control repo unchanged")
    control_changed = False

# LOAD CONFIG AFTER CONTROL SYNC
apps = json.load(open(f"{CONTROL}/apps.json"))

cfg_path = f"{CONTROL}/machines/{machine_id}.json"
cfg = (
    json.load(open(cfg_path))
    if os.path.exists(cfg_path)
    else json.load(open(f"{CONTROL}/default.json"))
)

# AUTO UPDATE MASTER SWITCH
if not cfg.get("auto_update", True):
    log("Auto update disabled, exiting")
    exit(0)

# UPDATE WINDOW WITH FORCE OVERRIDE
if not inside_update_window(cfg) and not cfg.get("force_restart", False):
    log("Outside update window, skipping")
    exit(0)

app = cfg["app"]
log(f"Configured app = {app}")

repo = apps[app]["repo"]
branch = apps[app].get("branch", "main")
app_dir = f"{APPS}/{app}"

app_changed = False
app_switched = False

# APP REPO
if not os.path.exists(app_dir):
    log(f"Cloning app {app}")
    run(["git", "clone", "-b", branch, repo, app_dir])
    app_changed = True
else:
    if head_differs_from_origin(app_dir, branch):
        log(f"App repo {app} changed, resetting")
        run(["git", "reset", "--hard", f"origin/{branch}"], cwd=app_dir)
        app_changed = True
    else:
        log(f"App repo {app} unchanged")

# LOG CURRENT COMMIT
try:
    commit = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=app_dir
    ).decode().strip()
    log(f"Running app commit {commit}")
except Exception:
    log("Unable to read app commit")

# ACTIVE SYMLINK
if not os.path.islink(ACTIVE) or os.readlink(ACTIVE) != app_dir:
    if os.path.exists(ACTIVE):
        os.unlink(ACTIVE)
    os.symlink(app_dir, ACTIVE)
    log(f"Active app switched to {app}")
    app_switched = True

# RESTART DECISION
restart_required = (
    control_changed
    or app_changed
    or app_switched
    or cfg.get("force_restart", False)
)

if restart_required:
    log("Restarting Magnolia service")
    run(["sudo", "systemctl", "restart", "magnolia.service"])
else:
    log("No restart needed")
