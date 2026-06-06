# ArchSim GH Params Exporter (+ Snapshot + History + Manifest)
# ─────────────────────────────────────────────────────────────────────────────
# Collects data from all upstream GH scripts, writes params.json, and captures
# a batch of named-view JPGs. Builds a round-by-round history + manifest so the
# JS app can browse / compare previous design rounds.
#
# INPUTS:
#   export             Boolean      — toggle True to write + capture
#   floorplate         Number       — fallback only; derived from massing if wired
#   buildingUse        String       — office / residential / mixed / retail / ...
#
#   # Grouped JSON inputs (connect export_json output from each script):
#   zoning             String       — from gh_zoning_envelope.py
#   massing            String       — from gh-massing.py
#   structure          String       — from gh-structure.py
#   karamba            String       — from gh-karamba-extract.py
#   windows            String       — from gh-windows.py
#   ladybug            String       — from gh-ladybug-extract.py
#
#   # Snapshot inputs (NEW — add these to the component):
#   view_names         List<String> — named views to capture, e.g.
#                                     Parallel_NE / Parallel_NW / Parallel_SE / Parallel_SW
#                                     List Access. If empty, uses the 4 defaults above.
#   snapshot_enable    Boolean      — optional, Item Access. Default True.
#                                     Wire a toggle if you want to disable capture.
#
#   # Round-token roundtrip input (NEW):
#   roundToken         String       — Item Access. Wire from
#                                     gh-inputs-read.roundToken. Echoed into
#                                     params.json so core/roundSync.js in the
#                                     app can detect when *this* round's solve
#                                     has completed (and not a stale previous
#                                     one). Optional — if not wired, the field
#                                     is omitted from params.json.
#
# OUTPUT:
#   out                String       — multi-line status summary
#
# BEHAVIOUR:
#   • Hash check: if data (excluding timestamp) is identical to the last written
#     round, skip everything. Lets you spam the export button safely.
#   • On change detected:
#       1. Write snapshots/latest/params.json  + overwrite latest/{view}.jpg
#       2. Copy everything into snapshots/history/{YYYYMMDD_HHMMSS}/
#       3. Append round entry to snapshots/manifest.json  (trim to last 50)
#       4. Also still writes the top-level params.json for backward compat.
#
# FOLDER LAYOUT (all under PROJECT_PATH/snapshots):
#   latest/
#       Parallel_NE.jpg, Parallel_NW.jpg, Parallel_SE.jpg, Parallel_SW.jpg
#       params.json
#   history/
#       20260410_161233/   ← one folder per round
#           Parallel_*.jpg
#           params.json
#       20260410_164512/
#           ...
#   manifest.json    ← summary index for the JS comparison UI
#   .params_hash.txt ← sidecar for change detection (internal)
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
import hashlib
import shutil

# Rhino imports (available in GHPython runtime)
import Rhino
import System.Drawing as sd
import System.Drawing.Imaging as sdi

# ── Config ────────────────────────────────────────────────────────────────────
PROJECT_PATH = r"C:\Users\Karl\Documents\UBC\MArch Yr3\Arch 549 GP2\01_Assignment\app\ClaudeCode\Claude_Project_ArchSimV2"
OUTPUT_FILE = os.path.join(PROJECT_PATH, "params.json")

SNAPSHOT_ROOT = os.path.join(PROJECT_PATH, "snapshots")
LATEST_DIR    = os.path.join(SNAPSHOT_ROOT, "latest")
HISTORY_DIR   = os.path.join(SNAPSHOT_ROOT, "history")
ARCHIVE_DIR   = os.path.join(SNAPSHOT_ROOT, "archive")   # per-session dumps
MANIFEST_FILE = os.path.join(SNAPSHOT_ROOT, "manifest.json")
HASH_FILE     = os.path.join(SNAPSHOT_ROOT, ".params_hash.txt")
SESSION_FILE  = os.path.join(SNAPSHOT_ROOT, ".session.json")  # written by serve.py

DEFAULT_VIEW_NAMES = ["Parallel_NE", "Parallel_NW", "Parallel_SE", "Parallel_SW"]
SNAPSHOT_W = 1920
SNAPSHOT_H = 1080
HISTORY_KEEP = 50  # retention cap; older rounds deleted after this

# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_parse(json_str):
    """Parse a JSON string input. Returns dict or empty dict."""
    if json_str is None or str(json_str).strip() in ("", "None"):
        return {}
    try:
        return json.loads(str(json_str))
    except:
        return {}

def _ensure_dir(p):
    if not os.path.exists(p):
        os.makedirs(p)

def _hash_data(d):
    """Stable MD5 of data dict excluding timestamp field."""
    d2 = dict(d)
    d2.pop("timestamp", None)
    s = json.dumps(d2, sort_keys=True)
    h = hashlib.md5()
    h.update(s.encode("utf-8") if hasattr(s, "encode") else s)
    return h.hexdigest()

def _read_prev_hash():
    if not os.path.exists(HASH_FILE):
        return None
    try:
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    except:
        return None

def _write_hash(h):
    _ensure_dir(SNAPSHOT_ROOT)
    with open(HASH_FILE, "w") as f:
        f.write(h)

def _capture_named_view(view_name, out_path):
    """Restore a Rhino Named View into the active viewport, then capture a JPG
    at SNAPSHOT_W x SNAPSHOT_H. Returns (ok, message).

    Note: mutates the active viewport's camera. We save the previous viewport
    state before each call in the batch loop and restore it at the end, so the
    user's working view isn't permanently changed."""
    doc = Rhino.RhinoDoc.ActiveDoc
    nv_table = doc.NamedViews
    idx = nv_table.FindByName(view_name)
    if idx < 0:
        return (False, "named view '{}' not found".format(view_name))

    active_view = doc.Views.ActiveView
    if active_view is None:
        return (False, "no active viewport to capture into")

    try:
        # Restore the named view into the active viewport
        ok = nv_table.Restore(idx, active_view.ActiveViewport)
        if not ok:
            return (False, "NamedViews.Restore failed for '{}'".format(view_name))
        active_view.Redraw()

        vc = Rhino.Display.ViewCapture()
        vc.Width = SNAPSHOT_W
        vc.Height = SNAPSHOT_H
        vc.ScaleScreenItems = False
        vc.DrawAxes = False
        vc.DrawGrid = False
        vc.DrawGridAxes = False
        vc.TransparentBackground = False
        bmp = vc.CaptureToBitmap(active_view)
        if bmp is None:
            return (False, "capture returned None for '{}'".format(view_name))
        bmp.Save(out_path, sdi.ImageFormat.Jpeg)
        return (True, "OK")
    except Exception as e:
        return (False, "{}: {}".format(view_name, str(e)))

def _load_manifest():
    if not os.path.exists(MANIFEST_FILE):
        return {"rounds": [], "lastRoundNumber": 0, "sessionId": None}
    try:
        with open(MANIFEST_FILE, "r") as f:
            m = json.load(f)
        if "rounds" not in m:
            m["rounds"] = []
        if "lastRoundNumber" not in m:
            # back-fill for old manifests: take max existing number, else 0
            nums = [r.get("roundNumber", 0) for r in m["rounds"]]
            m["lastRoundNumber"] = max(nums) if nums else 0
        if "sessionId" not in m:
            m["sessionId"] = None
        return m
    except:
        return {"rounds": [], "lastRoundNumber": 0, "sessionId": None}

def _save_manifest(m):
    _ensure_dir(SNAPSHOT_ROOT)
    with open(MANIFEST_FILE, "w") as f:
        json.dump(m, f, indent=2)

def _round_summary(data):
    """Pluck key numbers from the full data dict for the manifest entry.
    JS reads this to render the round list without opening each round's
    params.json."""
    m = data.get("massing", {}) or {}
    k = data.get("karamba", {}) or {}
    l = data.get("ladybug", {}) or {}
    w = data.get("windows", {}) or {}
    s = data.get("structure", {}) or {}
    return {
        "roundNumber":     data.get("roundNumber"),
        "roundLabel":      data.get("roundLabel"),
        "floors":          data.get("floors"),
        "floorplate":      data.get("floorplate"),
        "totalGFA":        round(float(data.get("floors", 0)) * float(data.get("floorplate", 0)), 1),
        "height":          data.get("height"),
        "structuralSpan":  data.get("structuralSpan"),
        "wwRatio":         data.get("wwRatio"),
        "orientation":     data.get("orientation"),
        "buildingUse":     data.get("buildingUse"),
        "massingType": "{} + {} + {}".format(
            m.get("baseShapeName", "?"),
            m.get("sectionTypeName", "?"),
            m.get("planTypeName", "?"),
        ) if m else None,
        "efficiency":      m.get("efficiency"),
        "maxDeflection":   k.get("maxDeflection"),
        "utilization":     k.get("utilization"),
        "lateralDrift":    k.get("lateralDrift"),
        "rigidBodyModes":  k.get("rigidBodyModes"),
        "avgRadiation":    l.get("avgRadiation"),
        "peakRadiation":   l.get("peakRadiation"),
        "annualSolarHours":l.get("annualSolarHours"),
        "overheatingRisk": l.get("overheatingRisk"),
        "windowType":      w.get("windowTypeName") or data.get("windowType"),
    }

def _read_session_marker():
    """Read snapshots/.session.json written by serve.py when the app submits
    a new Client Brief. Returns dict with sessionId / startedAt / brief, or
    None if missing/unreadable."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except:
        return None

def _archive_current_session(old_session_id):
    """Move latest/, history/, manifest.json, .params_hash.txt into
    archive/{old_session_id}/ so the next session starts from a clean slate.
    Returns (moved_count, message)."""
    if not old_session_id:
        old_session_id = "unknown_" + str(hash(MANIFEST_FILE))
    dest = os.path.join(ARCHIVE_DIR, old_session_id)
    _ensure_dir(ARCHIVE_DIR)
    # If a folder with this id already exists (e.g. double-click), suffix it
    if os.path.exists(dest):
        i = 2
        while os.path.exists(dest + "_" + str(i)):
            i += 1
        dest = dest + "_" + str(i)
    _ensure_dir(dest)

    moved = 0
    for src in (LATEST_DIR, HISTORY_DIR):
        if os.path.exists(src):
            try:
                shutil.move(src, os.path.join(dest, os.path.basename(src)))
                moved += 1
            except:
                pass
    for src in (MANIFEST_FILE, HASH_FILE):
        if os.path.exists(src):
            try:
                shutil.move(src, os.path.join(dest, os.path.basename(src)))
                moved += 1
            except:
                pass
    return (moved, dest)

def _trim_history(keep_n):
    """Delete oldest history folders beyond retention cap. Does NOT touch
    latest/ or the manifest (manifest trimmed separately). Sorts by the
    embedded datetime portion of the folder name (after the R### prefix) so
    that R001_… through R999_… are ordered chronologically rather than
    lexically when round numbers wrap past the 3-digit pad width."""
    if not os.path.exists(HISTORY_DIR):
        return 0
    entries = [e for e in os.listdir(HISTORY_DIR) if os.path.isdir(os.path.join(HISTORY_DIR, e))]

    def _sort_key(name):
        # Accept both legacy "YYYYMMDD_HHMMSS" and new "R###_YYYYMMDD_HHMMSS".
        parts = name.split("_", 1)
        if parts[0].startswith("R") and len(parts) == 2:
            return parts[1]  # datetime portion
        return name

    entries.sort(key=_sort_key)
    removed = 0
    while len(entries) > keep_n:
        victim = entries.pop(0)
        try:
            shutil.rmtree(os.path.join(HISTORY_DIR, victim))
            removed += 1
        except:
            pass
    return removed

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
status = "Toggle [export] to True to write params.json + capture snapshots"

if export:
    # ── Parse grouped inputs ─────────────────────────────────────────────────
    zoning_data    = safe_parse(zoning)
    massing_data   = safe_parse(massing)
    structure_data = safe_parse(structure)
    karamba_data   = safe_parse(karamba)
    windows_data   = safe_parse(windows)
    ladybug_data   = safe_parse(ladybug) if "ladybug" in dir() else {}

    # ── Reconstruct top-level params from grouped data ───────────────────────
    _floors  = massing_data.get("floors", 10)
    _fh      = massing_data.get("floorHeight", 3.6)
    _ori     = massing_data.get("orientation", 0)
    _span    = structure_data.get("structuralSpan", 8.0)
    _wwr     = windows_data.get("wwRatio", 0.4)
    _wtype   = windows_data.get("windowType", 0)
    _bay     = windows_data.get("baySpacing", 1.5)
    # floorplate: derive from massing total GFA / floors. Fallback to panel.
    _fp = None
    try:
        _gfa = massing_data.get("massingArea", None)
        if _gfa is not None and _floors and _floors > 0:
            _fp = round(float(_gfa) / float(_floors), 1)
    except:
        _fp = None
    if _fp is None:
        try:
            _fp = float(floorplate) if floorplate is not None else 800
        except:
            _fp = 800
    _use     = str(buildingUse)  if buildingUse is not None else "office"

    import datetime
    _now = datetime.datetime.now()
    _ts_human = _now.strftime("%Y-%m-%d %H:%M:%S")
    _ts_id    = _now.strftime("%Y%m%d_%H%M%S")  # folder-safe datetime

    # ── Session handshake ────────────────────────────────────────────────────
    # The JS app writes snapshots/.session.json via serve.py every time the
    # user submits a new Client Brief. If the sessionId there differs from
    # the one recorded in our manifest, we archive everything from the old
    # session into archive/{oldSessionId}/ and start a fresh manifest at R001.
    _session_marker = _read_session_marker()
    _current_sid    = _session_marker.get("sessionId") if _session_marker else None
    _peek_manifest  = _load_manifest()
    _manifest_sid   = _peek_manifest.get("sessionId")
    _session_note   = ""

    if _current_sid and _current_sid != _manifest_sid:
        # Only archive if there's actually something to archive
        if _peek_manifest.get("rounds") or os.path.exists(HISTORY_DIR) or os.path.exists(LATEST_DIR):
            _moved, _dest = _archive_current_session(_manifest_sid or "legacy")
            _session_note = "NEW SESSION — archived {} item(s) to {}".format(_moved, os.path.basename(_dest))
        else:
            _session_note = "NEW SESSION — {}".format(_current_sid)
        # Fresh manifest for the new session
        _peek_manifest = {"rounds": [], "lastRoundNumber": 0, "sessionId": _current_sid}
        # Persist immediately so a mid-round crash still remembers the sid
        _save_manifest(_peek_manifest)

    # Peek at manifest to get the next round number (monotonic within session —
    # never resets from trimming, only resets on new Client Brief).
    _round_number   = _peek_manifest.get("lastRoundNumber", 0) + 1
    _round_label    = "R{:03d}".format(_round_number)  # R001, R042, R128…
    _round_id       = "{}_{}".format(_round_label, _ts_id)  # R042_20260410_161233

    data = {
        "source": "grasshopper",
        "timestamp": _ts_human,
        "roundId":   _round_id,
        "roundNumber": _round_number,
        "roundLabel":  _round_label,

        "floors":          _floors,
        "floorplate":      _fp,
        "floorHeight":     _fh,
        "height":          _floors * _fh,
        "structuralSpan":  _span,
        "wwRatio":         _wwr,
        "orientation":     _ori,
        "buildingUse":     _use,
        "windowType":      _wtype,
        "baySpacing":      _bay,
        "ghConnected":     True,
    }

    # ── Round-token echo (for core/roundSync.js) ─────────────────────────────
    # The app writes a roundToken into .gh-inputs.json at the start of each
    # round; gh-inputs-read.py passes it through and we echo it here so the
    # app can poll params.json and match the token to know *this* round's
    # solve is done (rather than reading a stale file from a previous round).
    if "roundToken" in dir() and roundToken is not None:
        try:
            _rt = str(roundToken).strip()
            if _rt:
                data["roundToken"] = _rt
        except:
            pass

    # ── Attach grouped data as nested objects ────────────────────────────────
    if structure_data:
        data["structuralSpanX"] = structure_data.get("structuralSpanX", _span)
        data["structuralSpanY"] = structure_data.get("structuralSpanY", _span)
        data["structure"] = structure_data
    if zoning_data:    data["zoning"]   = zoning_data
    if massing_data:   data["massing"]  = massing_data
    if karamba_data:   data["karamba"]  = karamba_data
    if windows_data:   data["windows"]  = windows_data
    if ladybug_data:   data["ladybug"]  = ladybug_data

    # ── Hash check: skip if unchanged since last round ───────────────────────
    # When a roundToken is present the app/bootstrap is actively waiting for
    # a response, so ALWAYS write even if the design data hasn't changed.
    curr_hash  = _hash_data(data)
    prev_hash  = _read_prev_hash()
    _has_token = bool(data.get("roundToken"))
    unchanged  = (prev_hash == curr_hash) and os.path.exists(OUTPUT_FILE) and not _has_token

    snapshot_report = []  # populated below

    try:
        if unchanged:
            status_lines = ["SKIPPED — no changes since last round ({})".format(prev_hash[:8])]
            status = "\n".join(status_lines)
        else:
            # ── Write top-level params.json ────────────────────────────────
            with open(OUTPUT_FILE, "w") as f:
                json.dump(data, f, indent=2)

            # ── Resolve view names ─────────────────────────────────────────
            _views = []
            if "view_names" in dir() and view_names is not None:
                try:
                    _views = [str(v) for v in list(view_names) if v is not None and str(v).strip()]
                except:
                    _views = []
            if not _views:
                _views = list(DEFAULT_VIEW_NAMES)

            # ── Resolve snapshot_enable toggle (defaults to True) ──────────
            _snap_enable = True
            if "snapshot_enable" in dir() and snapshot_enable is not None:
                try:
                    _snap_enable = bool(snapshot_enable)
                except:
                    _snap_enable = True

            if _snap_enable:
                # ── Prepare folders ────────────────────────────────────────
                _ensure_dir(SNAPSHOT_ROOT)
                _ensure_dir(LATEST_DIR)
                _ensure_dir(HISTORY_DIR)
                round_dir = os.path.join(HISTORY_DIR, _round_id)
                _ensure_dir(round_dir)

                # Save the active viewport's current camera so we can restore
                # it after the batch — capturing named views mutates it.
                _saved_vp = None
                try:
                    _active = Rhino.RhinoDoc.ActiveDoc.Views.ActiveView
                    if _active is not None:
                        _saved_vp = _active.ActiveViewport.GetViewInfo()
                except:
                    _saved_vp = None

                # ── PASS 1: capture all N views to a staging folder inside
                #    history/. If any fail, the whole round is rolled back so
                #    the comparison UI never sees a partial round. Only after
                #    all N succeed do we promote them to latest/.
                staging_ok    = True
                staging_paths = []   # list of (view, staging_path)

                for vn in _views:
                    staging_path = os.path.join(round_dir, vn + ".jpg")
                    ok, msg = _capture_named_view(vn, staging_path)
                    if ok:
                        snapshot_report.append((vn, True, "OK"))
                        staging_paths.append((vn, staging_path))
                    else:
                        snapshot_report.append((vn, False, msg))
                        staging_ok = False

                # Restore the user's original camera regardless of outcome
                if _saved_vp is not None:
                    try:
                        _active = Rhino.RhinoDoc.ActiveDoc.Views.ActiveView
                        if _active is not None:
                            _active.ActiveViewport.PushViewInfo(_saved_vp, False)
                            _active.Redraw()
                    except:
                        pass

                # ── PASS 2: commit or rollback ──────────────────────────────
                if not staging_ok:
                    # Rollback — delete the staging history folder so we don't
                    # leave an incomplete round on disk. Also: do NOT touch
                    # latest/, do NOT update manifest, do NOT update hash.
                    try:
                        if os.path.exists(round_dir):
                            shutil.rmtree(round_dir)
                    except:
                        pass
                    # Raise so the outer try/except writes a clear error status
                    # and skips manifest + hash updates.
                    raise Exception(
                        "Round {} aborted — {}/{} views failed. Check Named View names in Rhino.".format(
                            _round_label,
                            sum(1 for r in snapshot_report if not r[1]),
                            len(snapshot_report),
                        )
                    )

                # All N succeeded — promote staging copies to latest/
                for vn, staging_path in staging_paths:
                    latest_path = os.path.join(LATEST_DIR, vn + ".jpg")
                    try:
                        shutil.copyfile(staging_path, latest_path)
                    except Exception as e:
                        # A copy failure at this stage is unusual — the disk is
                        # likely full or latest/ is locked. Treat it as a round
                        # failure and rollback.
                        try:
                            if os.path.exists(round_dir):
                                shutil.rmtree(round_dir)
                        except:
                            pass
                        raise Exception("Promote to latest/ failed for {}: {}".format(vn, str(e)))

                # ── Copy params.json into latest/ and history/round_dir ───
                try:
                    shutil.copyfile(OUTPUT_FILE, os.path.join(LATEST_DIR, "params.json"))
                    shutil.copyfile(OUTPUT_FILE, os.path.join(round_dir,  "params.json"))
                except Exception as e:
                    snapshot_report.append(("params.json copy", False, str(e)))

                # ── Update manifest (append + trim to HISTORY_KEEP) ────────
                manifest = _load_manifest()
                # Preserve current sessionId on every write so the next run
                # knows we're still in this session.
                if _current_sid:
                    manifest["sessionId"] = _current_sid
                manifest["rounds"].append({
                    "id":          _round_id,         # R042_20260410_161233
                    "roundNumber": _round_number,     # 42
                    "roundLabel":  _round_label,      # "R042"
                    "datetime":    _ts_id,            # 20260410_161233
                    "timestamp":   _ts_human,         # 2026-04-10 16:12:33
                    "path":        "history/" + _round_id,
                    "hash":        curr_hash,
                    "summary":     _round_summary(data),
                })
                manifest["lastRoundNumber"] = _round_number
                # Trim manifest + history dirs in sync
                if len(manifest["rounds"]) > HISTORY_KEEP:
                    manifest["rounds"] = manifest["rounds"][-HISTORY_KEEP:]
                _save_manifest(manifest)
                _trim_history(HISTORY_KEEP)

            # ── Persist new hash ───────────────────────────────────────────
            _write_hash(curr_hash)

            # ── Build multi-line summary ───────────────────────────────────
            groups = [g for g in ["zoning", "massing", "structure", "karamba", "windows", "ladybug"] if data.get(g)]
            lines = []
            lines.append("OK — {}  ({})".format(_round_label, _ts_human))
            if _session_note:
                lines.append(_session_note)
            if _current_sid:
                lines.append("Session: {}".format(_current_sid))
            lines.append("Round id: {}".format(_round_id))
            lines.append("params.json: {}".format(OUTPUT_FILE))
            lines.append("Groups: {}".format(" + ".join(groups) if groups else "sliders only"))
            lines.append("")
            lines.append("── Core design params ──")
            lines.append("Floors: {}  x  {:.1f}m  =  {:.1f}m total".format(_floors, float(_fh), float(_floors) * float(_fh)))
            lines.append("Floorplate: {} m2   Total GFA: {:.0f} m2".format(_fp, float(_fp) * float(_floors)))
            lines.append("Structural span: {} m   WWR: {:.0%}".format(_span, float(_wwr)))
            lines.append("Orientation: {:.0f} deg   Use: {}".format(float(_ori), _use))

            if massing_data:
                lines.append("")
                lines.append("── Massing ──")
                lines.append("{} + {} + {}".format(
                    massing_data.get("baseShapeName", "?"),
                    massing_data.get("sectionTypeName", "?"),
                    massing_data.get("planTypeName", "?")
                ))
                lines.append("Area: {} m2   Volume: {} m3   Efficiency: {:.1%}".format(
                    massing_data.get("massingArea", 0),
                    massing_data.get("massingVolume", 0),
                    float(massing_data.get("efficiency", 0))
                ))

            if karamba_data:
                lines.append("")
                lines.append("── Structure (Karamba) ──")
                lines.append("Max deflection: {} mm   Utilization: {:.0%}".format(
                    karamba_data.get("maxDeflection", 0),
                    float(karamba_data.get("utilization", 0))
                ))
                lines.append("Drift: H/{}  ({})".format(
                    karamba_data.get("driftRatio", "?"),
                    karamba_data.get("lateralDrift", "?")
                ))
                if karamba_data.get("rigidBodyModes", 0) > 0:
                    lines.append("!! {} rigid body modes — unstable".format(karamba_data.get("rigidBodyModes")))

            if ladybug_data:
                lines.append("")
                lines.append("── Environment (Ladybug) ──")
                lines.append("Avg radiation: {} kWh/m2   Peak: {} kWh/m2".format(
                    ladybug_data.get("avgRadiation", 0),
                    ladybug_data.get("peakRadiation", 0)
                ))
                lines.append("Avg sun hours: {} hrs/year   Overheating: {}".format(
                    int(ladybug_data.get("annualSolarHours", 0)),
                    ladybug_data.get("overheatingRisk", "?")
                ))

            if windows_data:
                lines.append("")
                lines.append("── Windows ──")
                lines.append("Type: {}   WWR: {:.0%}   Bay spacing: {} m".format(
                    windows_data.get("windowTypeName", _wtype),
                    float(windows_data.get("wwRatio", _wwr)),
                    windows_data.get("baySpacing", _bay)
                ))

            if zoning_data:
                lines.append("")
                lines.append("── Zoning ──")
                _maxgfa = zoning_data.get("maxGFA", None)
                if _maxgfa:
                    _used = float(_fp) * float(_floors) / float(_maxgfa)
                    lines.append("Max GFA: {} m2   Used: {:.0%}".format(_maxgfa, _used))
                else:
                    lines.append("(no maxGFA reported)")

            # Snapshot section
            lines.append("")
            if _snap_enable and snapshot_report:
                ok_count   = sum(1 for r in snapshot_report if r[1])
                fail_count = sum(1 for r in snapshot_report if not r[1])
                lines.append("── Snapshots ──")
                lines.append("Captured {}/{}  →  snapshots/latest/ + history/{}/".format(
                    ok_count, len(snapshot_report), _round_id
                ))
                for vn, ok, msg in snapshot_report:
                    tag = "OK " if ok else "FAIL"
                    lines.append("  [{}] {}{}".format(tag, vn, "" if ok else "  — " + msg))
                if fail_count:
                    lines.append("({} failed — check view names in Rhino)".format(fail_count))
            elif not _snap_enable:
                lines.append("── Snapshots ──")
                lines.append("(disabled via snapshot_enable = False)")

            status = "\n".join(lines)

    except Exception as e:
        status = "ERROR: " + str(e)

print(status)
