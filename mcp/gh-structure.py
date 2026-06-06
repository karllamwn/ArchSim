# ArchSim Structure — Column Grid + Karamba Line Model
# ─────────────────────────────────────────────────────────────────────────────
# Main GHPython component. Heavy logic in structure_helpers.py.
#
# INPUTS:
#   base_curve       Curve      — Base footprint
#   floor_curves     List[Curve]— Per-floor curves from massing (optional)
#   floor_slabs      List[Brep] — Per-floor slab breps (edges = primary beams)
#   floors           Integer    — Number of floors
#   floor_height     Number     — Floor-to-floor height (m)
#   structural_span  Number     — Target column spacing (m, 6-12)
#   lateral_system   Integer    — 0=RC Core  1=Perimeter Walls  2=Moment Frame  3=Coupled Cores
#   base_shape       Integer    — 0=Rect 1=Ellipse 2=Circle 3=Chamfered 4=Diamond
#   base_scale       Number     — 0.3-1.0
#   orientation      Number     — Rotation degrees
#   top_scale        Number     — Top vs base scale 0.1-1.0
#   top_rotation     Number     — Twist angle degrees
#   section_type     Integer    — 0=Straight 1=Podium+Tower 2=Stepped 3=Stilt 4=SkyGarden
#   podium_floors    Integer    — Podium height (section_type=1)
#   tower_ratio      Number     — Tower footprint ratio (section_type=1)
#   stilt_floors     Integer    — Open ground floors (section_type=3)
#   garden_interval  Integer    — Sky garden every N floors (section_type=4, default 6)
#   garden_floors    Integer    — Sky garden floor count (section_type=4, default 1)
#   plan_type        Integer    — 0=Solid 1..3=Courtyard 4=L 5=U 6=Split
#   courtyard_ratio  Number     — Courtyard void ratio
#   void_corner      Integer    — Corner for L (0=NE 1=NW 2=SW 3=SE)
#   void_ratio       Number     — Void ratio for L/U
#   split_gap        Number     — Gap between bars (m)
#   bar_ratio        Number     — Width ratio per bar
#   column_shape     Integer    — 0=Square 1=Round
#   column_size      Number     — Column width/diameter (m)
#
# OUTPUTS:
#   column_lines, primary_beam_lines, secondary_beam_lines
#   support_points, gravity_vector
#   col_id, primary_id, secondary_id
#   core_geometry, actual_span_x, actual_span_y
#   export_json, out
# ─────────────────────────────────────────────────────────────────────────────

import Rhino.Geometry as rg
import math
import json
import sys
import os

# ── Import helpers ──────────────────────────────────────────────────────────
# Add mcp directory to path so structure_helpers can be imported.
try:
    _ghdoc = ghenv.Component.OnPingDocument()
    _ghpath = _ghdoc.FilePath if _ghdoc else ""
    if _ghpath:
        _mcp = os.path.normpath(os.path.join(os.path.dirname(_ghpath),
               "app", "ClaudeCode", "Claude_Project_ArchSimV2", "mcp"))
        if os.path.isdir(_mcp) and _mcp not in sys.path:
            sys.path.insert(0, _mcp)
except:
    pass
# Also try the script's own directory (if __file__ is defined)
try:
    _self_dir = os.path.dirname(os.path.abspath(__file__))
    if _self_dir not in sys.path:
        sys.path.insert(0, _self_dir)
except:
    pass

# Force reload during development
if "structure_helpers" in sys.modules:
    del sys.modules["structure_helpers"]
import structure_helpers as sh

# ── Safe param readers ──────────────────────────────────────────────────────
def safe_int(val, default):
    if val is None or str(val) == "None":
        return default
    try:    return int(val)
    except: return default

def safe_float(val, default):
    if val is None or str(val) == "None":
        return default
    try:    return float(val)
    except: return default

# ── Coerce base_curve ────────────────────────────────────────────────────────
crv = None
if base_curve is not None:
    if hasattr(base_curve, "GetBoundingBox"):
        crv = base_curve
    elif hasattr(base_curve, "Geometry"):
        crv = base_curve.Geometry
    else:
        try:
            import rhinoscriptsyntax as rs
            crv = rs.coercecurve(base_curve)
        except:
            pass

if crv is None:
    out = "ERROR: base_curve is None"
    column_lines = []; primary_beam_lines = []; secondary_beam_lines = []
    support_points = []; gravity_vector = rg.Vector3d(0, 0, -1)
    col_id = "COL"; primary_id = "PB"; secondary_id = "SB"
    core_geometry = []; actual_span_x = 0.0; actual_span_y = 0.0
    export_json = json.dumps({})
    raise Exception(out)

# ── Read all optional inputs safely ──────────────────────────────────────────
_inputs = {}
_input_defaults = {
    "floor_curves": None, "floor_slabs": None,
    "floors": 10, "floor_height": 3.6, "structural_span": 8.0,
    "lateral_system": 0,
    "base_shape": 0, "base_scale": 1.0, "orientation": 0.0,
    "top_scale": 1.0, "top_rotation": 0.0,
    "section_type": 0, "podium_floors": 3, "tower_ratio": 0.5,
    "plan_type": 0, "courtyard_ratio": 0.25, "void_corner": 0,
    "void_ratio": 0.4, "split_gap": 4.0, "bar_ratio": 0.4,
    "column_shape": 0, "column_size": 0.5, "stilt_floors": 2,
    "garden_interval": 6, "garden_floors": 1,
}
for _k, _def in _input_defaults.items():
    try:
        _v = eval(_k)
        _inputs[_k] = _v if _v is not None and str(_v) != "None" else _def
    except:
        _inputs[_k] = _def

# ── Coerce floor_curves + floor_slabs ────────────────────────────────────────
import rhinoscriptsyntax as rs
import System

_fc_list = []
_has_fc = False
try:
    _fc_raw = _inputs["floor_curves"]
    if _fc_raw is not None:
        fc_items = list(_fc_raw) if hasattr(_fc_raw, "__iter__") else [_fc_raw]
        for fc_item in fc_items:
            fc = None
            if isinstance(fc_item, System.Guid):       fc = rs.coercecurve(fc_item)
            elif hasattr(fc_item, "GetBoundingBox"):    fc = fc_item
            elif hasattr(fc_item, "Geometry"):          fc = fc_item.Geometry
            elif hasattr(fc_item, "Value"):             fc = fc_item.Value
            if fc is not None and hasattr(fc, "IsClosed"):
                _fc_list.append(fc)
        if len(_fc_list) >= 2:
            _has_fc = True
except:
    _fc_list = []

_fs_list = []
_has_fs = False
try:
    _fs_raw = _inputs["floor_slabs"]
    if _fs_raw is not None:
        fs_items = list(_fs_raw) if hasattr(_fs_raw, "__iter__") else [_fs_raw]
        for fs_item in fs_items:
            fs = None
            if isinstance(fs_item, System.Guid):     fs = rs.coercebrep(fs_item)
            elif hasattr(fs_item, "Edges"):          fs = fs_item
            elif hasattr(fs_item, "Geometry"):       fs = fs_item.Geometry
            elif hasattr(fs_item, "Value"):          fs = fs_item.Value
            if fs is not None and hasattr(fs, "Edges"):
                _fs_list.append(fs)
        if len(_fs_list) >= 1:
            _has_fs = True
except:
    _fs_list = []

# ── Parameters ───────────────────────────────────────────────────────────────
nf   = safe_int(_inputs["floors"], 10)
fh   = safe_float(_inputs["floor_height"], 3.6)
span = max(3.0, safe_float(_inputs["structural_span"], 8.0))
lat  = safe_int(_inputs["lateral_system"], 0)
H    = nf * fh

b_shape        = safe_int(_inputs["base_shape"], 0)
b_scale        = max(0.3, min(1.0, safe_float(_inputs["base_scale"], 1.0)))
ori            = safe_float(_inputs["orientation"], 0.0)
p_top_scale    = max(0.1, min(1.0, safe_float(_inputs["top_scale"], 1.0)))
p_top_rotation = safe_float(_inputs["top_rotation"], 0.0)
s_type         = safe_int(_inputs["section_type"], 0)
p_podium_floors = safe_int(_inputs["podium_floors"], 3)
p_tower_ratio  = max(0.2, min(0.9, safe_float(_inputs["tower_ratio"], 0.5)))

p_type            = safe_int(_inputs["plan_type"], 0)
p_courtyard_ratio = max(0.05, min(0.6, safe_float(_inputs["courtyard_ratio"], 0.25)))
p_void_corner     = safe_int(_inputs["void_corner"], 0)
p_void_ratio      = max(0.2, min(0.6, safe_float(_inputs["void_ratio"], 0.4)))
p_split_gap       = max(1.0, safe_float(_inputs["split_gap"], 4.0))
p_bar_ratio       = max(0.15, min(0.45, safe_float(_inputs["bar_ratio"], 0.4)))

p_col_shape = safe_int(_inputs["column_shape"], 0)
p_col_size  = max(0.2, min(2.0, safe_float(_inputs["column_size"], 0.5)))
p_stilt_floors = safe_int(_inputs["stilt_floors"], 2)
p_stilt_col_span = max(3.0, safe_float(_inputs.get("stilt_col_span", span), span))
p_garden_interval = max(3, safe_int(_inputs["garden_interval"], 6))
p_garden_floors = max(1, safe_int(_inputs["garden_floors"], 1))

_is_courtyard = p_type in (1, 2, 3)
_has_twist = abs(p_top_rotation) > 0.001
_use_radial = b_shape in (1, 2, 3, 4)

print("Structure: shape={} sType={} pType={} fc={} span={} floors={}".format(
    b_shape, s_type, p_type, _has_fc, span, nf))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: BUILD PER-FLOOR CURVES
# ══════════════════════════════════════════════════════════════════════════════
_floor_crvs_flat = []
_floor_crvs_notwist = []

if _has_fc:
    for i in range(len(_fc_list)):
        _floor_crvs_flat.append(sh.flatten_crv(_fc_list[i]))
    while len(_floor_crvs_flat) <= nf:
        _floor_crvs_flat.append(_floor_crvs_flat[-1].DuplicateCurve())
    _floor_crvs_notwist = [c.DuplicateCurve() for c in _floor_crvs_flat]
    print("Using {} floor_curves from massing".format(len(_fc_list)))
else:
    shaped = sh.build_shaped_curve(crv, b_shape, b_scale, ori)
    _floor_crvs_flat, _floor_crvs_notwist = sh.build_floor_curves(
        shaped, nf, s_type, p_top_scale, p_top_rotation,
        p_podium_floors, p_tower_ratio)
    print("Derived floor curves from base_curve + params")

_ground_crv = _floor_crvs_flat[0]

# ── Void floors ──────────────────────────────────────────────────────────────
_void_beam_floors = {0}  # ground: no beams, but columns OK
_void_col_floors = set()
if s_type == 3:
    p_stilt_floors = max(1, min(p_stilt_floors, nf - 1))
    for vi in range(0, p_stilt_floors):
        _void_beam_floors.add(vi)
        _void_col_floors.add(vi)
elif s_type == 4:
    # Sky Garden: periodic void floors matching massing logic
    p_garden_floors = min(p_garden_floors, p_garden_interval - 1)
    for i in range(1, nf + 1):
        if i % p_garden_interval == 0:
            for g in range(p_garden_floors):
                vi = i + g
                if vi < nf:  # never void the top floor
                    _void_beam_floors.add(vi)
                    _void_col_floors.add(vi)
print("Void beam: {}  Void col: {}".format(sorted(_void_beam_floors), sorted(_void_col_floors)))

# ── Plan void ────────────────────────────────────────────────────────────────
def _make_void(fi):
    return sh.make_void_for_floor(fi, _floor_crvs_notwist, p_type, _is_courtyard,
                                  p_courtyard_ratio, p_void_corner, p_void_ratio,
                                  p_split_gap, p_bar_ratio)

_plan_void_crv = _make_void(0)
_plan_void_ccw = sh.ensure_ccw(_plan_void_crv) if _plan_void_crv is not None else None

def _point_in_void(pt):
    if _plan_void_ccw is None or not _plan_void_ccw.IsClosed:
        return False
    return _plan_void_ccw.Contains(pt, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: GENERATE BEAMS
# ══════════════════════════════════════════════════════════════════════════════
gnd_bb = _ground_crv.GetBoundingBox(True)
full_W = gnd_bb.Max.X - gnd_bb.Min.X
full_D = gnd_bb.Max.Y - gnd_bb.Min.Y

all_ring_lns = []
all_radial_lns = []

# Build slab boundaries
_slab_crvs_by_z = sh.build_slab_boundaries(_fs_list) if _has_fs else {}
if _slab_crvs_by_z:
    print("Slab boundaries at {} Z levels".format(len(_slab_crvs_by_z)))

# Generate beams per floor
for fi in range(nf + 1):
    z = fi * fh
    if fi in _void_beam_floors:
        print("  Floor {}: beam-void".format(fi))
        continue

    fi_crv = sh.ensure_ccw(_floor_crvs_flat[fi])
    floor_void = _make_void(fi)
    if floor_void is not None and _has_twist:
        t = float(fi) / max(1, nf)
        tw = t * p_top_rotation
        if abs(tw) > 0.001:
            floor_void = sh.rotate_curve(floor_void, tw, sh.get_centroid(fi_crv))

    try:
        rings, radials = sh.generate_beams_for_floor(fi_crv, z, floor_void, _use_radial, span, _is_courtyard)
        all_ring_lns.extend(rings)
        all_radial_lns.extend(radials)
        print("  Floor {}: {} ring + {} radial".format(fi, len(rings), len(radials)))
    except Exception as ex:
        print("  Floor {} ERROR: {}".format(fi, ex))

    # Stepped transition: add larger footprint beams
    if fi > 0 and s_type == 2:
        prev_crv = sh.ensure_ccw(_floor_crvs_flat[fi - 1])
        if sh.get_area(prev_crv) > 0 and sh.get_area(fi_crv) < sh.get_area(prev_crv) * 0.85:
            prev_void = _make_void(fi - 1)
            if prev_void is not None and _has_twist:
                t_p = float(fi) / max(1, nf)
                tw_p = t_p * p_top_rotation
                if abs(tw_p) > 0.001:
                    prev_void = sh.rotate_curve(prev_void, tw_p, sh.get_centroid(prev_crv))
            try:
                tr, trad = sh.generate_beams_for_floor(prev_crv, z, prev_void, _use_radial, span, _is_courtyard)
                all_ring_lns.extend(tr)
                all_radial_lns.extend(trad)
                print("  Floor {} STEP: +{} ring +{} radial".format(fi, len(tr), len(trad)))
            except:
                pass

# ── SkyGarden / Stilt transition beams ──────────────────────────────────────
# Add beams at the bottom and top of each void range so the structure has
# "cap" beams framing the open zone (uses the adjacent non-void floor curve).
if _void_col_floors:
    _sorted_vc = sorted(_void_col_floors)
    _vc_ranges = []
    _rs, _re = _sorted_vc[0], _sorted_vc[0]
    for _vi in _sorted_vc[1:]:
        if _vi == _re + 1:
            _re = _vi
        else:
            _vc_ranges.append((_rs, _re))
            _rs, _re = _vi, _vi
    _vc_ranges.append((_rs, _re))

    def _gen_beams_at(fi_ref, z_target):
        """Generate beams using fi_ref floor curve at z_target elevation."""
        fc = sh.ensure_ccw(_floor_crvs_flat[fi_ref])
        fv = _make_void(fi_ref)
        if fv is not None and _has_twist:
            t = float(fi_ref) / max(1, nf)
            tw = t * p_top_rotation
            if abs(tw) > 0.001:
                fv = sh.rotate_curve(fv, tw, sh.get_centroid(fc))
        try:
            r, rd = sh.generate_beams_for_floor(fc, z_target, fv, _use_radial, span, _is_courtyard)
            all_ring_lns.extend(r)
            all_radial_lns.extend(rd)
            print("  Void-cap at Z={:.1f} (ref fi={}): +{} ring +{} radial".format(
                z_target, fi_ref, len(r), len(rd)))
        except:
            pass

    for (_vs, _ve) in _vc_ranges:
        # Bottom cap: beams at bottom of void zone using floor below
        z_bot = _vs * fh
        if _vs > 0 and (_vs - 1) not in _void_beam_floors:
            if z_bot not in set(round(fi * fh, 1) for fi in range(nf+1) if fi not in _void_beam_floors):
                _gen_beams_at(_vs - 1, z_bot)
        # Top cap: beams at top of void zone using floor above
        z_top = (_ve + 1) * fh
        fi_above = _ve + 1
        if fi_above <= nf and fi_above not in _void_beam_floors:
            if z_top not in set(round(fi * fh, 1) for fi in range(nf+1) if fi not in _void_beam_floors):
                _gen_beams_at(fi_above, z_top)

# ── Grid info ────────────────────────────────────────────────────────────────
if _use_radial:
    r_max = max(full_W, full_D) / 2.0
    n_rings = max(2, int(math.ceil(r_max / span)))
    a_e, b_e = full_W / 2.0, full_D / 2.0
    p_g = math.pi * (3*(a_e+b_e) - math.sqrt((3*a_e+b_e)*(a_e+3*b_e)))
    n_rad = max(8, int(math.ceil(p_g / span)))
    grid_type = "radial ({}r x {}rad)".format(n_rings, n_rad)
    actual_span_x = r_max / n_rings
    actual_span_y = actual_span_x
    nx, ny = n_rings, n_rad
    p_dir, s_dir = "ring", "radial"
else:
    nx = max(2, int(math.ceil(full_W / span)))
    ny = max(2, int(math.ceil(full_D / span)))
    actual_span_x = full_W / nx
    actual_span_y = full_D / ny
    grid_type = "orthogonal ({}x{})".format(nx, ny)
    p_dir, s_dir = "edge", "grid"

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: ASSEMBLE PRIMARY / SECONDARY BEAMS
# ══════════════════════════════════════════════════════════════════════════════
primary_beam_lines = list(all_ring_lns)
_void_z_set = set(round(vi * fh, 1) for vi in _void_beam_floors)

if _has_fs:
    for slab in _fs_list:
        slab_bb = slab.GetBoundingBox(True)
        if round(slab_bb.Min.Z, 1) in _void_z_set:
            continue
        edges = slab.Edges
        if edges is None or edges.Count == 0:
            continue
        edge_hash = set()
        for ei in range(edges.Count):
            ec = edges[ei].DuplicateCurve()
            if ec is None or ec.GetLength() < 0.1:
                continue
            mid = ec.PointAtNormalizedLength(0.5)
            # Skip slab edges inside plan void (courtyard/L/U/split)
            if _plan_void_ccw is not None and _plan_void_ccw.IsClosed:
                mid_2d = rg.Point3d(mid.X, mid.Y, 0)
                if _plan_void_ccw.Contains(mid_2d, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                    continue
            mk = (round(mid.X, 1), round(mid.Y, 1), round(mid.Z, 1))
            if mk not in edge_hash:
                edge_hash.add(mk)
                primary_beam_lines.append(ec)
    print("Primary: {} (ring + slab edges)".format(len(primary_beam_lines)))
else:
    for fi in range(nf + 1):
        if fi in _void_beam_floors:
            continue
        z = fi * fh
        fi_crv = _floor_crvs_flat[fi]
        if fi_crv is None or fi_crv.GetLength() < 1.0:
            continue
        crv_at_z = fi_crv.DuplicateCurve()
        crv_at_z.Translate(rg.Vector3d(0, 0, z))
        if _plan_void_crv is not None:
            flat_c = sh.flatten_crv(fi_crv)
            ix = rg.Intersect.Intersection.CurveCurve(flat_c, _plan_void_crv, 0.01, 0.01)
            if ix is not None and ix.Count >= 2:
                sp = sorted([ix[i].ParameterA for i in range(ix.Count)])
                splits = crv_at_z.Split(sp)
                if splits:
                    for seg in splits:
                        mid = seg.PointAtNormalizedLength(0.5)
                        if not _point_in_void(rg.Point3d(mid.X, mid.Y, 0)):
                            primary_beam_lines.append(seg)
                    continue
        primary_beam_lines.append(crv_at_z)
    print("Primary: {} (fallback)".format(len(primary_beam_lines)))

# Re-trim secondary beams to actual slab boundaries
secondary_beam_lines = sh.retrim_secondary_beams(all_radial_lns, _slab_crvs_by_z)

# Subdivide all beams into short segments for Karamba node merging.
# Karamba only merges element ENDPOINTS within limit distance (0.5m),
# so beams must be broken into segments <= 0.5m.
primary_beam_lines = sh.subdivide_beams(primary_beam_lines, max_seg_len=0.5)
secondary_beam_lines = sh.subdivide_beams(secondary_beam_lines, max_seg_len=0.5)
print("After subdivide: {} primary, {} secondary".format(
    len(primary_beam_lines), len(secondary_beam_lines)))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: COLUMNS
# ══════════════════════════════════════════════════════════════════════════════
# Pre-compute core center and size for column exclusion in stilt/garden zones
_gnd_nt_bb = _floor_crvs_notwist[0].GetBoundingBox(True)
_gnd_c = sh.get_centroid(_floor_crvs_notwist[0])
W = _gnd_nt_bb.Max.X - _gnd_nt_bb.Min.X
D = _gnd_nt_bb.Max.Y - _gnd_nt_bb.Min.Y
cx, cy = _gnd_c.X, _gnd_c.Y
_core_size = max(2.0, round(min(W, D) * 0.18, 2)) if lat == 0 else 0

_all_beams = all_ring_lns + all_radial_lns
col_lns, col_pts = sh.generate_columns(
    nf, fh, span, s_type, p_top_rotation,
    _floor_crvs_flat, _all_beams, primary_beam_lines, secondary_beam_lines,
    _void_col_floors, make_void_fn=_make_void, b_shape=b_shape,
    core_cx=cx, core_cy=cy, core_size=_core_size,
    stilt_col_span=p_stilt_col_span)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: LATERAL SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

core_geom, core_note = sh.build_lateral_system(
    lat, p_type, W, D, H, nf, fh,
    cx, cy, _gnd_nt_bb.Min.X, _gnd_nt_bb.Min.Y, _gnd_nt_bb.Max.X, _gnd_nt_bb.Max.Y,
    p_void_ratio, p_void_corner, p_bar_ratio, p_split_gap, _point_in_void,
    void_col_floors=_void_col_floors,
    floor_crvs=_floor_crvs_flat, b_shape=b_shape,
    make_void_fn=_make_void, has_twist=_has_twist,
    top_rotation=p_top_rotation)

# ══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ══════════════════════════════════════════════════════════════════════════════
column_lines   = col_lns

# Extract support points directly from column line base endpoints
# to guarantee exact coordinate match with Karamba nodes
support_points = [cl.PointAtStart for cl in col_lns if abs(cl.PointAtStart.Z) < 0.01]
# Add core base support points (4 corners at z=0)
if lat == 0 and _core_size > 0:
    cs2 = _core_size / 2.0
    for (ccx, ccy) in [(cx-cs2, cy-cs2), (cx+cs2, cy-cs2),
                        (cx+cs2, cy+cs2), (cx-cs2, cy+cs2)]:
        support_points.append(rg.Point3d(ccx, ccy, 0))
print("Supports: {} column bases + {} core".format(
    len([cl for cl in col_lns if abs(cl.PointAtStart.Z) < 0.01]),
    4 if lat == 0 and _core_size > 0 else 0))
gravity_vector = rg.Vector3d(0, 0, -5.0)
core_geometry  = core_geom

col_id       = "COL"
primary_id   = "PB"
secondary_id = "SB"

lat_labels = ["RC Core", "Perimeter Walls", "Moment Frame", "Reserved"]
lat_label  = lat_labels[lat] if lat < len(lat_labels) else "Unknown"
PLAN_NAMES = ["Solid", "Courtyard", "Courtyard (Tower)", "Courtyard (Podium)",
              "L-Shape", "U-Shape", "Split / Dual Bar"]
p_name = PLAN_NAMES[p_type] if p_type < len(PLAN_NAMES) else "Solid"
BASE_NAMES = ["Rectangle", "Ellipse", "Circle", "Chamfered", "Diamond"]
b_name = BASE_NAMES[b_shape] if b_shape < len(BASE_NAMES) else "Rectangle"
src = "floor_curves ({})".format(len(_fc_list)) if _has_fc else "derived ({})".format(b_name)

out = (
    "Grid: {}  |  Span={:.2f}m\n"
    "Primary: {} ({})  Secondary: {} ({})\n"
    "Columns: {} ({}mm {})  |  Lateral: {} ({})\n"
    "Source: {}  |  Plan: {}\n"
    "Total: {} col + {} PB + {} SB = {}"
).format(
    grid_type, span,
    p_dir, len(primary_beam_lines),
    s_dir, len(secondary_beam_lines),
    len(col_pts), int(p_col_size * 1000),
    "Round" if p_col_shape == 1 else "Square",
    lat_label, core_note, src, p_name,
    len(col_lns), len(primary_beam_lines), len(secondary_beam_lines),
    len(col_lns) + len(primary_beam_lines) + len(secondary_beam_lines)
)

export_json = json.dumps({
    "structuralSpan": round(span, 3),
    "structuralSpanX": round(actual_span_x, 3),
    "structuralSpanY": round(actual_span_y, 3),
    "lateralSystem": lat_label,
    "columnCount": len(col_pts),
    "columnShape": "Round" if p_col_shape == 1 else "Square",
    "columnSize": round(p_col_size, 3),
    "gridType": "radial" if _use_radial else "orthogonal",
    "gridX": nx, "gridY": ny,
    "planType": p_name,
    "baseShape": b_name,
    "hasVoid": _plan_void_crv is not None,
    "floorCurvesConnected": _has_fc,
    "coreCenter": [round(cx, 2), round(cy, 2)],
    "totalElements": len(col_lns) + len(primary_beam_lines) + len(secondary_beam_lines)
})
