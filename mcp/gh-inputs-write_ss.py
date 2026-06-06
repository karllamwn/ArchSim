# ArchSim GH Live Writer — pushes current GH state TO app
# ─────────────────────────────────────────────────────────────────────────────
# Writes snapshots/.gh-live.json on each solve. The app's core/ghSync.js
# polls it at ~800ms and updates the UI when values differ from what it
# last pushed — that's how a slider nudged directly in Rhino shows up
# live in the browser.
#
# INPUTS (all Item Access — wire GH sliders / panels / values here):
#   floors            int
#   floorHeight       float
#   floorplate        float
#   structuralSpan    float
#   wwRatio           float
#   orientation       float
#   buildingUse       str
#   windowType        int
#   siteWidth         float
#   siteDepth         float
#   zoneMaxHeight     float
#   zoneMaxFSR        float
#   zoneFrontSetback  float
#   zoneSideSetback   float
#   zoneRearSetback   float
#   zoneMaxCoverage   float
#
# OUTPUT:
#   status            str  — "OK hh:mm:ss - written" / "unchanged" / error
#
# BEHAVIOUR:
#   • Hash-compares against the last written payload — skips disk I/O when
#     nothing has changed, so the app poller sees no spurious updates.
#   • Atomic write (temp + rename) so the app never reads a half file.
# ─────────────────────────────────────────────────────────────────────────────
import os
import json
import hashlib
import datetime

PROJECT_PATH = r"C:\Users\Karl\Documents\UBC\MArch Yr3\Arch 549 GP2\01_Assignment\app\ClaudeCode\Claude_Project_ArchSimV2"
LIVE_FILE    = os.path.join(PROJECT_PATH, "snapshots", ".gh-live.json")
LIVE_TMP     = LIVE_FILE + ".tmp"

if "_last_hash" not in globals():
    _last_hash = ""

def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except:
        return None

payload = {
    "floors":           int(round(_num(floors)))      if floors            is not None else None,
    "floorHeight":      _num(floorHeight),
    "floorplate":       _num(floorplate),
    "structuralSpan":   _num(structuralSpan),
    "wwRatio":          _num(wwRatio),
    "orientation":      _num(orientation),
    "buildingUse":      str(buildingUse) if buildingUse is not None else None,
    "windowType":       int(round(_num(windowType)))  if windowType        is not None else None,
    "siteWidth":        _num(siteWidth),
    "siteDepth":        _num(siteDepth),
    "zoneMaxHeight":    _num(zoneMaxHeight),
    "zoneMaxFSR":       _num(zoneMaxFSR),
    "zoneFrontSetback": _num(zoneFrontSetback),
    "zoneSideSetback":  _num(zoneSideSetback),
    "zoneRearSetback":  _num(zoneRearSetback),
    "zoneMaxCoverage":  _num(zoneMaxCoverage),
}
# Strip None so the app doesn't clobber keys GH doesn't provide
payload = {k: v for k, v in payload.items() if v is not None}
payload["_ts"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Hash excluding timestamp so we only write on real changes
_h_data = {k: v for k, v in payload.items() if k != "_ts"}
_h = hashlib.md5(json.dumps(_h_data, sort_keys=True).encode("utf-8")).hexdigest()

status_str = "unchanged ({})".format(_h[:8])
if _h != _last_hash:
    try:
        _dir = os.path.dirname(LIVE_FILE)
        if not os.path.exists(_dir):
            os.makedirs(_dir)
        with open(LIVE_TMP, "w") as f:
            json.dump(payload, f, indent=2)
        # os.replace is atomic on both Windows and POSIX
        if os.path.exists(LIVE_FILE):
            os.remove(LIVE_FILE)
        os.rename(LIVE_TMP, LIVE_FILE)
        _last_hash = _h
        status_str = "OK {} - written ({} keys)".format(
            datetime.datetime.now().strftime("%H:%M:%S"),
            len(payload) - 1,
        )
    except Exception as e:
        status_str = "ERROR: " + str(e)

status = status_str
print(status)
