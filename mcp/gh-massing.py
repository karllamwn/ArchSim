# ArchSim Massing Generator V2 — Two-Curve System
# ─────────────────────────────────────────────────────────────────────────────
# Generates parametric building massing from base + top curves.
# Section modifiers control vertical stacking.
# Plan modifiers control floor plate shape.
# Combinable: 5 section x 5 plan = 25 possible combinations.
#
# Inspired by EvoMass (Likai Wang, NUS/XJTLU) subtractive/additive approach.
#
# INPUTS:
#   base_curve       Curve   — Bottom footprint (from zoning buildableFootprint)
#   top_curve        Curve   — Top footprint (optional, auto-generated if None)
#   site_boundary    Curve   — Site/buildable boundary for clipping (optional)
#   floors           Integer — Number of floors
#   floor_height     Number  — Floor-to-floor height (m)
#   orientation      Number  — Rotation angle in degrees (0 = North)
#
#   # Base shape (footprint derived from base_curve bounding box):
#   base_shape       Integer — 0=Rectangle (use base_curve as-is)
#                               1=Ellipse  2=Circle  3=Chamfered
#                               4=Diamond  5=H-Shape  6=Cross (+)
#   base_scale       Number  — Scale of footprint within base_curve (0.3-1.0, default 1.0)
#
#   # Top curve params (used when top_curve is not connected):
#   top_scale        Number  — Scale of top vs base (0.1-1.0, default 1.0)
#   top_offset_x     Number  — Shift top east/west in metres (default 0)
#   top_offset_y     Number  — Shift top north/south in metres (default 0)
#   top_rotation     Number  — Twist top vs base in degrees (default 0)
#
#   # Section modifier (how floors stack vertically):
#   section_type     Integer — 0=Straight  1=Podium+Tower  2=Stepped
#                               3=Stilt/Piloti  4=Sky Garden
#
#   # Plan modifier (floor plate shape):
#   plan_type        Integer — 0=Solid
#                               1=Courtyard (Both)  2=Courtyard (Tower Only)
#                               3=Courtyard (Podium Only)
#                               4=L-Shape  5=U-Shape  6=Split/Dual Bar
#
#   # Section params:
#   podium_floors    Integer — Podium height in floors (section 1, default 3)
#   tower_ratio      Number  — Tower footprint ratio of base (section 1, 0.2-0.9, default 0.5)
#   setback_depth    Number  — Setback depth per step in m (section 2, default 2.0)
#   setback_interval Integer — Step every N floors (section 2, default 5)
#   stilt_floors     Integer — Open ground floors (section 3, default 2)
#   stilt_col_span   Number  — Column spacing in stilt zone m (default 8, matches structural_span)
#   stilt_col_shape  Integer — Column shape: 0=Square  1=Round (default 0)
#   stilt_col_size   Number  — Column width/diameter in m (default 0.8)
#   lateral_system   Integer — 0=RC Core 1=Perimeter 2=Moment 3=Reserved (default 0)
#   garden_interval  Integer — Sky garden every N floors (section 4, default 6)
#   garden_floors    Integer — Sky garden floor count (section 4, default 1)
#
#   # Plan params:
#   courtyard_ratio  Number  — Courtyard void ratio (plan 1-3, 0.05-0.6, default 0.25)
#   void_corner      Integer — Corner to void (plan 4, 0=NE 1=NW 2=SW 3=SE, default 0)
#   void_ratio       Number  — Void size ratio (plan 4/5, 0.2-0.6, default 0.4)
#   split_gap        Number  — Gap between bars in m (plan 6, default 4.0)
#   bar_ratio        Number  — Width ratio per bar (plan 6, 0.15-0.45, default 0.4)
#
# OUTPUTS:
#   floor_slabs      List of Brep   — Floor slab surfaces per level
#   building_mass    List of Brep   — Building solid(s)
#   stilt_columns    List of Brep   — Stilt/sky garden column breps (separate output)
#   floor_curves     List of Curve  — Floor plate curves at each level
#   massing_area     Number         — Total gross floor area
#   massing_volume   Number         — Building volume
#   efficiency       Number         — Floor area ratio vs base case (1.0 = no loss)
#   export_json      String         — JSON bundle (connect to gh-params-export)
#   out              String         — Summary
# ─────────────────────────────────────────────────────────────────────────────

import Rhino.Geometry as rg
import math
import json
import System
import os, sys

# ── Import massing_helpers ─────────────────────────────────────────────────
# Add mcp directory to path so massing_helpers can be imported.
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
try:
    _self_dir = os.path.dirname(os.path.abspath(__file__))
    if _self_dir not in sys.path:
        sys.path.insert(0, _self_dir)
except:
    pass

# Force reload during development
if "massing_helpers" in sys.modules:
    del sys.modules["massing_helpers"]
import massing_helpers as mh

# ── Validate & coerce required inputs ───────────────────────────────────────
if base_curve is None:
    raise Exception("Connect base_curve (buildableFootprint from zoning envelope).")
if not hasattr(base_curve, "DuplicateCurve"):
    if hasattr(base_curve, "Geometry"):
        base_curve = base_curve.Geometry
    else:
        import rhinoscriptsyntax as rs
        base_curve = rs.coercecurve(base_curve)
        if base_curve is None:
            raise Exception("base_curve: cannot coerce input to Curve")
if floors is None or floors < 1:
    raise Exception("floors must be >= 1")
if floor_height is None or floor_height <= 0:
    raise Exception("floor_height must be > 0")

# ── Safe param readers ──────────────────────────────────────────────────────
def safe_int(val, default):
    if val is None or str(val) == "None":
        return default
    try:
        return int(val)
    except:
        return default

def safe_float(val, default):
    if val is None or str(val) == "None":
        return default
    try:
        return float(val)
    except:
        return default

# ── Parse all inputs ────────────────────────────────────────────────────────
nf   = int(floors)
fh   = float(floor_height)
ori  = safe_float(orientation, 0.0)
height = nf * fh

# Top curve params
p_top_scale    = max(0.1, min(1.0, safe_float(top_scale, 1.0)))
p_top_offset_x = safe_float(top_offset_x, 0.0)
p_top_offset_y = safe_float(top_offset_y, 0.0)
p_top_rotation = safe_float(top_rotation, 0.0)

# Base shape
b_shape = safe_int(base_shape, 0)
b_scale = max(0.3, min(1.0, safe_float(base_scale, 1.0)))

# Section + plan type
s_type = safe_int(section_type, 0)
p_type = safe_int(plan_type, 0)

# Section params
p_podium_floors    = safe_int(podium_floors, 3)
p_tower_ratio      = safe_float(tower_ratio, 0.5)
p_setback_depth    = safe_float(setback_depth, 2.0)
p_setback_interval = safe_int(setback_interval, 5)
p_stilt_floors     = safe_int(stilt_floors, 2)
p_stilt_col_span   = safe_float(stilt_col_span, 8.0)
p_stilt_col_shape  = safe_int(stilt_col_shape, 0)    # 0=Square, 1=Round
p_stilt_col_size   = max(0.2, min(3.0, safe_float(stilt_col_size, 0.8)))
p_lateral_system   = safe_int(lateral_system, 0)
p_garden_interval  = safe_int(garden_interval, 6)
p_garden_floors    = safe_int(garden_floors, 1)

# Plan params
p_courtyard_ratio = safe_float(courtyard_ratio, 0.25)
p_void_corner     = safe_int(void_corner, 0)
p_void_ratio      = safe_float(void_ratio, 0.4)
p_split_gap       = safe_float(split_gap, 4.0)
p_bar_ratio       = safe_float(bar_ratio, 0.4)

SECTION_NAMES = ["Straight", "Podium + Tower", "Stepped", "Stilt / Piloti", "Sky Garden"]
PLAN_NAMES    = ["Solid", "Courtyard", "Courtyard (Tower)", "Courtyard (Podium)",
                 "L-Shape", "U-Shape", "Split / Dual Bar"]
COURTYARD_ZONE_NAMES = ["Both", "Tower Only", "Podium Only"]

# Plan type helper flags
_is_courtyard = p_type in (1, 2, 3)
_courtyard_zone = p_type - 1 if _is_courtyard else -1
BASE_SHAPE_NAMES = ["Rectangle", "Ellipse", "Circle", "Chamfered", "Diamond", "H-Shape", "Cross"]

# ── Base footprint info ─────────────────────────────────────────────────────
bb, bb_min, bb_max = mh.get_bb(base_curve)
base_W = bb_max.X - bb_min.X
base_D = bb_max.Y - bb_min.Y
x0 = bb_min.X
y0 = bb_min.Y
centroid = mh.get_centroid(base_curve)

# ── Generate base shape from bounding box ──────────────────────────────────
if b_shape > 0:
    cx, cy = centroid.X, centroid.Y
    hw = base_W / 2.0 * b_scale
    hd = base_D / 2.0 * b_scale

    if b_shape == 1:
        el = rg.Ellipse(rg.Plane(rg.Point3d(cx, cy, 0), rg.Vector3d.ZAxis), hw, hd)
        base_curve = el.ToNurbsCurve()
    elif b_shape == 2:
        r = min(hw, hd)
        circle = rg.Circle(rg.Plane(rg.Point3d(cx, cy, 0), rg.Vector3d.ZAxis), r)
        base_curve = circle.ToNurbsCurve()
    elif b_shape == 3:
        ch = min(hw, hd) * 0.3
        pts = [
            rg.Point3d(cx - hw + ch, cy - hd, 0), rg.Point3d(cx + hw - ch, cy - hd, 0),
            rg.Point3d(cx + hw, cy - hd + ch, 0), rg.Point3d(cx + hw, cy + hd - ch, 0),
            rg.Point3d(cx + hw - ch, cy + hd, 0), rg.Point3d(cx - hw + ch, cy + hd, 0),
            rg.Point3d(cx - hw, cy + hd - ch, 0), rg.Point3d(cx - hw, cy - hd + ch, 0),
        ]
        pts.append(pts[0])
        base_curve = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])
    elif b_shape == 4:
        pts = [
            rg.Point3d(cx, cy - hd, 0), rg.Point3d(cx + hw, cy, 0),
            rg.Point3d(cx, cy + hd, 0), rg.Point3d(cx - hw, cy, 0),
        ]
        pts.append(pts[0])
        base_curve = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])
    elif b_shape == 5:
        fw = hw * 0.35
        wh = hd * 0.35
        pts = [
            rg.Point3d(cx - hw, cy - hd, 0), rg.Point3d(cx - hw + fw, cy - hd, 0),
            rg.Point3d(cx - hw + fw, cy - wh, 0), rg.Point3d(cx + hw - fw, cy - wh, 0),
            rg.Point3d(cx + hw - fw, cy - hd, 0), rg.Point3d(cx + hw, cy - hd, 0),
            rg.Point3d(cx + hw, cy + hd, 0), rg.Point3d(cx + hw - fw, cy + hd, 0),
            rg.Point3d(cx + hw - fw, cy + wh, 0), rg.Point3d(cx - hw + fw, cy + wh, 0),
            rg.Point3d(cx - hw + fw, cy + hd, 0), rg.Point3d(cx - hw, cy + hd, 0),
        ]
        pts.append(pts[0])
        base_curve = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])
    elif b_shape == 6:
        aw = hw * 0.4
        ad = hd * 0.4
        pts = [
            rg.Point3d(cx - aw, cy - hd, 0), rg.Point3d(cx + aw, cy - hd, 0),
            rg.Point3d(cx + aw, cy - ad, 0), rg.Point3d(cx + hw, cy - ad, 0),
            rg.Point3d(cx + hw, cy + ad, 0), rg.Point3d(cx + aw, cy + ad, 0),
            rg.Point3d(cx + aw, cy + hd, 0), rg.Point3d(cx - aw, cy + hd, 0),
            rg.Point3d(cx - aw, cy + ad, 0), rg.Point3d(cx - hw, cy + ad, 0),
            rg.Point3d(cx - hw, cy - ad, 0), rg.Point3d(cx - aw, cy - ad, 0),
        ]
        pts.append(pts[0])
        base_curve = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])

elif b_scale < 0.999:
    base_curve = mh.scale_curve(base_curve, b_scale, centroid)

# Recompute after shape generation
centroid = mh.get_centroid(base_curve)
base_area = mh.get_area(base_curve)
if base_area == 0:
    bb2 = base_curve.GetBoundingBox(True)
    base_area = (bb2.Max.X - bb2.Min.X) * (bb2.Max.Y - bb2.Min.Y)

# ── Coerce top_curve if provided ────────────────────────────────────────────
has_top_curve = top_curve is not None
_top_crv_input = None
if has_top_curve:
    if hasattr(top_curve, "DuplicateCurve"):
        _top_crv_input = top_curve
    elif hasattr(top_curve, "Geometry"):
        _top_crv_input = top_curve.Geometry
    else:
        import rhinoscriptsyntax as rs
        _top_crv_input = rs.coercecurve(top_curve)
        if _top_crv_input is None:
            raise Exception("top_curve: cannot coerce input to Curve (got {})".format(type(top_curve)))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 0: APPLY ORIENTATION + FIT TO SITE BOUNDARY
# ══════════════════════════════════════════════════════════════════════════════

_site_bnd = None
if site_boundary is not None:
    if hasattr(site_boundary, "DuplicateCurve"):
        _site_bnd = site_boundary
    elif hasattr(site_boundary, "Geometry"):
        _site_bnd = site_boundary.Geometry
    else:
        import rhinoscriptsyntax as rs
        _site_bnd = rs.coercecurve(site_boundary)

if abs(ori) > 0.001:
    base_curve = mh.rotate_curve(base_curve, ori, centroid)

_fit_scale = 1.0
if _site_bnd is not None and _site_bnd.IsClosed:
    def calc_fit_scale(crv, bnd, center):
        tol = 0.01
        n_samples = 64
        min_ratio = 1.0
        any_outside = False
        for i in range(n_samples):
            t = crv.Domain.ParameterAt(i / float(n_samples))
            pt = crv.PointAt(t)
            if bnd.Contains(pt, rg.Plane.WorldXY, tol) == rg.PointContainment.Outside:
                any_outside = True
                dx = pt.X - center.X
                dy = pt.Y - center.Y
                dist_pt = (dx*dx + dy*dy) ** 0.5
                if dist_pt < 0.001:
                    continue
                ray_line = rg.LineCurve(
                    rg.Point3d(center.X, center.Y, 0),
                    rg.Point3d(center.X + dx * 10, center.Y + dy * 10, 0))
                ix_events = rg.Intersect.Intersection.CurveCurve(ray_line, bnd, tol, tol)
                if ix_events:
                    for ev in ix_events:
                        bnd_pt = ev.PointA
                        dist_bnd = ((bnd_pt.X - center.X)**2 + (bnd_pt.Y - center.Y)**2) ** 0.5
                        if dist_bnd > 0.001:
                            ratio = dist_bnd / dist_pt
                            if ratio < min_ratio:
                                min_ratio = ratio
        if not any_outside:
            return 1.0
        return max(0.1, min_ratio * 0.98)

    _fit_scale = calc_fit_scale(base_curve, _site_bnd, centroid)
    if _fit_scale < 0.999:
        base_curve = mh.scale_curve(base_curve, _fit_scale, centroid)

# ── Resolve top curve ──────────────────────────────────────────────────────
fitted_centroid = mh.get_centroid(base_curve)
if has_top_curve:
    _top_crv = _top_crv_input
    if abs(ori) > 0.001:
        _top_crv = mh.rotate_curve(_top_crv, ori, centroid)
    if _fit_scale < 0.999:
        _top_crv = mh.scale_curve(_top_crv, _fit_scale, centroid)
else:
    _top_crv = base_curve.DuplicateCurve()

if p_top_scale != 1.0:
    _top_crv = mh.scale_curve(_top_crv, p_top_scale, fitted_centroid)
if p_top_offset_x != 0 or p_top_offset_y != 0:
    _top_crv = mh.offset_curve(_top_crv, p_top_offset_x, p_top_offset_y)

# Recompute from fitted base
bb, bb_min, bb_max = mh.get_bb(base_curve)
base_W = bb_max.X - bb_min.X
base_D = bb_max.Y - bb_min.Y
x0 = bb_min.X
y0 = bb_min.Y
centroid = mh.get_centroid(base_curve)
base_area = mh.get_area(base_curve)
if base_area == 0:
    base_area = base_W * base_D

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: INTERPOLATE BASE → TOP for each floor (section-aware)
# ══════════════════════════════════════════════════════════════════════════════
void_floors = set()
step_count = 0

def _interp(floor_idx):
    return mh.interpolate_curve(floor_idx, base_curve, _top_crv, nf)

envelope_curves = []

if s_type == 0:
    for i in range(nf + 1):
        envelope_curves.append(_interp(i))

elif s_type == 1:
    p_podium_floors = max(1, min(p_podium_floors, nf - 1))
    p_tower_ratio = max(0.2, min(p_tower_ratio, 0.9))
    for i in range(nf + 1):
        if i <= p_podium_floors:
            envelope_curves.append(_interp(i))
        else:
            interp = _interp(i)
            c = mh.get_centroid(interp)
            envelope_curves.append(mh.scale_curve(interp, p_tower_ratio, c))

elif s_type == 2:
    p_setback_interval = max(2, p_setback_interval)
    p_setback_depth = max(0.5, p_setback_depth)
    current_offset = 0.0
    for i in range(nf + 1):
        step_idx = i // p_setback_interval if i > 0 else 0
        current_offset = step_idx * p_setback_depth
        if step_idx > 0:
            step_count = step_idx
        step_base_floor = step_idx * p_setback_interval
        step_crv = _interp(step_base_floor)
        if current_offset > 0:
            step_crv = mh.offset_rect_inward(step_crv, current_offset)
        envelope_curves.append(step_crv)

elif s_type == 3:
    p_stilt_floors = max(1, min(p_stilt_floors, nf - 1))
    for i in range(nf + 1):
        envelope_curves.append(_interp(i))
    for i in range(0, p_stilt_floors):
        void_floors.add(i)

elif s_type == 4:
    p_garden_interval = max(3, p_garden_interval)
    p_garden_floors = max(1, min(p_garden_floors, p_garden_interval - 1))
    for i in range(nf + 1):
        envelope_curves.append(_interp(i))
    for i in range(1, nf + 1):
        if i % p_garden_interval == 0:
            for g in range(p_garden_floors):
                if i + g < nf:
                    void_floors.add(i + g)

else:
    s_type = 0
    for i in range(nf + 1):
        envelope_curves.append(_interp(i))

# Save unrotated envelope
_env_no_twist = [crv.DuplicateCurve() for crv in envelope_curves]

# Apply per-floor twist
_has_twist = abs(p_top_rotation) > 0.001 and not has_top_curve
if _has_twist:
    for i in range(len(envelope_curves)):
        t = float(i) / max(1, nf)
        angle = t * p_top_rotation
        if abs(angle) > 0.001:
            c_i = mh.get_centroid(envelope_curves[i])
            rad = math.radians(angle)
            xf = rg.Transform.Rotation(math.sin(rad), math.cos(rad),
                                        rg.Vector3d.ZAxis, c_i)
            envelope_curves[i].Transform(xf)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: BUILD FLOOR CURVES
# ══════════════════════════════════════════════════════════════════════════════
curves_out = []

p_courtyard_ratio = max(0.05, min(p_courtyard_ratio, 0.6))
p_void_corner = max(0, min(p_void_corner, 3))
p_void_ratio = max(0.2, min(p_void_ratio, 0.6))
p_bar_ratio = max(0.15, min(p_bar_ratio, 0.45))
p_split_gap = max(1.0, p_split_gap)
p_courtyard_zone = _courtyard_zone

for i in range(nf + 1):
    curves_out.append(mh.move_curve_z(envelope_curves[i], i * fh))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: GENERATE FLOOR SLABS (with plan voids applied)
# ══════════════════════════════════════════════════════════════════════════════
slabs_out = mh.generate_floor_slabs(
    nf, fh, void_floors, curves_out, envelope_curves,
    p_type, s_type, p_podium_floors,
    p_courtyard_ratio, p_void_corner, p_void_ratio,
    p_split_gap, p_bar_ratio,
    _is_courtyard, _courtyard_zone,
    _has_twist, p_top_rotation)

# ── Void cap slabs (sky garden / stilt) ────────────────────────────────────
slabs_out.extend(mh.generate_void_cap_slabs(
    void_floors, s_type, nf, fh, curves_out, envelope_curves,
    p_type, p_courtyard_ratio, p_void_corner, p_void_ratio,
    p_split_gap, p_bar_ratio,
    _is_courtyard, _has_twist, p_top_rotation))

# ── Step/podium transition cap slabs ──────────────────────────────────────
slabs_out.extend(mh.generate_step_cap_slabs(
    s_type, p_type, nf, fh, void_floors,
    envelope_curves, curves_out,
    p_courtyard_ratio, p_void_corner, p_void_ratio,
    p_split_gap, p_bar_ratio,
    _has_twist, p_top_rotation))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: GENERATE BUILDING MASS
# ══════════════════════════════════════════════════════════════════════════════
mass_parts = []

def _range_has_courtyard(f_bot, f_top):
    if not _is_courtyard:
        return False
    if s_type != 1:
        return True
    is_tower_range = f_bot >= p_podium_floors
    is_podium_range = f_top <= p_podium_floors
    if _courtyard_zone == 0:
        return True
    elif _courtyard_zone == 1:
        return is_tower_range
    elif _courtyard_zone == 2:
        return is_podium_range
    return True

def get_section_ranges():
    if s_type == 1:
        ranges = []
        if p_podium_floors > 0:
            ranges.append((0, p_podium_floors, 0))
        if p_podium_floors < nf:
            ranges.append((p_podium_floors, nf, p_podium_floors + 1))
        return ranges
    elif s_type == 2:
        ranges = []
        boundaries = [0]
        for i in range(1, nf + 1):
            if i % p_setback_interval == 0:
                boundaries.append(i)
        if boundaries[-1] != nf:
            boundaries.append(nf)
        for si in range(len(boundaries) - 1):
            fb = boundaries[si]
            ft = boundaries[si + 1]
            ranges.append((fb, ft, fb))
        return ranges
    elif s_type == 3:
        if p_stilt_floors < nf:
            return [(p_stilt_floors, nf, p_stilt_floors)]
        return []
    elif s_type == 4:
        ranges = []
        sorted_voids = sorted(void_floors)
        start = 0
        for vf in sorted_voids:
            if vf > start:
                ranges.append((start, vf, start))
            start = vf + 1
        if start <= nf:
            ranges.append((start, nf, start))
        return ranges if ranges else [(0, nf, 0)]
    else:
        return [(0, nf, 0)]

_section_ranges = get_section_ranges()
_flat_transition = s_type in (1, 2)
print("DEBUG mass gen: ranges={}, twist={}, plan={}".format(_section_ranges, _has_twist, p_type))

for (f_bot, f_top, crv_idx) in _section_ranges:
    if f_top <= f_bot:
        continue
    z_bot = f_bot * fh
    z_top = f_top * fh
    range_h = z_top - z_bot
    if range_h <= 0:
        continue

    m = None

    def _get_floor_crv(fi):
        if _flat_transition:
            crv = _env_no_twist[crv_idx].DuplicateCurve()
            if _has_twist:
                t = float(fi) / max(1, nf)
                angle = t * p_top_rotation
                if abs(angle) > 0.001:
                    ct = mh.get_centroid(crv)
                    rad = math.radians(angle)
                    xf = rg.Transform.Rotation(math.sin(rad), math.cos(rad),
                                                rg.Vector3d.ZAxis, ct)
                    crv.Transform(xf)
            return crv
        else:
            return envelope_curves[fi].DuplicateCurve()

    if _range_has_courtyard(f_bot, f_top):
        outer_crvs = []
        inner_crvs = []
        for fi in range(f_bot, f_top + 1):
            outer_fi = _get_floor_crv(fi)
            outer_crvs.append(mh.move_curve_z(outer_fi, fi * fh))
            c_fi = mh.get_centroid(outer_fi)
            inner_fi = mh.scale_curve(outer_fi, math.sqrt(p_courtyard_ratio), c_fi)
            inner_crvs.append(mh.move_curve_z(inner_fi, fi * fh))
        if len(outer_crvs) >= 2:
            m = mh.build_ring_mass(outer_crvs, inner_crvs)
        if not m:
            if _has_twist and len(outer_crvs) >= 2:
                m = mh.loft_curves(outer_crvs)
            else:
                crv_z = mh.move_curve_z(envelope_curves[crv_idx].DuplicateCurve(), z_bot)
                m = mh.extrude_curve_z(crv_z, range_h)
        print("  F{}-F{}: courtyard ring -> {}".format(
            f_bot, f_top, "OK solid={}".format(m.IsSolid) if m else "FAIL"))

    elif p_type >= 4:
        base_env_untw = _env_no_twist[crv_idx].DuplicateCurve()
        _be_bb, _be_mn, _be_mx = mh.get_bb(base_env_untw)
        _be_w = _be_mx.X - _be_mn.X
        _be_d = _be_mx.Y - _be_mn.Y
        _be_c = mh.get_centroid(base_env_untw)
        base_void_crv = None
        if p_type == 4:
            _vw = _be_w * p_void_ratio
            _vd = _be_d * p_void_ratio
            if p_void_corner == 0:
                _vx, _vy = _be_mx.X - _vw / 2.0, _be_mx.Y - _vd / 2.0
            elif p_void_corner == 1:
                _vx, _vy = _be_mn.X + _vw / 2.0, _be_mx.Y - _vd / 2.0
            elif p_void_corner == 2:
                _vx, _vy = _be_mn.X + _vw / 2.0, _be_mn.Y + _vd / 2.0
            else:
                _vx, _vy = _be_mx.X - _vw / 2.0, _be_mn.Y + _vd / 2.0
            base_void_crv = mh.make_rect_curve(_vx, _vy, _vw, _vd, 0)
        elif p_type == 5:
            _vw = _be_w * p_void_ratio
            _vd = _be_d * p_void_ratio
            base_void_crv = mh.make_rect_curve(_be_c.X, _be_mx.Y - _vd / 2.0, _vw, _vd, 0)
        elif p_type == 6:
            _vgap = min(p_split_gap, _be_w - _be_w * p_bar_ratio * 2)
            if _vgap < 1.0:
                _vgap = 1.0
            base_void_crv = mh.make_rect_curve(_be_c.X, _be_c.Y, _vgap, _be_d + 2, 0)

        base_pieces = mh.apply_void_2d(base_env_untw, base_void_crv)
        print("  F{}-F{}: L/U/split 2D boolean -> {} pieces (once on untwisted)".format(
            f_bot, f_top, len(base_pieces)))

        if len(base_pieces) > 1 or (len(base_pieces) == 1 and base_void_crv is not None):
            for pi_idx, base_piece in enumerate(base_pieces):
                loft_crvs = []
                for fi in range(f_bot, f_top + 1):
                    pc = base_piece.DuplicateCurve()
                    pc_c = mh.get_centroid(pc)
                    if not _flat_transition:
                        fi_env = _env_no_twist[fi]
                        fi_bb = fi_env.GetBoundingBox(True)
                        fi_w = fi_bb.Max.X - fi_bb.Min.X
                        fi_d = fi_bb.Max.Y - fi_bb.Min.Y
                        sx = fi_w / _be_w if _be_w > 0.001 else 1.0
                        sy = fi_d / _be_d if _be_d > 0.001 else 1.0
                        if abs(sx - 1.0) > 0.001 or abs(sy - 1.0) > 0.001:
                            xf_s = rg.Transform.Scale(rg.Plane(pc_c, rg.Vector3d.ZAxis), sx, sy, 1.0)
                            pc.Transform(xf_s)
                            fi_c = mh.get_centroid(fi_env)
                            new_c = mh.get_centroid(pc)
                            dx = fi_c.X - new_c.X
                            dy = fi_c.Y - new_c.Y
                            if abs(dx) > 0.001 or abs(dy) > 0.001:
                                pc.Translate(rg.Vector3d(dx, dy, 0))
                    if _has_twist:
                        t = float(fi) / max(1, nf)
                        angle = t * p_top_rotation
                        if abs(angle) > 0.001:
                            rad = math.radians(angle)
                            xf = rg.Transform.Rotation(math.sin(rad), math.cos(rad),
                                                        rg.Vector3d.ZAxis, _be_c)
                            pc.Transform(xf)
                    loft_crvs.append(mh.move_curve_z(pc, fi * fh))

                if len(loft_crvs) >= 2:
                    pm = mh.loft_curves(loft_crvs)
                    if pm:
                        mass_parts.append(pm)
                        print("    piece[{}]: loft {} crvs -> solid={}".format(
                            pi_idx, len(loft_crvs), pm.IsSolid))
                    else:
                        pm = mh.extrude_curve_z(loft_crvs[0], range_h)
                        if pm:
                            mass_parts.append(pm)
                            print("    piece[{}]: loft failed, extrude -> solid={}".format(
                                pi_idx, pm.IsSolid))
                        else:
                            print("    piece[{}]: all methods FAILED".format(pi_idx))
        else:
            crv_z = mh.move_curve_z(_env_no_twist[crv_idx].DuplicateCurve(), z_bot)
            m = mh.extrude_curve_z(crv_z, range_h)
            if m:
                mass_parts.append(m)
            print("  F{}-F{}: L/U/split boolean failed, solid fallback -> {}".format(
                f_bot, f_top, "OK" if m else "FAIL"))
        m = None

    elif _has_twist:
        loft_crvs = []
        for fi in range(f_bot, f_top + 1):
            loft_crvs.append(mh.move_curve_z(_get_floor_crv(fi), fi * fh))
        if len(loft_crvs) >= 2:
            m = mh.loft_curves(loft_crvs)
        print("  F{}-F{}: twist loft (flat={}) -> {} solid={}".format(
            f_bot, f_top, _flat_transition, "OK" if m else "FAIL",
            m.IsSolid if m else "n/a"))

    else:
        crv_z = mh.move_curve_z(envelope_curves[crv_idx].DuplicateCurve(), z_bot)
        m = mh.extrude_curve_z(crv_z, range_h)
        print("  F{}-F{}: extrude -> {} solid={}".format(
            f_bot, f_top, "OK" if m else "FAIL",
            m.IsSolid if m else "n/a"))

    if m:
        mass_parts.append(m)
print("DEBUG mass gen: {} parts".format(len(mass_parts)))

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4b: COLUMNS (stilt / sky garden)
# ══════════════════════════════════════════════════════════════════════════════
_core_cx = centroid.X
_core_cy = centroid.Y
_core_cs = max(2.0, round(min(base_W, base_D) * 0.18, 2)) if p_lateral_system == 0 else 0
_core_hs = _core_cs / 2.0 + 0.3 if _core_cs > 0 else 0

_stilt_col_breps = []

_col_args = dict(
    envelope_curves=envelope_curves, nf=nf, fh=fh,
    p_stilt_col_size=p_stilt_col_size, p_stilt_col_shape=p_stilt_col_shape,
    b_shape=b_shape, p_type=p_type,
    p_courtyard_ratio=p_courtyard_ratio, p_void_corner=p_void_corner,
    p_void_ratio=p_void_ratio, p_split_gap=p_split_gap, p_bar_ratio=p_bar_ratio,
    has_twist=_has_twist, p_top_rotation=p_top_rotation,
    core_cx=_core_cx, core_cy=_core_cy, core_hs=_core_hs,
    env_no_twist=_env_no_twist, ori=ori)

if s_type == 3:
    _stilt_col_breps.extend(mh.add_columns(0, p_stilt_floors * fh, p_stilt_col_span, **_col_args))

if s_type == 4 and len(void_floors) > 0:
    sorted_voids = sorted(void_floors)
    void_start = sorted_voids[0]
    prev = sorted_voids[0]
    for vf in sorted_voids[1:]:
        if vf != prev + 1:
            _stilt_col_breps.extend(mh.add_columns(void_start * fh, (prev + 1 - void_start) * fh,
                                                    p_stilt_col_span, **_col_args))
            void_start = vf
        prev = vf
    _stilt_col_breps.extend(mh.add_columns(void_start * fh, (prev + 1 - void_start) * fh,
                                            p_stilt_col_span, **_col_args))

# Fallback mass
if len(mass_parts) == 0:
    try:
        ext = rg.Extrusion.Create(base_curve, height, True)
        if ext:
            mass_parts.append(ext.ToBrep(True))
    except:
        pass
if len(mass_parts) == 0:
    fb = rg.Brep.CreateFromBox(rg.Box(rg.Plane.WorldXY,
        rg.Interval(bb_min.X, bb_max.X), rg.Interval(bb_min.Y, bb_max.Y), rg.Interval(0, height)))
    if fb:
        mass_parts.append(fb)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5: COMPUTE METRICS
# ══════════════════════════════════════════════════════════════════════════════
total_area = 0.0
for slab in slabs_out:
    ap = rg.AreaMassProperties.Compute(slab)
    if ap:
        total_area += ap.Area

base_case_area = base_area * (nf + 1)
eff = total_area / base_case_area if base_case_area > 0 else 1.0

vol = 0.0
for part in mass_parts:
    vp = rg.VolumeMassProperties.Compute(part)
    if vp:
        vol += abs(vp.Volume)

# ── Outputs ──────────────────────────────────────────────────────────────────
floor_curves  = curves_out
floor_slabs   = slabs_out
building_mass = mass_parts
stilt_columns = _stilt_col_breps
massing_area   = round(total_area, 1)
massing_volume = round(vol, 1)
efficiency     = round(eff, 3)

# ── Summary ──────────────────────────────────────────────────────────────────
s_name = SECTION_NAMES[s_type] if s_type < len(SECTION_NAMES) else "Unknown"
p_name = PLAN_NAMES[p_type] if p_type < len(PLAN_NAMES) else "Unknown"

detail_parts = []
if has_top_curve:
    detail_parts.append("top_curve=connected")
else:
    if p_top_scale != 1.0:
        detail_parts.append("top_scale={:.0%}".format(p_top_scale))
    if p_top_offset_x != 0 or p_top_offset_y != 0:
        detail_parts.append("top_offset=({:.1f}, {:.1f})".format(p_top_offset_x, p_top_offset_y))
    if p_top_rotation != 0:
        detail_parts.append("top_rot={:.0f} deg".format(p_top_rotation))

if s_type == 1:
    detail_parts.append("podium={}F, tower_ratio={:.0%}".format(p_podium_floors, p_tower_ratio))
elif s_type == 2:
    detail_parts.append("step every {}F, depth={:.1f}m ({} steps)".format(p_setback_interval, p_setback_depth, step_count))
elif s_type == 3:
    detail_parts.append("stilt={}F ({:.1f}m open)".format(p_stilt_floors, p_stilt_floors * fh))
elif s_type == 4:
    detail_parts.append("garden every {}F, {}F open ({} voids)".format(p_garden_interval, p_garden_floors, len(void_floors)))

if _is_courtyard:
    cz_name = COURTYARD_ZONE_NAMES[_courtyard_zone] if 0 <= _courtyard_zone < len(COURTYARD_ZONE_NAMES) else "Both"
    zone_str = " zone={}".format(cz_name) if s_type == 1 and _courtyard_zone > 0 else ""
    detail_parts.append("courtyard={:.0%}{}".format(p_courtyard_ratio, zone_str))
elif p_type == 4:
    corner_names = ["NE", "NW", "SW", "SE"]
    detail_parts.append("L-void corner={}, ratio={:.0%}".format(corner_names[p_void_corner], p_void_ratio))
elif p_type == 5:
    detail_parts.append("U-void={:.0%}".format(p_void_ratio))
elif p_type == 6:
    detail_parts.append("2 bars {:.1f}m wide, {:.1f}m gap".format(base_W * p_bar_ratio, p_split_gap))

b_name = BASE_SHAPE_NAMES[b_shape] if b_shape < len(BASE_SHAPE_NAMES) else "Unknown"
print("MASSING: Base={} + Section={} + Plan={}".format(b_name, s_name, p_name))
print("Floors: {} x {:.1f}m = {:.1f}m total".format(nf, fh, height))
if detail_parts:
    print("Params: {}".format(", ".join(detail_parts)))
if len(void_floors) > 0:
    print("Void floors: {} ({} open)".format(sorted(void_floors), len(void_floors)))
print("GFA: {:.1f} m2  |  Volume: {:.1f} m3".format(total_area, vol))
print("Efficiency vs base: {:.1%}".format(eff))
print("Footprint: {:.1f} x {:.1f}m ({:.1f} m2)".format(base_W, base_D, base_area))
print("Mass parts: {}".format(len(mass_parts)))
print("Orientation: {:.1f} deg{}".format(ori, " (scaled to {:.0%} to fit site)".format(_fit_scale) if _fit_scale < 0.999 else ""))
print("Top params: scale={:.3f} offset=({:.1f},{:.1f}) rot={:.1f} has_top_curve={}".format(p_top_scale, p_top_offset_x, p_top_offset_y, p_top_rotation, has_top_curve))

# ── Export JSON bundle ─────────────────────────────────────────────────────
_massing_export = {
    "baseShape": b_shape,
    "baseShapeName": b_name,
    "baseScale": round(b_scale, 3),
    "sectionType": s_type,
    "sectionTypeName": s_name,
    "planType": p_type,
    "planTypeName": p_name,
    "massingArea": round(total_area, 1),
    "massingVolume": round(vol, 1),
    "efficiency": round(eff, 3),
    "floors": nf,
    "floorHeight": fh,
    "orientation": ori,
    "topCurveConnected": has_top_curve,
    "params": {}
}
if not has_top_curve:
    if p_top_scale != 1.0:
        _massing_export["params"]["topScale"] = round(p_top_scale, 3)
    if p_top_offset_x != 0:
        _massing_export["params"]["topOffsetX"] = round(p_top_offset_x, 2)
    if p_top_offset_y != 0:
        _massing_export["params"]["topOffsetY"] = round(p_top_offset_y, 2)
    if p_top_rotation != 0:
        _massing_export["params"]["topRotation"] = round(p_top_rotation, 1)
if s_type == 1:
    _massing_export["params"]["podiumFloors"] = p_podium_floors
    _massing_export["params"]["towerRatio"] = round(p_tower_ratio, 3)
elif s_type == 2:
    _massing_export["params"]["setbackInterval"] = p_setback_interval
    _massing_export["params"]["setbackDepth"] = round(p_setback_depth, 2)
elif s_type == 3:
    _massing_export["params"]["stiltFloors"] = p_stilt_floors
elif s_type == 4:
    _massing_export["params"]["gardenInterval"] = p_garden_interval
    _massing_export["params"]["gardenFloors"] = p_garden_floors
if _is_courtyard:
    _massing_export["params"]["courtyardRatio"] = round(p_courtyard_ratio, 3)
    _massing_export["params"]["courtyardZone"] = _courtyard_zone
    _massing_export["params"]["courtyardZoneName"] = COURTYARD_ZONE_NAMES[_courtyard_zone] if 0 <= _courtyard_zone < len(COURTYARD_ZONE_NAMES) else "Both"
elif p_type == 4:
    _massing_export["params"]["voidCorner"] = p_void_corner
    _massing_export["params"]["voidRatio"] = round(p_void_ratio, 3)
elif p_type == 5:
    _massing_export["params"]["voidRatio"] = round(p_void_ratio, 3)
elif p_type == 6:
    _massing_export["params"]["splitGap"] = round(p_split_gap, 2)
    _massing_export["params"]["barRatio"] = round(p_bar_ratio, 3)

export_json = json.dumps(_massing_export)
