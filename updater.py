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
    return subprocess.run(cmd, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def repo_has_changes(path, branch="main"):
    run(["git", "fetch"], cwd=path)
    result = subprocess.run(
        ["git", "diff", "--quiet", f"HEAD", f"origin/{branch}"],
        cwd=path
    )
    return result.returncode != 0  # True if changes exist

log("Updater started")

# ─── Local override ─────────────────────────────────────
if os.path.exists(OVERRIDE) and os.path.getsize(OVERRIDE) > 0:
    log("Local override active, skipping")
    exit(0)

# ─── Machine ID ─────────────────────────────────────────
if not os.path.exists(MID_FILE):
    log("Machine ID missing")
    exit(1)

machine_id = open(MID_FILE).read().strip()

# ─── Pull control repo ──────────────────────────────────
control_changed = repo_has_changes(CONTROL)
if control_changed:
    log("Control repo changed, syncing")
    run(["git", "reset", "--hard", "origin/main"], cwd=CONTROL)
else:
    log("Control repo unchanged")

apps = json.load(open(f"{CONTROL}/apps.json"))

cfg_path = f"{CONTROL}/machines/{machine_id}.json"
cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else json.load(open(f"{CONTROL}/default.json"))

app = cfg["app"]
log(f"Configured app = {app}")

repo = apps[app]["repo"]
branch = apps[app].get("branch", "main")
app_dir = f"{APPS}/{app}"

app_changed = False
app_switched = False

# ─── App repo handling ──────────────────────────────────
if not os.path.exists(app_dir):
    log(f"Cloning {app}")
    run(["git", "clone", "-b", branch, repo, app_dir])
    app_changed = True
else:
    if repo_has_changes(app_dir, branch):
        log(f"App repo {app} changed, pulling")
        run(["git", "reset", "--hard", f"origin/{branch}"], cwd=app_dir)
        app_changed = True
    else:
        log(f"App repo {app} unchanged")

# ─── Active symlink ─────────────────────────────────────
if not os.path.islink(ACTIVE) or os.readlink(ACTIVE) != app_dir:
    if os.path.exists(ACTIVE):
        os.unlink(ACTIVE)
    os.symlink(app_dir, ACTIVE)
    log(f"Active app switched to {app}")
    app_switched = True

# ─── Restart decision ───────────────────────────────────
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
