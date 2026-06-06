# ArchSim Window Visualiser — Rhino 8 / Python 3
# ─────────────────────────────────────────────────────────────────────────────
# Generates window/wall panels per floor using per-floor curves from massing.
# Handles taper, twist, podium/tower, stepped, stilt, sky garden, and plan voids.
#
# INPUTS:
#   floor_curves     List[Curve] — Per-floor curves from massing (or structure)
#   floor_slabs      List[Brep]  — Per-floor slab breps from massing (optional, for void detection)
#   floors           Integer     — Number of floors
#   floor_height     Number      — Floor-to-floor height m
#   wwRatio          Number      — Window-to-wall ratio 0.0–1.0
#   window_type      Integer     — 0=Ribbon  1=CurtainWall  2=Punched  3=Vertical
#   bay_spacing      Number      — Bay/mullion spacing m (default 1.5)
#   section_type     Integer     — 0=Straight 1=Podium+Tower 2=Stepped 3=Stilt 4=SkyGarden
#   stilt_floors     Integer     — Open ground floors (section_type=3)
#   garden_interval  Integer     — Sky garden every N floors (section_type=4, default 6)
#   garden_floors    Integer     — Sky garden floor count (section_type=4, default 1)
#   plan_type        Integer     — 0=Solid 1..3=Courtyard 4=L 5=U 6=Split
#   courtyard_ratio  Number      — Courtyard void ratio
#   void_corner      Integer     — Corner for L (0=NE 1=NW 2=SW 3=SE)
#   void_ratio       Number      — Void ratio for L/U
#   split_gap        Number      — Gap between bars (m)
#   bar_ratio        Number      — Width ratio per bar
#
# OUTPUTS:
#   windows       List[Brep] — Glazing surfaces  → Custom Preview: blue
#   wall_panels   List[Brep] — Opaque surfaces   → Custom Preview: grey
#   mullion_lines List[Curve]                    → Custom Preview: dark
#   export_json   String     — JSON bundle (connect to gh-params-export)
#   out           String     — Debug/summary
# ─────────────────────────────────────────────────────────────────────────────

import Rhino.Geometry as rg
import math
import json
import sys
import os

# ── Import structure_helpers for void curve generation ────────────────────────
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
    _this_dir = os.path.dirname(os.path.abspath(__file__))
    if _this_dir not in sys.path:
        sys.path.insert(0, _this_dir)
except:
    pass

import structure_helpers as sh

# ── Parameters ────────────────────────────────────────────────────────────────
_wwr    = max(0.0, min(1.0, float(wwRatio)       if wwRatio       is not None else 0.4))
_fh     = float(floor_height)  if floor_height    is not None else 3.6
_nf     = int(floors)          if floors           is not None else 10
_wtype  = int(window_type)     if window_type      is not None else 0
_bay    = float(bay_spacing)   if bay_spacing      is not None else 1.5
_stype  = int(section_type)    if section_type     is not None else 0
_ptype  = int(plan_type)       if plan_type        is not None else 0

_stilt_fl    = int(stilt_floors)     if "stilt_floors"     in dir() and stilt_floors     is not None else 2
_garden_int  = int(garden_interval)  if "garden_interval"  in dir() and garden_interval  is not None else 6
_garden_fl   = int(garden_floors)    if "garden_floors"    in dir() and garden_floors    is not None else 1
_court_ratio = float(courtyard_ratio) if "courtyard_ratio" in dir() and courtyard_ratio is not None else 0.25
_void_corner = int(void_corner)      if "void_corner"      in dir() and void_corner     is not None else 0
_void_ratio  = float(void_ratio)     if "void_ratio"       in dir() and void_ratio      is not None else 0.3
_split_gap   = float(split_gap)      if "split_gap"        in dir() and split_gap        is not None else 3.0
_bar_ratio   = float(bar_ratio)      if "bar_ratio"        in dir() and bar_ratio        is not None else 0.35

# ── Coerce floor_curves ──────────────────────────────────────────────────────
_fc_list = []
if "floor_curves" in dir() and floor_curves is not None:
    for fc in floor_curves:
        if fc is not None:
            c = fc if hasattr(fc, "GetLength") else None
            if c is None:
                try:
                    import rhinoscriptsyntax as rs
                    c = rs.coercecurve(fc)
                except:
                    pass
            if c is not None:
                _fc_list.append(c)

if len(_fc_list) == 0:
    out = "ERROR: No floor_curves provided"
    windows = []; wall_panels = []; mullion_lines = []
    export_json = json.dumps({"wwRatio": _wwr, "windowType": _wtype, "baySpacing": _bay})
    raise Exception(out)

# ── Determine void floors (no windows at these levels) ────────────────────────
_void_floors = set()
if _stype == 3:  # Stilt — open ground floors have no facade
    _stilt_fl = max(1, min(_stilt_fl, _nf - 1))
    for vi in range(0, _stilt_fl):
        _void_floors.add(vi)
elif _stype == 4:  # Sky Garden
    _garden_fl = min(_garden_fl, _garden_int - 1)
    for i in range(1, _nf + 1):
        if i % _garden_int == 0:
            for g in range(_garden_fl):
                vi = i + g
                if vi < _nf:
                    _void_floors.add(vi)

# ── Plan void detection ──────────────────────────────────────────────────────
_is_courtyard = _ptype in (1, 2, 3)
_has_plan_void = _ptype > 0

# Build untwisted floor curves for void generation (just flatten Z to 0)
_fc_notwist = []
for fc in _fc_list:
    c = fc.DuplicateCurve()
    bb = c.GetBoundingBox(True)
    if abs(bb.Min.Z) > 0.01:
        c.Translate(rg.Vector3d(0, 0, -bb.Min.Z))
    _fc_notwist.append(c)

def _make_void(fi):
    """Generate plan void curve for floor fi."""
    if not _has_plan_void:
        return None
    idx = min(fi, len(_fc_notwist) - 1)
    return sh.make_void_for_floor(idx, _fc_notwist, _ptype, _is_courtyard,
                                  _court_ratio, _void_corner, _void_ratio,
                                  _split_gap, _bar_ratio)

# ── Quad Brep helper ──────────────────────────────────────────────────────────
def Q(a, b, c, d):
    """Planar quad Brep from 4 Point3d corners [BL, BR, TR, TL]."""
    ns = rg.NurbsSurface.CreateFromCorners(a, b, c, d)
    if ns:
        return ns.ToBrep()
    return None

# ── Segment extraction helper ─────────────────────────────────────────────────
def get_segments(crv, max_seg_len=1.5):
    """Extract facade segments from a curve.
    Linear segments are kept whole (or subdivided only if very long).
    Curved segments (arcs, ellipses) are subdivided into short straight pieces."""
    total_len = crv.GetLength()
    if total_len < 0.1:
        return []

    # Get sub-segments from the curve
    raw_segs = list(crv.DuplicateSegments())

    # If only 1 segment and closed (full ellipse/circle), subdivide directly
    if len(raw_segs) <= 1 and crv.IsClosed:
        n = max(8, int(math.ceil(total_len / max_seg_len)))
        result = []
        for i in range(n):
            p0 = crv.PointAtNormalizedLength(float(i) / n)
            p1 = crv.PointAtNormalizedLength(float(i + 1) / n)
            if p0.DistanceTo(p1) > 0.01:
                result.append(rg.LineCurve(p0, p1))
        return result

    # Process each segment individually: keep linear, subdivide curved
    result = []
    for seg in raw_segs:
        seg_len = seg.GetLength()
        if seg_len < 0.05:
            continue

        # Check if this segment is linear
        _is_linear = False
        try:
            _is_linear = seg.IsLinear(0.05)
        except:
            pass
        if not _is_linear and isinstance(seg, rg.LineCurve):
            _is_linear = True

        if _is_linear:
            # Linear segment: keep as single piece (facade uses full edge)
            result.append(seg)
        else:
            # Curved segment: subdivide into short straight pieces
            n = max(3, int(math.ceil(seg_len / max_seg_len)))
            for i in range(n):
                p0 = seg.PointAtNormalizedLength(float(i) / n)
                p1 = seg.PointAtNormalizedLength(min(float(i + 1) / n, 1.0))
                if p0.DistanceTo(p1) > 0.01:
                    result.append(rg.LineCurve(p0, p1))

    # Fallback: if nothing worked, subdivide the entire curve
    if len(result) == 0 and total_len > 0.1:
        n = max(8, int(math.ceil(total_len / max_seg_len)))
        for i in range(n):
            p0 = crv.PointAtNormalizedLength(float(i) / n)
            p1 = crv.PointAtNormalizedLength(float(i + 1) / n)
            if p0.DistanceTo(p1) > 0.01:
                result.append(rg.LineCurve(p0, p1))
    return result

# ── Generate facade panels for one edge segment at one floor ──────────────────
def _calc_bays(seg_len, bay):
    """Calculate bay count and width, keeping bays as close to target as possible.
    Uses floor to get full bays at target width, remainder absorbed into last bay."""
    if seg_len <= bay * 1.3:
        # Short segment: single bay
        return 1, seg_len
    n_full = int(math.floor(seg_len / bay))
    remainder = seg_len - n_full * bay
    # If remainder is too small (<30% of bay), merge into last full bay
    if remainder < bay * 0.3 and n_full > 1:
        return n_full, seg_len / n_full
    # If remainder is large enough, add as extra bay
    elif remainder >= bay * 0.3:
        return n_full + 1, seg_len / (n_full + 1)
    else:
        return max(1, n_full), seg_len / max(1, n_full)

def gen_panels(A, B, z0, fh, wwr, wtype, bay, wins, walls, mulls):
    """Generate window/wall panels for a single edge from A to B at floor z0."""
    dx = B.X - A.X
    dy = B.Y - A.Y
    seg_len = (dx*dx + dy*dy) ** 0.5
    if seg_len < 0.1:
        return
    ux = dx / seg_len
    uy = dy / seg_len
    ztop = z0 + fh

    def P(t, z):
        return rg.Point3d(A.X + ux * t, A.Y + uy * t, z)

    # ── TYPE 0 : Ribbon ──────────────────────────────────────────────────
    if wtype == 0:
        win_h  = fh * wwr
        sill_h = (fh - win_h) / 2.0
        gz0    = z0 + sill_h
        gz1    = gz0 + win_h

        if sill_h > 0.001:
            s = Q(P(0,z0), P(seg_len,z0), P(seg_len,gz0), P(0,gz0))
            if s: walls.append(s)
        if win_h > 0.001:
            s = Q(P(0,gz0), P(seg_len,gz0), P(seg_len,gz1), P(0,gz1))
            if s: wins.append(s)
        if ztop - gz1 > 0.001:
            s = Q(P(0,gz1), P(seg_len,gz1), P(seg_len,ztop), P(0,ztop))
            if s: walls.append(s)

    # ── TYPE 1 : Curtain Wall ────────────────────────────────────────────
    elif wtype == 1:
        spandrel = max(0.04, fh * (1.0 - wwr) / 2.0)
        gz0 = z0   + spandrel
        gz1 = ztop - spandrel

        n_bays, bay_w = _calc_bays(seg_len, bay)
        pier   = bay_w * 0.04

        if spandrel > 0.001:
            s = Q(P(0,z0),  P(seg_len,z0),  P(seg_len,gz0), P(0,gz0))
            if s: walls.append(s)
            s = Q(P(0,gz1), P(seg_len,gz1), P(seg_len,ztop), P(0,ztop))
            if s: walls.append(s)

        for b in range(n_bays):
            t0 = b * bay_w
            t1 = t0 + bay_w
            if gz1 - gz0 > 0.001:
                s = Q(P(t0+pier,gz0), P(t1-pier,gz0), P(t1-pier,gz1), P(t0+pier,gz1))
                if s: wins.append(s)
            if pier > 0.001:
                s = Q(P(t0,gz0),      P(t0+pier,gz0), P(t0+pier,gz1), P(t0,gz1))
                if s: walls.append(s)
                s = Q(P(t1-pier,gz0), P(t1,gz0),      P(t1,gz1),      P(t1-pier,gz1))
                if s: walls.append(s)
            if b > 0:
                mulls.append(rg.Line(P(t0,z0), P(t0,ztop)).ToNurbsCurve())

    # ── TYPE 2 : Punched ─────────────────────────────────────────────────
    elif wtype == 2:
        n_bays, bay_w = _calc_bays(seg_len, bay)
        win_w  = bay_w  * wwr
        pier   = (bay_w - win_w) / 2.0
        win_h  = fh * wwr
        sill_h = (fh - win_h) / 2.0
        gz0    = z0 + sill_h
        gz1    = gz0 + win_h

        for b in range(n_bays):
            t0  = b * bay_w
            t1  = t0 + bay_w
            tbl = t0 + pier
            tbr = tbl + win_w

            if pier > 0.001:
                s = Q(P(t0,z0),  P(tbl,z0),  P(tbl,ztop), P(t0,ztop))
                if s: walls.append(s)
                s = Q(P(tbr,z0), P(t1,z0),   P(t1,ztop),  P(tbr,ztop))
                if s: walls.append(s)
            if sill_h > 0.001:
                s = Q(P(tbl,z0),  P(tbr,z0),  P(tbr,gz0),  P(tbl,gz0))
                if s: walls.append(s)
            if ztop - gz1 > 0.001:
                s = Q(P(tbl,gz1), P(tbr,gz1), P(tbr,ztop), P(tbl,ztop))
                if s: walls.append(s)
            s = Q(P(tbl,gz0), P(tbr,gz0), P(tbr,gz1), P(tbl,gz1))
            if s: wins.append(s)

    # ── TYPE 3 : Vertical Strip ──────────────────────────────────────────
    elif wtype == 3:
        n_bays, bay_w = _calc_bays(seg_len, bay)
        win_w  = bay_w  * wwr
        pier   = (bay_w - win_w) / 2.0
        sill_h = fh * 0.08
        gz0    = z0   + sill_h
        gz1    = ztop - sill_h

        for b in range(n_bays):
            t0  = b * bay_w
            t1  = t0 + bay_w
            tbl = t0 + pier
            tbr = tbl + win_w

            if pier > 0.001:
                s = Q(P(t0,z0),  P(tbl,z0),  P(tbl,ztop), P(t0,ztop))
                if s: walls.append(s)
                s = Q(P(tbr,z0), P(t1,z0),   P(t1,ztop),  P(tbr,ztop))
                if s: walls.append(s)
            if sill_h > 0.001:
                s = Q(P(tbl,z0),  P(tbr,z0),  P(tbr,gz0),  P(tbl,gz0))
                if s: walls.append(s)
                s = Q(P(tbl,gz1), P(tbr,gz1), P(tbr,ztop), P(tbl,ztop))
                if s: walls.append(s)
            s = Q(P(tbl,gz0), P(tbr,gz0), P(tbr,gz1), P(tbl,gz1))
            if s: wins.append(s)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN: Generate windows per floor
# ══════════════════════════════════════════════════════════════════════════════
windows_out       = []
wall_panels_out   = []
mullion_lines_out = []
debug_lines       = []

debug_lines.append("floors={}, fc_count={}, wtype={}, wwr={}, bay={}, void_floors={}".format(
    _nf, len(_fc_list), _wtype, _wwr, _bay, sorted(_void_floors)))

_win_floors = 0
for fi in range(_nf):
    z0 = fi * _fh

    # Skip void floors (stilt open, sky garden open)
    if fi in _void_floors:
        debug_lines.append("  fi={}: void — skip".format(fi))
        continue

    # Get floor curve for this level
    fc_idx = min(fi, len(_fc_list) - 1)
    fc = _fc_list[fc_idx]

    # Flatten curve to Z=0 for segment extraction, then use z0 for panel placement
    fc_flat = fc.DuplicateCurve()
    fc_bb = fc_flat.GetBoundingBox(True)
    if abs(fc_bb.Min.Z) > 0.01:
        fc_flat.Translate(rg.Vector3d(0, 0, -fc_bb.Min.Z))

    _fc_len = fc_flat.GetLength()
    _fc_closed = fc_flat.IsClosed

    # ── Detect setback: if next floor has a smaller footprint ──────────────
    # Podium/Tower (s_type=1): REPLACE outer facade with smaller (tower) curve
    #   — the podium perimeter at transition is a roof, not a wall
    # Stepped (s_type=2) and others: keep current floor's curve as-is
    #   — each step floor uses its own footprint for the facade
    _facade_crv = fc_flat  # default: use this floor's curve
    _is_setback = False
    if fi + 1 < _nf and fi + 1 not in _void_floors:
        next_idx = min(fi + 1, len(_fc_list) - 1)
        next_fc = _fc_list[next_idx]
        next_flat = next_fc.DuplicateCurve()
        next_bb = next_flat.GetBoundingBox(True)
        if abs(next_bb.Min.Z) > 0.01:
            next_flat.Translate(rg.Vector3d(0, 0, -next_bb.Min.Z))

        cur_bb = fc_flat.GetBoundingBox(True)
        cur_w = cur_bb.Max.X - cur_bb.Min.X
        cur_d = cur_bb.Max.Y - cur_bb.Min.Y
        nxt_bb = next_flat.GetBoundingBox(True)
        nxt_w = nxt_bb.Max.X - nxt_bb.Min.X
        nxt_d = nxt_bb.Max.Y - nxt_bb.Min.Y
        if (nxt_w < cur_w * 0.9) or (nxt_d < cur_d * 0.9):
            _is_setback = True
            # Only replace facade for podium/tower — transition is a roof
            if _stype == 1:
                _facade_crv = next_flat
            debug_lines.append("    setback at fi={}: {}x{} -> {}x{} replace={}".format(
                fi, round(cur_w,1), round(cur_d,1), round(nxt_w,1), round(nxt_d,1), _stype == 1))

    # ── Get void curve for this floor (needed for facade filtering) ─────
    # If facade was replaced with next floor's (tower) curve at setback,
    # use the tower floor's void so it matches the facade size.
    _void_fi = fi
    if _is_setback and _stype == 1:
        _void_fi = min(fi + 1, _nf)
    _void_crv = _make_void(_void_fi) if _has_plan_void else None

    # ── Build facade outline ──────────────────────────────────────────────
    _n_outer = 0
    _n_inner = 0

    if _void_crv is not None and _void_crv.IsClosed:
        if _ptype in (4, 5, 6):
            # L/U/Split: use boolean difference to get the actual slab outline.
            # This single curve follows the building plate exactly — outer edges
            # follow the envelope, void-facing edges follow the void boundary.
            _slab_crvs = []
            try:
                diff = rg.Curve.CreateBooleanDifference(_facade_crv, _void_crv, 0.001)
                if diff and len(diff) > 0:
                    _slab_crvs = list(diff)
            except:
                pass
            if not _slab_crvs:
                _slab_crvs = [_facade_crv]

            for _sc in _slab_crvs:
                try:
                    segs = get_segments(_sc)
                except:
                    segs = []
                for seg in segs:
                    A = seg.PointAtStart
                    B = seg.PointAtEnd
                    gen_panels(A, B, z0, _fh, _wwr, _wtype, _bay,
                               windows_out, wall_panels_out, mullion_lines_out)
                    _n_outer += 1

        elif _is_courtyard:
            # Courtyard: outer perimeter + inner ring as separate facades
            try:
                outer_segs = get_segments(_facade_crv)
            except:
                outer_segs = []
            for seg in outer_segs:
                A = seg.PointAtStart
                B = seg.PointAtEnd
                gen_panels(A, B, z0, _fh, _wwr, _wtype, _bay,
                           windows_out, wall_panels_out, mullion_lines_out)
                _n_outer += 1

            inner_segs = get_segments(_void_crv)
            for seg in inner_segs:
                A = seg.PointAtStart
                B = seg.PointAtEnd
                gen_panels(A, B, z0, _fh, _wwr, _wtype, _bay,
                           windows_out, wall_panels_out, mullion_lines_out)
                _n_inner += 1
    else:
        # Solid plan or no void: just the outer facade
        try:
            outer_segs = get_segments(_facade_crv)
        except:
            outer_segs = []
        for seg in outer_segs:
            A = seg.PointAtStart
            B = seg.PointAtEnd
            gen_panels(A, B, z0, _fh, _wwr, _wtype, _bay,
                       windows_out, wall_panels_out, mullion_lines_out)
            _n_outer += 1

    debug_lines.append("  fi={}: idx={} len={:.1f} closed={} outer={} inner={}".format(
        fi, fc_idx, _fc_len, _fc_closed, _n_outer, _n_inner))
    _win_floors += 1

# ══════════════════════════════════════════════════════════════════════════════
# OUTPUTS
# ══════════════════════════════════════════════════════════════════════════════
windows       = windows_out
wall_panels   = wall_panels_out
mullion_lines = mullion_lines_out

debug_lines.append("RESULT: {} floors, {} windows, {} walls, {} mullions".format(
    _win_floors, len(windows_out), len(wall_panels_out), len(mullion_lines_out)))
out = "\n".join(debug_lines)

# ── Export JSON bundle (connect to gh-params-export windows input) ────────────
export_json = json.dumps({
    "wwRatio": round(_wwr, 3),
    "windowType": _wtype,
    "baySpacing": round(_bay, 3),
    "windowFloors": _win_floors,
    "windowCount": len(windows_out),
    "wallPanelCount": len(wall_panels_out)
})
