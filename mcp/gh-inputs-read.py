# ArchSim GH Inputs Reader — round-boundary sync FROM app
# ─────────────────────────────────────────────────────────────────────────────
# Reads snapshots/.gh-inputs.json (written by the app via serve.py) and
# outputs each parameter on its own output pin. Wire a GH Timer component
# into the `tick` input to drive reads at ~400-600ms.
#
# FLOW:
#   1. App (core/roundSync.js) generates a roundToken and POSTs the full
#      params payload to serve.py /gh-inputs.
#   2. serve.py atomically writes snapshots/.gh-inputs.json.
#   3. This script reads that file each timer tick and unpacks into 38
#      output pins that drive gh-massing / gh-structure / gh-windows /
#      gh-zoning-envelope / gh-params-export.
#   4. GH solves, gh-params-export.py echoes `roundToken` into params.json.
#   5. core/roundSync.js polls params.json and matches the token.
#
# INPUT:
#   tick          Any       — connect a Timer component here to drive ticks
#                             (or a button for manual refresh).
#
# OUTPUTS (all Item Access — 38 pins + status):
#
#   Site & zoning:
#     siteWidth            float
#     siteDepth            float
#     zoneMaxHeight        float
#     zoneMaxFSR           float
#     zoneFrontSetback     float
#     zoneSideSetback      float
#     zoneRearSetback      float
#     zoneMaxCoverage      float
#
#   Core geometry:
#     floors               int
#     floor_height         float
#     orientation          float
#
#   Base / top shape (gh-massing):
#     base_shape           int
#     base_scale           float
#     top_scale            float
#     top_offset_x         float
#     top_offset_y         float
#     top_rotation         float
#
#   Section typology (gh-massing):
#     section_type         int
#     podium_floors        int
#     tower_ratio          float
#     setback_depth        float
#     setback_interval     int
#     stilt_floors         int
#     stilt_col_shape      int
#     stilt_col_size       float
#     garden_interval      int
#     garden_floors        int
#
#   Plan typology (gh-massing):
#     plan_type            int
#     courtyard_ratio      float
#     void_corner          int
#     void_ratio           float
#     split_gap            float
#     bar_ratio            float
#
#   Structure (gh-structure). NOTE: structural_span is ONE pin but the user
#   wires it twice in the GH canvas — once to gh-structure.structural_span
#   and once to gh-massing.stilt_col_span (gh-massing.py:46 says the stilt
#   column span must match the structural span, so a single source of truth):
#     structural_span      float
#     lateral_system       int
#     column_shape         int     — 0=Square 1=Round
#     column_size          float   — Column width/diameter (m)
#
#   Windows (gh-windows):
#     window_type          int
#     wwRatio              float
#     bay_spacing          float
#
#   Round-token roundtrip (see core/roundSync.js + gh-params-export.py):
#     roundToken           str
#
#   status                 str  — "OK hh:mm:ss — N keys" / "waiting" / error
#
# BEHAVIOUR:
#   • If .gh-inputs.json doesn't exist yet, every pin outputs None and
#     status = "waiting for app". Downstream components should handle None
#     by falling back to native GH sliders (OR logic / Longest List etc).
#   • Caches the last successful payload in sticky globals so a transient
#     read failure doesn't collapse the graph to None.
#   • No-op if the file hasn't changed since last tick (mtime check).
# ─────────────────────────────────────────────────────────────────────────────
import os
import json
import datetime

PROJECT_PATH = r"C:\Users\Karl\Documents\UBC\MArch Yr3\Arch 549 GP2\01_Assignment\app\ClaudeCode\Claude_Project_ArchSimV2"
INPUTS_FILE  = os.path.join(PROJECT_PATH, "snapshots", ".gh-inputs.json")

# Sticky cache so a missing/locked file doesn't clear downstream values
if "_last_payload" not in globals():
    _last_payload = {}
if "_last_mtime" not in globals():
    _last_mtime = 0.0

def _safe_num(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except:
        return default

def _safe_int(v, default=None):
    n = _safe_num(v, None)
    return int(round(n)) if n is not None else default

def _safe_str(v, default=None):
    return str(v) if v is not None else default

status_str = "waiting for app"
_payload = dict(_last_payload)

try:
    if os.path.exists(INPUTS_FILE):
        mt = os.path.getmtime(INPUTS_FILE)
        if mt != _last_mtime:
            with open(INPUTS_FILE, "r") as f:
                fresh = json.load(f)
            if isinstance(fresh, dict):
                _payload      = fresh
                _last_payload = fresh
                _last_mtime   = mt
        now = datetime.datetime.now().strftime("%H:%M:%S")
        status_str = "OK {} - {} keys".format(now, len(_payload))
    else:
        status_str = "waiting for app (no .gh-inputs.json yet)"
except Exception as e:
    status_str = "ERROR: " + str(e)

def _g(k):
    return _payload.get(k)

# ── Site & zoning ────────────────────────────────────────────────────────────
siteWidth        = _safe_num(_g("siteWidth"))
siteDepth        = _safe_num(_g("siteDepth"))
zoneMaxHeight    = _safe_num(_g("zoneMaxHeight"))
zoneMaxFSR       = _safe_num(_g("zoneMaxFSR"))
zoneFrontSetback = _safe_num(_g("zoneFrontSetback"))
zoneSideSetback  = _safe_num(_g("zoneSideSetback"))
zoneRearSetback  = _safe_num(_g("zoneRearSetback"))
zoneMaxCoverage  = _safe_num(_g("zoneMaxCoverage"))

# ── Core geometry ────────────────────────────────────────────────────────────
floors           = _safe_int(_g("floors"))
floor_height     = _safe_num(_g("floor_height") if _g("floor_height") is not None else _g("floorHeight"))
orientation      = _safe_num(_g("orientation"))

# ── Base / top shape (gh-massing) ────────────────────────────────────────────
base_shape       = _safe_int(_g("base_shape"))
base_scale       = _safe_num(_g("base_scale"))
top_scale        = _safe_num(_g("top_scale"))
top_offset_x     = _safe_num(_g("top_offset_x"))
top_offset_y     = _safe_num(_g("top_offset_y"))
top_rotation     = _safe_num(_g("top_rotation"))

# ── Section typology (gh-massing) ────────────────────────────────────────────
section_type     = _safe_int(_g("section_type") if _g("section_type") is not None else _g("sectionType"))
podium_floors    = _safe_int(_g("podium_floors"))
tower_ratio      = _safe_num(_g("tower_ratio"))
setback_depth    = _safe_num(_g("setback_depth"))
setback_interval = _safe_int(_g("setback_interval"))
stilt_floors     = _safe_int(_g("stilt_floors"))
stilt_col_shape  = _safe_int(_g("stilt_col_shape"))
stilt_col_size   = _safe_num(_g("stilt_col_size"))
garden_interval  = _safe_int(_g("garden_interval"))
garden_floors    = _safe_int(_g("garden_floors"))

# ── Plan typology (gh-massing) ───────────────────────────────────────────────
plan_type        = _safe_int(_g("plan_type") if _g("plan_type") is not None else _g("planType"))
courtyard_ratio  = _safe_num(_g("courtyard_ratio"))
void_corner      = _safe_int(_g("void_corner"))
void_ratio       = _safe_num(_g("void_ratio"))
split_gap        = _safe_num(_g("split_gap"))
bar_ratio        = _safe_num(_g("bar_ratio"))

# ── Structure (gh-structure). ONE pin, user wires it twice in the canvas ────
# (once to gh-structure.structural_span, once to gh-massing.stilt_col_span).
structural_span  = _safe_num(_g("structural_span") if _g("structural_span") is not None else _g("structuralSpan"))
lateral_system   = _safe_int(_g("lateral_system") if _g("lateral_system") is not None else _g("lateralSystem"))
column_shape     = _safe_int(_g("column_shape"))
column_size      = _safe_num(_g("column_size"))

# ── Windows (gh-windows) ─────────────────────────────────────────────────────
window_type      = _safe_int(_g("window_type") if _g("window_type") is not None else _g("windowType"))
wwRatio          = _safe_num(_g("wwRatio"))
bay_spacing      = _safe_num(_g("bay_spacing") if _g("bay_spacing") is not None else _g("baySpacing"))

# ── Round-token roundtrip ────────────────────────────────────────────────────
roundToken       = _safe_str(_g("roundToken"))

status = status_str
print(status)
