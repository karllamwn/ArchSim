# ArchSim Massing Helpers
# ─────────────────────────────────────────────────────────────────────────────
# Pure geometry utilities and helper functions for gh-massing.py.
# All functions take explicit parameters — no module-level state.
# ─────────────────────────────────────────────────────────────────────────────

import Rhino.Geometry as rg
import math
import System

# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════

def get_bb(crv):
    bb = crv.GetBoundingBox(True)
    return bb, bb.Min, bb.Max

def get_centroid(crv):
    ap = rg.AreaMassProperties.Compute(crv)
    return ap.Centroid if ap else rg.Point3d.Origin

def get_area(crv):
    ap = rg.AreaMassProperties.Compute(crv)
    return ap.Area if ap else 0.0

def scale_curve(crv, factor, center):
    dup = crv.DuplicateCurve()
    xf = rg.Transform.Scale(rg.Plane(center, rg.Vector3d.ZAxis), factor, factor, 1.0)
    dup.Transform(xf)
    return dup

def move_curve_z(crv, z):
    dup = crv.DuplicateCurve()
    dup.Translate(rg.Vector3d(0, 0, z))
    return dup

def rotate_curve(crv, angle_deg, center):
    dup = crv.DuplicateCurve()
    rad = math.radians(angle_deg)
    xf = rg.Transform.Rotation(math.sin(rad), math.cos(rad), rg.Vector3d.ZAxis, center)
    dup.Transform(xf)
    return dup

def offset_curve(crv, dx, dy):
    dup = crv.DuplicateCurve()
    dup.Translate(rg.Vector3d(dx, dy, 0))
    return dup

def offset_rect_inward(crv, depth):
    """Shrink curve inward by depth (metres) on each side."""
    if depth <= 0:
        return crv.DuplicateCurve()
    c = get_centroid(crv)
    bb, mn, mx = get_bb(crv)
    w = mx.X - mn.X
    d_dim = mx.Y - mn.Y
    if w > 2 * depth and d_dim > 2 * depth:
        sx = (w - 2 * depth) / w
        sy = (d_dim - 2 * depth) / d_dim
    else:
        sx = 0.1
        sy = 0.1
    dup = crv.DuplicateCurve()
    xf = rg.Transform.Scale(rg.Plane(c, rg.Vector3d.ZAxis), sx, sy, 1.0)
    dup.Transform(xf)
    return dup

def ensure_ccw(crv_in):
    """Ensure a closed curve is CCW for correct Contains() results.
    Uses centroid self-check to verify correctness (handles NurbsCurves
    from rotated polylines where ClosedCurveOrientation may be unreliable)."""
    if crv_in is None or not crv_in.IsClosed:
        return crv_in
    orient = crv_in.ClosedCurveOrientation(rg.Plane.WorldXY)
    if orient == rg.CurveOrientation.Clockwise:
        dup = crv_in.DuplicateCurve()
        dup.Reverse()
        return dup
    # Self-check: centroid must be "inside" the curve
    # If not, orientation detection was wrong — reverse
    c = get_centroid(crv_in)
    test = crv_in.Contains(c, rg.Plane.WorldXY, 0.01)
    if test == rg.PointContainment.Outside:
        dup = crv_in.DuplicateCurve()
        dup.Reverse()
        return dup
    return crv_in

# ══════════════════════════════════════════════════════════════════════════════
# CURVE CONSTRUCTORS
# ══════════════════════════════════════════════════════════════════════════════

def make_rect_curve(cx, cy, w, d, z):
    hw, hd = w / 2.0, d / 2.0
    pts = [
        rg.Point3d(cx - hw, cy - hd, z),
        rg.Point3d(cx + hw, cy - hd, z),
        rg.Point3d(cx + hw, cy + hd, z),
        rg.Point3d(cx - hw, cy + hd, z)
    ]
    segs = [rg.LineCurve(pts[i], pts[(i + 1) % 4]) for i in range(4)]
    joined = rg.Curve.JoinCurves(segs)
    return joined[0] if joined and len(joined) > 0 else rg.Polyline(pts + [pts[0]]).ToNurbsCurve()

def make_l_shape(x0, y0, W, D, void_w, void_d, corner, z):
    if corner == 0:  # remove NE
        pts = [rg.Point3d(x0,y0,z), rg.Point3d(x0+W,y0,z), rg.Point3d(x0+W,y0+D-void_d,z),
               rg.Point3d(x0+W-void_w,y0+D-void_d,z), rg.Point3d(x0+W-void_w,y0+D,z), rg.Point3d(x0,y0+D,z)]
    elif corner == 1:  # remove NW
        pts = [rg.Point3d(x0,y0,z), rg.Point3d(x0+W,y0,z), rg.Point3d(x0+W,y0+D,z),
               rg.Point3d(x0+void_w,y0+D,z), rg.Point3d(x0+void_w,y0+D-void_d,z), rg.Point3d(x0,y0+D-void_d,z)]
    elif corner == 2:  # remove SW
        pts = [rg.Point3d(x0+void_w,y0,z), rg.Point3d(x0+W,y0,z), rg.Point3d(x0+W,y0+D,z),
               rg.Point3d(x0,y0+D,z), rg.Point3d(x0,y0+void_d,z), rg.Point3d(x0+void_w,y0+void_d,z)]
    else:  # corner == 3, remove SE
        pts = [rg.Point3d(x0,y0,z), rg.Point3d(x0+W-void_w,y0,z), rg.Point3d(x0+W-void_w,y0+void_d,z),
               rg.Point3d(x0+W,y0+void_d,z), rg.Point3d(x0+W,y0+D,z), rg.Point3d(x0,y0+D,z)]
    segs = [rg.LineCurve(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    joined = rg.Curve.JoinCurves(segs)
    return joined[0] if joined and len(joined) > 0 else rg.Polyline(pts + [pts[0]]).ToNurbsCurve()

def make_u_shape(x0, y0, W, D, void_w, void_d, z):
    wing = (W - void_w) / 2.0
    pts = [rg.Point3d(x0,y0,z), rg.Point3d(x0+W,y0,z), rg.Point3d(x0+W,y0+D,z),
           rg.Point3d(x0+W-wing,y0+D,z), rg.Point3d(x0+W-wing,y0+D-void_d,z),
           rg.Point3d(x0+wing,y0+D-void_d,z), rg.Point3d(x0+wing,y0+D,z), rg.Point3d(x0,y0+D,z)]
    segs = [rg.LineCurve(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    joined = rg.Curve.JoinCurves(segs)
    return joined[0] if joined and len(joined) > 0 else rg.Polyline(pts + [pts[0]]).ToNurbsCurve()

# ══════════════════════════════════════════════════════════════════════════════
# SLAB & BREP CREATION
# ══════════════════════════════════════════════════════════════════════════════

def make_slab(crv):
    breps = rg.Brep.CreatePlanarBreps(crv, 0.001)
    if breps and len(breps) > 0:
        return breps[0]
    return None

def make_ring_slab(outer_crv, inner_crv):
    outer_slab = make_slab(outer_crv)
    inner_slab = make_slab(inner_crv)
    if outer_slab and inner_slab:
        ring = rg.Brep.CreateBooleanDifference(outer_slab, inner_slab, 0.01)
        if ring and len(ring) > 0:
            return ring[0]
    return outer_slab

def loft_no_cap(curves):
    """Loft curves into an OPEN surface (no end caps)."""
    if len(curves) < 2:
        return None
    try:
        arr = System.Array[rg.Curve](curves)
        lofted = rg.Brep.CreateFromLoft(arr, rg.Point3d.Unset, rg.Point3d.Unset,
                                         rg.LoftType.Straight, False)
    except:
        try:
            lofted = rg.Brep.CreateFromLoft(curves, rg.Point3d.Unset, rg.Point3d.Unset,
                                             rg.LoftType.Straight, False)
        except:
            return None
    if lofted and len(lofted) > 0:
        return lofted[0]
    return None

def build_ring_mass(outer_crvs, inner_crvs):
    """Build a ring-shaped solid from outer and inner curve lists.
    Avoids boolean by lofting outer + inner surfaces + ring caps, then joining."""
    if len(outer_crvs) < 2 or len(inner_crvs) < 2:
        return None
    outer_srf = loft_no_cap(outer_crvs)
    inner_srf = loft_no_cap(inner_crvs)
    if not outer_srf:
        return None
    pieces = [outer_srf]
    if inner_srf:
        pieces.append(inner_srf)
    # Create ring caps at bottom and top
    for end_crvs in [(outer_crvs[0], inner_crvs[0]), (outer_crvs[-1], inner_crvs[-1])]:
        try:
            arr2 = System.Array[rg.Curve]([end_crvs[0], end_crvs[1]])
            cap = rg.Brep.CreatePlanarBreps(arr2, 0.001)
            if cap and len(cap) > 0:
                pieces.extend(cap)
        except:
            try:
                cap = rg.Brep.CreatePlanarBreps([end_crvs[0], end_crvs[1]], 0.001)
                if cap and len(cap) > 0:
                    pieces.extend(cap)
            except:
                pass
    # Join all surfaces into one brep
    if len(pieces) >= 2:
        try:
            arr_b = System.Array[rg.Brep](pieces)
            joined = rg.Brep.JoinBreps(arr_b, 0.1)
        except:
            try:
                joined = rg.Brep.JoinBreps(pieces, 0.1)
            except:
                joined = None
        if joined and len(joined) > 0:
            result = joined[0]
            print("    ring mass: {} pieces joined, solid={}".format(len(pieces), result.IsSolid))
            return result
    # Fallback: return outer surface with caps
    m = loft_curves(outer_crvs)
    if m:
        print("    ring mass: join failed, fallback to solid outer")
    return m

def loft_curves(curves):
    if len(curves) < 2:
        return None
    lofted = None
    try:
        arr = System.Array[rg.Curve](curves)
        lofted = rg.Brep.CreateFromLoft(arr, rg.Point3d.Unset, rg.Point3d.Unset,
                                         rg.LoftType.Straight, False)
    except:
        try:
            lofted = rg.Brep.CreateFromLoft(curves, rg.Point3d.Unset, rg.Point3d.Unset,
                                             rg.LoftType.Straight, False)
        except:
            return None
    if not lofted or len(lofted) == 0:
        return None
    result = lofted[0]
    # Try built-in capping with increasing tolerance
    for tol in [0.001, 0.01, 0.1, 1.0]:
        try:
            capped = result.CapPlanarHoles(tol)
            if capped and capped.IsValid and capped.IsSolid:
                return capped
        except:
            pass
    # Manual capping: create end caps from first/last curves and join
    try:
        bot_cap = make_slab(curves[0])
        top_cap = make_slab(curves[-1])
        pieces = [result]
        if bot_cap:
            pieces.append(bot_cap)
        if top_cap:
            pieces.append(top_cap)
        if len(pieces) > 1:
            joined = rg.Brep.JoinBreps(pieces, 0.1)
            if joined and len(joined) > 0:
                j = joined[0]
                if j.IsValid:
                    if j.IsSolid:
                        return j
                    try:
                        capped2 = j.CapPlanarHoles(1.0)
                        if capped2 and capped2.IsSolid:
                            return capped2
                    except:
                        pass
                    return j
    except:
        pass
    return result

def extrude_curve_z(crv, h):
    """Extrude a curve upward by h. Multiple fallback strategies."""
    if h <= 0:
        return None
    # Strategy 1: Extrusion.Create
    try:
        ext = rg.Extrusion.Create(crv, h, True)
        if ext:
            brep = ext.ToBrep(True)
            if brep and brep.IsValid:
                return brep
            ext2 = rg.Extrusion.Create(crv, h, False)
            if ext2:
                brep2 = ext2.ToBrep(True)
                if brep2:
                    try:
                        capped = brep2.CapPlanarHoles(0.01)
                        if capped and capped.IsValid:
                            return capped
                    except:
                        pass
                    if brep2.IsValid:
                        return brep2
    except:
        pass
    # Strategy 2: Loft bottom to top
    top = move_curve_z(crv, h)
    result = loft_curves([crv, top])
    if result:
        return result
    # Strategy 3: Surface.CreateExtrusion
    try:
        srf = rg.Surface.CreateExtrusion(crv, rg.Vector3d(0, 0, h))
        if srf:
            brep3 = srf.ToBrep()
            if brep3:
                try:
                    capped = brep3.CapPlanarHoles(0.01)
                    if capped and capped.IsValid:
                        return capped
                except:
                    pass
                return brep3
    except:
        pass
    print("  WARNING: all extrusion strategies failed for curve type={}".format(type(crv).__name__))
    return None

# ══════════════════════════════════════════════════════════════════════════════
# INTERPOLATION
# ══════════════════════════════════════════════════════════════════════════════

def interpolate_curve(floor_idx, base_curve, top_crv, nf):
    """Blend base_curve -> top_crv based on floor position (0=base, nf=top).
    Returns curve at z=0."""
    t = float(floor_idx) / max(1, nf)
    if t <= 0.001:
        return base_curve.DuplicateCurve()
    if t >= 0.999:
        return top_crv.DuplicateCurve()
    base_c = get_centroid(base_curve)
    top_c = get_centroid(top_crv)
    base_bb = base_curve.GetBoundingBox(True)
    top_bb = top_crv.GetBoundingBox(True)
    base_sx = base_bb.Max.X - base_bb.Min.X
    top_sx = top_bb.Max.X - top_bb.Min.X
    base_sy = base_bb.Max.Y - base_bb.Min.Y
    top_sy = top_bb.Max.Y - top_bb.Min.Y
    sx = (base_sx + t * (top_sx - base_sx)) / base_sx if base_sx > 0 else 1.0
    sy = (base_sy + t * (top_sy - base_sy)) / base_sy if base_sy > 0 else 1.0
    crv = base_curve.DuplicateCurve()
    xf_s = rg.Transform.Scale(rg.Plane(base_c, rg.Vector3d.ZAxis), sx, sy, 1.0)
    crv.Transform(xf_s)
    dx = t * (top_c.X - base_c.X)
    dy = t * (top_c.Y - base_c.Y)
    if abs(dx) > 0.001 or abs(dy) > 0.001:
        crv.Translate(rg.Vector3d(dx, dy, 0))
    return crv

# ══════════════════════════════════════════════════════════════════════════════
# PLAN VOID GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def make_void_crv_for_floor(floor_i, envelope_curves, p_type,
                            p_courtyard_ratio, p_void_corner, p_void_ratio,
                            p_split_gap, p_bar_ratio):
    """Generate plan void curve for floor_i at z=0.
    Uses envelope_curves[floor_i] bounding box for sizing."""
    env = envelope_curves[floor_i]
    if p_type in (1, 2, 3):
        c_i = get_centroid(env)
        inner = scale_curve(env, math.sqrt(p_courtyard_ratio), c_i)
        return inner
    if p_type < 4:
        return None
    ebb, emn, emx = get_bb(env)
    ew = emx.X - emn.X
    ed = emx.Y - emn.Y
    ec = get_centroid(env)
    if p_type == 4:  # L-shape
        vw = ew * p_void_ratio
        vd = ed * p_void_ratio
        if p_void_corner == 0:
            vx, vy = emx.X - vw / 2.0, emx.Y - vd / 2.0
        elif p_void_corner == 1:
            vx, vy = emn.X + vw / 2.0, emx.Y - vd / 2.0
        elif p_void_corner == 2:
            vx, vy = emn.X + vw / 2.0, emn.Y + vd / 2.0
        else:
            vx, vy = emx.X - vw / 2.0, emn.Y + vd / 2.0
        return make_rect_curve(vx, vy, vw, vd, 0)
    elif p_type == 5:  # U-shape
        vw = ew * p_void_ratio
        vd = ed * p_void_ratio
        return make_rect_curve(ec.X, emx.Y - vd / 2.0, vw, vd, 0)
    elif p_type == 6:  # Split
        gap = min(p_split_gap, ew - ew * p_bar_ratio * 2)
        if gap < 1.0:
            gap = 1.0
        return make_rect_curve(ec.X, ec.Y, gap, ed + 2, 0)
    return None

def apply_void_2d(env_crv, void_crv):
    """Subtract void_crv from env_crv using 2D curve boolean. Returns list of curves."""
    if void_crv is None:
        return [env_crv]
    try:
        diff = rg.Curve.CreateBooleanDifference(env_crv, void_crv, 0.001)
        if diff and len(diff) > 0:
            return list(diff)
    except:
        pass
    return [env_crv]

# ══════════════════════════════════════════════════════════════════════════════
# SLAB GENERATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def generate_floor_slabs(nf, fh, void_floors, curves_out, envelope_curves,
                         p_type, s_type, p_podium_floors,
                         p_courtyard_ratio, p_void_corner, p_void_ratio,
                         p_split_gap, p_bar_ratio,
                         is_courtyard, courtyard_zone,
                         has_twist, p_top_rotation):
    """Generate all floor slabs with plan void subtraction.
    Returns list of slab Breps."""
    slabs = []

    def _floor_has_courtyard(floor_i):
        if not is_courtyard:
            return False
        if s_type != 1:
            return True
        is_tower = floor_i > p_podium_floors
        if courtyard_zone == 0:
            return True
        elif courtyard_zone == 1:
            return is_tower
        elif courtyard_zone == 2:
            return not is_tower
        return True

    def _void_for_floor(fi):
        return make_void_crv_for_floor(fi, envelope_curves, p_type,
                                       p_courtyard_ratio, p_void_corner,
                                       p_void_ratio, p_split_gap, p_bar_ratio)

    for i in range(nf + 1):
        if i in void_floors:
            continue
        env_crv_z = curves_out[i]

        if _floor_has_courtyard(i):
            c_i = get_centroid(envelope_curves[i])
            inner = scale_curve(envelope_curves[i], math.sqrt(p_courtyard_ratio), c_i)
            inner_z = move_curve_z(inner, i * fh)
            try:
                arr_c = System.Array[rg.Curve]([env_crv_z, inner_z])
                ring = rg.Brep.CreatePlanarBreps(arr_c, 0.001)
            except:
                ring = None
            if ring and len(ring) > 0:
                slabs.extend(ring)
            else:
                slab = make_slab(env_crv_z)
                if slab:
                    slabs.append(slab)

        elif p_type >= 4:
            void_crv = _void_for_floor(i)
            if void_crv is not None:
                if has_twist:
                    t = float(i) / max(1, nf)
                    angle = t * p_top_rotation
                    if abs(angle) > 0.001:
                        vc_center = get_centroid(envelope_curves[i])
                        void_crv = rotate_curve(void_crv, angle, vc_center)
                void_crv_z = move_curve_z(void_crv, i * fh)

                # For non-rectangular envelopes, trim void to envelope
                void_trimmed = void_crv_z
                if not envelope_curves[i].IsLinear():
                    try:
                        ix_result = rg.Curve.CreateBooleanIntersection(env_crv_z, void_crv_z, 0.001)
                        if ix_result and len(ix_result) > 0:
                            void_trimmed = ix_result[0]
                    except:
                        pass

                made = False
                try:
                    diff = rg.Curve.CreateBooleanDifference(env_crv_z, void_trimmed, 0.001)
                    if diff and len(diff) > 0:
                        for dc in diff:
                            slab = make_slab(dc)
                            if slab:
                                slabs.append(slab)
                                made = True
                except:
                    pass
                if not made:
                    try:
                        arr_c = System.Array[rg.Curve]([env_crv_z, void_trimmed])
                        ring = rg.Brep.CreatePlanarBreps(arr_c, 0.001)
                        if ring and len(ring) > 0:
                            slabs.extend(ring)
                            made = True
                    except:
                        pass
                if not made:
                    print("  Slab fi={}: void boolean FAILED, using full slab".format(i))
                    slab = make_slab(env_crv_z)
                    if slab:
                        slabs.append(slab)
            else:
                slab = make_slab(env_crv_z)
                if slab:
                    slabs.append(slab)

        else:
            slab = make_slab(env_crv_z)
            if slab:
                slabs.append(slab)

    return slabs


def generate_void_cap_slabs(void_floors, s_type, nf, fh, curves_out,
                            envelope_curves, p_type,
                            p_courtyard_ratio, p_void_corner, p_void_ratio,
                            p_split_gap, p_bar_ratio,
                            is_courtyard, has_twist, p_top_rotation):
    """Generate cap slabs at sky garden / stilt void boundaries.
    Returns list of slab Breps."""
    slabs = []
    if len(void_floors) == 0 or s_type not in (3, 4):
        return slabs

    sorted_vf = sorted(void_floors)
    _ranges = []
    _rs, _re = sorted_vf[0], sorted_vf[0]
    for _vf in sorted_vf[1:]:
        if _vf == _re + 1:
            _re = _vf
        else:
            _ranges.append((_rs, _re))
            _rs, _re = _vf, _vf
    _ranges.append((_rs, _re))

    def _void_for_floor(fi):
        return make_void_crv_for_floor(fi, envelope_curves, p_type,
                                       p_courtyard_ratio, p_void_corner,
                                       p_void_ratio, p_split_gap, p_bar_ratio)

    def _make_cap(fi_cap):
        if fi_cap < 0 or fi_cap >= len(curves_out):
            return
        cap_crv = curves_out[fi_cap]
        if p_type >= 4:
            void_crv = _void_for_floor(fi_cap)
            if void_crv is not None:
                if has_twist:
                    t = float(fi_cap) / max(1, nf)
                    angle = t * p_top_rotation
                    if abs(angle) > 0.001:
                        void_crv = rotate_curve(void_crv, angle, get_centroid(envelope_curves[fi_cap]))
                void_crv_z = move_curve_z(void_crv, fi_cap * fh)
                try:
                    diff = rg.Curve.CreateBooleanDifference(cap_crv, void_crv_z, 0.001)
                    if diff and len(diff) > 0:
                        for dc in diff:
                            slab = make_slab(dc)
                            if slab:
                                slabs.append(slab)
                        print("  Cap slab (voided): fi={} z={:.1f}".format(fi_cap, fi_cap * fh))
                        return
                except:
                    pass
        elif is_courtyard:
            c_i = get_centroid(envelope_curves[fi_cap])
            inner = scale_curve(envelope_curves[fi_cap], math.sqrt(p_courtyard_ratio), c_i)
            inner_z = move_curve_z(inner, fi_cap * fh)
            try:
                arr_c = System.Array[rg.Curve]([cap_crv, inner_z])
                ring = rg.Brep.CreatePlanarBreps(arr_c, 0.001)
                if ring and len(ring) > 0:
                    slabs.extend(ring)
                    print("  Cap slab (courtyard): fi={} z={:.1f}".format(fi_cap, fi_cap * fh))
                    return
            except:
                pass
        slab = make_slab(cap_crv)
        if slab:
            slabs.append(slab)
            print("  Cap slab: fi={} z={:.1f}".format(fi_cap, fi_cap * fh))

    for (_vs, _ve) in _ranges:
        # Top cap: main loop already handles _ve+1
        fi_top = _ve + 1
        if fi_top <= nf and fi_top < len(curves_out):
            pass

        # Bottom cap
        if _vs == 0 and s_type == 3:
            pass  # Stilt: no ground slab
        elif s_type == 4:
            _make_cap(_vs)

    return slabs


def generate_step_cap_slabs(s_type, p_type, nf, fh, void_floors,
                            envelope_curves, curves_out,
                            p_courtyard_ratio, p_void_corner, p_void_ratio,
                            p_split_gap, p_bar_ratio,
                            has_twist, p_top_rotation):
    """Generate transition ring caps for stepped / podium+tower.
    Returns list of slab Breps."""
    slabs = []
    if s_type not in (1, 2):
        return slabs

    def _void_for_floor(fi):
        return make_void_crv_for_floor(fi, envelope_curves, p_type,
                                       p_courtyard_ratio, p_void_corner,
                                       p_void_ratio, p_split_gap, p_bar_ratio)

    for i in range(1, nf + 1):
        if i in void_floors:
            continue
        prev_idx = max(0, i - 1)
        cur_bb = envelope_curves[i].GetBoundingBox(True)
        prev_bb = envelope_curves[prev_idx].GetBoundingBox(True)
        cur_w = cur_bb.Max.X - cur_bb.Min.X
        cur_d = cur_bb.Max.Y - cur_bb.Min.Y
        prev_w = prev_bb.Max.X - prev_bb.Min.X
        prev_d = prev_bb.Max.Y - prev_bb.Min.Y
        if (prev_w > cur_w * 1.05) or (prev_d > cur_d * 1.05):
            # Actual transition Z depends on s_type:
            #  - s_type=1 (P+T): tower range starts at prev_idx*fh (top of
            #    podium = base of tower), even though the smaller envelope
            #    curve first appears at index i. Cap must sit at the tower
            #    base plate level, not one floor above.
            #  - s_type=2 (setback): range change happens at i*fh, which is
            #    where the newly-smaller envelope curve is first applied.
            step_z = (prev_idx * fh) if s_type == 1 else (i * fh)

            # For podium+tower with L/U/Split: skip ring cap entirely
            if p_type >= 4 and s_type == 1:
                print("  Step cap SKIPPED (podium+tower L/U/Split): fi={} z={:.1f}".format(i, step_z))
                continue

            larger_crv = move_curve_z(envelope_curves[prev_idx], step_z)
            smaller_crv = move_curve_z(envelope_curves[i], step_z)
            _step_made = False

            # Solid / courtyard / void / split plan: build the ring as a single
            # planar brep with the tower/smaller outline as a HOLE. Without
            # this, the cap fills the full outer boundary and the tower plate
            # is missed.
            if p_type < 4:
                try:
                    arr_ring = System.Array[rg.Curve]([larger_crv, smaller_crv])
                    ring_breps = rg.Brep.CreatePlanarBreps(arr_ring, 0.001)
                    if ring_breps and len(ring_breps) > 0:
                        slabs.extend(ring_breps)
                        _step_made = True
                        print("  Step cap ring (hole=tower plate): fi={} z={:.1f}".format(i, step_z))
                        continue
                except:
                    pass

            try:
                ring_diff = rg.Curve.CreateBooleanDifference(larger_crv, smaller_crv, 0.001)
                if ring_diff and len(ring_diff) > 0:
                    for rc in ring_diff:
                        if not rc.IsClosed:
                            continue
                        # Subtract plan void from ring if L/U/Split
                        if p_type >= 4:
                            _ring_void = _void_for_floor(prev_idx)
                            if _ring_void is not None:
                                if has_twist:
                                    t = float(i) / max(1, nf)
                                    angle = t * p_top_rotation
                                    if abs(angle) > 0.001:
                                        _ring_void = rotate_curve(_ring_void, angle, get_centroid(envelope_curves[prev_idx]))
                                _ring_void_z = move_curve_z(_ring_void, step_z)
                                # For ellipse: trim void to ring bounds
                                try:
                                    ix = rg.Curve.CreateBooleanIntersection(rc, _ring_void_z, 0.001)
                                    if ix and len(ix) > 0:
                                        _ring_void_z = ix[0]
                                except:
                                    pass
                                try:
                                    vdiff = rg.Curve.CreateBooleanDifference(rc, _ring_void_z, 0.001)
                                    if vdiff and len(vdiff) > 0:
                                        for vdc in vdiff:
                                            if vdc.IsClosed:
                                                slab = make_slab(vdc)
                                                if slab:
                                                    slabs.append(slab)
                                                    _step_made = True
                                        if _step_made:
                                            continue
                                except:
                                    pass
                                # Void subtraction failed — use CreatePlanarBreps fallback
                                try:
                                    arr_c = System.Array[rg.Curve]([rc, _ring_void_z])
                                    ring_breps = rg.Brep.CreatePlanarBreps(arr_c, 0.001)
                                    if ring_breps and len(ring_breps) > 0:
                                        slabs.extend(ring_breps)
                                        _step_made = True
                                        continue
                                except:
                                    pass
                        # No plan void or solid plan type — use ring as-is
                        slab = make_slab(rc)
                        if slab:
                            slabs.append(slab)
                            _step_made = True
            except:
                pass
            if _step_made:
                print("  Step cap ring: fi={} z={:.1f}".format(i, step_z))
            else:
                print("  Step cap SKIPPED: fi={} z={:.1f}".format(i, step_z))

    return slabs

# ══════════════════════════════════════════════════════════════════════════════
# COLUMN GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def make_col_profile(cx, cy, z, shape, size):
    """Create column cross-section curve at (cx, cy, z).
    shape: 0=Square, 1=Round. size=diameter/width."""
    hs = size / 2.0
    if shape == 1:
        circle = rg.Circle(rg.Plane(rg.Point3d(cx, cy, z), rg.Vector3d.ZAxis), hs)
        return circle.ToNurbsCurve()
    else:
        return make_rect_curve(cx, cy, size, size, z)

def add_columns(z_base, col_h, col_span, envelope_curves, nf, fh,
                p_stilt_col_size, p_stilt_col_shape, b_shape,
                p_type, p_courtyard_ratio, p_void_corner, p_void_ratio,
                p_split_gap, p_bar_ratio,
                has_twist, p_top_rotation,
                core_cx, core_cy, core_hs,
                env_no_twist=None, ori=0.0):
    """Add column grid from z_base upward for col_h height.
    Returns list of column Brep objects."""
    col_breps = []
    if col_h <= 0:
        return col_breps
    col_size = p_stilt_col_size
    col_shape = p_stilt_col_shape
    inset = col_size + 0.5
    span = max(3.0, col_span)

    col_floor = max(0, min(nf, int(round(z_base / fh))))
    col_env = envelope_curves[col_floor] if col_floor < len(envelope_curves) else envelope_curves[0]
    col_env = ensure_ccw(col_env)

    # Inset containment curve
    col_contain = None
    c_env = get_centroid(col_env)
    try:
        offsets = col_env.Offset(rg.Plane.WorldXY, -inset, 0.01, rg.CurveOffsetCornerStyle.Sharp)
        if offsets and len(offsets) > 0:
            best = None
            best_dist = float("inf")
            for oc in offsets:
                if oc.IsClosed:
                    oc_c = get_centroid(oc)
                    d = c_env.DistanceTo(oc_c)
                    oc_area = get_area(oc)
                    env_area = get_area(col_env)
                    if oc_area < env_area and d < best_dist:
                        best = oc
                        best_dist = d
            col_contain = best
            if col_contain:
                print("  add_columns: Offset OK, area={:.1f}".format(get_area(col_contain)))
            else:
                print("  add_columns: Offset returned {} curves but none valid".format(len(offsets)))
        else:
            print("  add_columns: Offset returned None/empty")
    except Exception as _oe:
        print("  add_columns: Offset FAILED: {}".format(_oe))
    if col_contain is None:
        col_contain = offset_rect_inward(col_env, inset)
        print("  add_columns: using fallback offset, closed={}".format(col_contain.IsClosed if col_contain else False))
    col_contain = ensure_ccw(col_contain)

    # Per-floor void — use UNROTATED envelopes for correct void positioning,
    # then rotate the void by orientation to match the rotated building.
    _void_env = env_no_twist if env_no_twist is not None else envelope_curves
    col_void_crv = make_void_crv_for_floor(col_floor, _void_env, 0 if p_type < 4 else p_type,
                                            p_courtyard_ratio, p_void_corner, p_void_ratio,
                                            p_split_gap, p_bar_ratio)
    if col_void_crv is not None:
        # Rotate void by orientation to align with rotated building
        if abs(ori) > 0.001:
            _void_center = get_centroid(_void_env[col_floor])
            col_void_crv = rotate_curve(col_void_crv, ori, _void_center)
        col_void_crv = ensure_ccw(col_void_crv)
        if has_twist:
            t = float(col_floor) / max(1, nf)
            angle = t * p_top_rotation
            if abs(angle) > 0.001:
                vc = get_centroid(col_env)
                col_void_crv = rotate_curve(col_void_crv, angle, vc)

    cc_bb = col_contain.GetBoundingBox(True)
    cc_W = cc_bb.Max.X - cc_bb.Min.X
    cc_D = cc_bb.Max.Y - cc_bb.Min.Y
    cc_c = get_centroid(col_contain)

    _use_radial_col = b_shape in (1, 2, 3, 4, 5, 6)
    # Debug: verify containment curve
    _cc_centroid = get_centroid(col_contain)
    _cc_test = col_contain.Contains(_cc_centroid, rg.Plane.WorldXY, 0.01)
    print("  add_columns: contain BB={:.1f}x{:.1f} centroid_inside={} z={:.2f} closed={}".format(
        cc_W, cc_D, _cc_test, col_contain.PointAtStart.Z, col_contain.IsClosed))

    col_positions = []

    # Get Z of containment curve for consistent point checking
    _contain_z = col_contain.PointAtStart.Z if col_contain else 0
    _void_z = col_void_crv.PointAtStart.Z if col_void_crv else 0

    def _pt_ok(cx_c, cy_c):
        # Use same Z as the containment curve for accurate Contains()
        pt = rg.Point3d(cx_c, cy_c, _contain_z)
        if col_contain.IsClosed:
            if col_contain.Contains(pt, rg.Plane.WorldXY, 0.01) == rg.PointContainment.Outside:
                return False
        if col_void_crv is not None and col_void_crv.IsClosed:
            vpt = rg.Point3d(cx_c, cy_c, _void_z)
            if col_void_crv.Contains(vpt, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                return False
        if core_hs > 0:
            if abs(cx_c - core_cx) < core_hs and abs(cy_c - core_cy) < core_hs:
                return False
        return True

    if _use_radial_col:
        r_max = max(cc_W, cc_D) / 2.0
        n_rings = max(3, int(math.ceil(r_max / span)) + 1)
        a_ell = cc_W / 2.0
        b_ell = cc_D / 2.0
        perim = math.pi * (3*(a_ell+b_ell) -
                math.sqrt((3*a_ell+b_ell)*(a_ell+3*b_ell)))
        n_radials = max(8, int(math.ceil(perim / span)))
        if n_radials > 48:
            n_radials = 48

        for ri in range(n_rings + 1):
            if n_rings > 0:
                scale_f = 1.0 - (float(ri) / n_rings)
            else:
                scale_f = 1.0
            if scale_f < 0.05:
                continue
            ring_r_x = a_ell * scale_f
            ring_r_y = b_ell * scale_f
            for rj in range(n_radials):
                angle = rj * 2.0 * math.pi / n_radials
                cx_c = cc_c.X + ring_r_x * math.cos(angle)
                cy_c = cc_c.Y + ring_r_y * math.sin(angle)
                if _pt_ok(cx_c, cy_c):
                    col_positions.append((cx_c, cy_c))

        if _pt_ok(cc_c.X, cc_c.Y):
            col_positions.append((cc_c.X, cc_c.Y))
    else:
        nx_col = max(1, int(round(cc_W / span)))
        ny_col = max(1, int(round(cc_D / span)))
        sx_col = cc_W / nx_col
        sy_col = cc_D / ny_col
        for ix in range(nx_col + 1):
            for iy in range(ny_col + 1):
                cx_c = cc_bb.Min.X + ix * sx_col
                cy_c = cc_bb.Min.Y + iy * sy_col
                if _pt_ok(cx_c, cy_c):
                    col_positions.append((cx_c, cy_c))

    # Deduplicate and create geometry
    col_hash = set()
    _n_cols = 0
    for (cx_c, cy_c) in col_positions:
        ck = (round(cx_c, 1), round(cy_c, 1))
        if ck in col_hash:
            continue
        col_hash.add(ck)
        col_crv = make_col_profile(cx_c, cy_c, z_base, col_shape, col_size)
        col_mass = extrude_curve_z(col_crv, col_h)
        if col_mass:
            col_breps.append(col_mass)
            _n_cols += 1
    print("  add_columns: z={:.1f} h={:.1f} radial={} positions={} cols={}".format(
        z_base, col_h, _use_radial_col, len(col_positions), _n_cols))
    return col_breps
