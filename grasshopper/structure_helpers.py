# structure_helpers.py — Helper functions for gh-structure.py
# Split out to keep the main GHPython component lean.
# Import via: sys.path + import structure_helpers as sh

import Rhino.Geometry as rg
import math


# ══════════════════════════════════════════════════════════════════════════════
# GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_centroid(c):
    ap = rg.AreaMassProperties.Compute(c)
    return ap.Centroid if ap else rg.Point3d.Origin

def get_area(c):
    ap = rg.AreaMassProperties.Compute(c)
    return ap.Area if ap else 0.0

def ensure_ccw(crv_in):
    if crv_in is None or not crv_in.IsClosed:
        return crv_in
    orient = crv_in.ClosedCurveOrientation(rg.Plane.WorldXY)
    if orient == rg.CurveOrientation.Clockwise:
        dup = crv_in.DuplicateCurve()
        dup.Reverse()
        return dup
    return crv_in

def scale_curve(c, factor, center):
    dup = c.DuplicateCurve()
    xf = rg.Transform.Scale(rg.Plane(center, rg.Vector3d.ZAxis), factor, factor, 1.0)
    dup.Transform(xf)
    return dup

def rotate_curve(c, angle_deg, center):
    dup = c.DuplicateCurve()
    rad = math.radians(angle_deg)
    xf = rg.Transform.Rotation(math.sin(rad), math.cos(rad), rg.Vector3d.ZAxis, center)
    dup.Transform(xf)
    return dup

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

def flatten_crv(c):
    dup = c.DuplicateCurve()
    bb_c = dup.GetBoundingBox(True)
    if abs(bb_c.Min.Z) > 0.001 or abs(bb_c.Max.Z) > 0.001:
        xf = rg.Transform.Translation(0, 0, -bb_c.Min.Z)
        dup.Transform(xf)
    return ensure_ccw(dup)

def offset_rect_inward(crv_in, depth):
    if depth <= 0:
        return crv_in.DuplicateCurve()
    c = get_centroid(crv_in)
    bb_in = crv_in.GetBoundingBox(True)
    w = bb_in.Max.X - bb_in.Min.X
    d_dim = bb_in.Max.Y - bb_in.Min.Y
    if w > 2 * depth and d_dim > 2 * depth:
        sx = (w - 2 * depth) / w
        sy = (d_dim - 2 * depth) / d_dim
    else:
        sx, sy = 0.1, 0.1
    dup = crv_in.DuplicateCurve()
    xf = rg.Transform.Scale(rg.Plane(c, rg.Vector3d.ZAxis), sx, sy, 1.0)
    dup.Transform(xf)
    return dup


# ══════════════════════════════════════════════════════════════════════════════
# FLOOR CURVE GENERATION (Option B — from base_curve + params)
# ══════════════════════════════════════════════════════════════════════════════

def build_shaped_curve(crv, b_shape, b_scale, ori):
    """Apply base_shape + scale + orientation to the base curve."""
    shaped = crv.DuplicateCurve()
    bb = shaped.GetBoundingBox(True)
    c = get_centroid(shaped)
    hw = (bb.Max.X - bb.Min.X) / 2.0 * b_scale
    hd = (bb.Max.Y - bb.Min.Y) / 2.0 * b_scale
    cx, cy = c.X, c.Y

    if b_shape == 1:  # Ellipse
        el = rg.Ellipse(rg.Plane(rg.Point3d(cx, cy, 0), rg.Vector3d.ZAxis), hw, hd)
        shaped = el.ToNurbsCurve()
    elif b_shape == 2:  # Circle
        r = min(hw, hd)
        circ = rg.Circle(rg.Plane(rg.Point3d(cx, cy, 0), rg.Vector3d.ZAxis), r)
        shaped = circ.ToNurbsCurve()
    elif b_shape == 3:  # Chamfered
        ch = min(hw, hd) * 0.3
        pts = [
            rg.Point3d(cx - hw + ch, cy - hd, 0), rg.Point3d(cx + hw - ch, cy - hd, 0),
            rg.Point3d(cx + hw, cy - hd + ch, 0), rg.Point3d(cx + hw, cy + hd - ch, 0),
            rg.Point3d(cx + hw - ch, cy + hd, 0), rg.Point3d(cx - hw + ch, cy + hd, 0),
            rg.Point3d(cx - hw, cy + hd - ch, 0), rg.Point3d(cx - hw, cy - hd + ch, 0),
        ]
        pts.append(pts[0])
        shaped = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])
    elif b_shape == 4:  # Diamond
        pts = [
            rg.Point3d(cx, cy - hd, 0), rg.Point3d(cx + hw, cy, 0),
            rg.Point3d(cx, cy + hd, 0), rg.Point3d(cx - hw, cy, 0),
        ]
        pts.append(pts[0])
        shaped = rg.PolylineCurve([rg.Point3d(p.X, p.Y, p.Z) for p in pts])
    elif b_scale < 0.999 and b_shape == 0:
        shaped = scale_curve(shaped, b_scale, c)

    sc = get_centroid(shaped)
    if abs(ori) > 0.001:
        shaped = rotate_curve(shaped, ori, sc)
    return shaped


def build_floor_curves(shaped_crv, nf, s_type, p_top_scale, p_top_rotation,
                       p_podium_floors, p_tower_ratio):
    """Build per-floor curves (flat, at z=0) with section-type awareness.
    Returns (floor_crvs_flat, floor_crvs_notwist)."""
    sc_center = get_centroid(shaped_crv)
    top_crv = shaped_crv.DuplicateCurve()
    if p_top_scale != 1.0:
        top_crv = scale_curve(top_crv, p_top_scale, sc_center)

    def _interp(fi):
        t = float(fi) / max(1, nf)
        if t <= 0.001:
            return shaped_crv.DuplicateCurve()
        if t >= 0.999:
            return top_crv.DuplicateCurve()
        bc = get_centroid(shaped_crv)
        tc = get_centroid(top_crv)
        bbb = shaped_crv.GetBoundingBox(True)
        tbb = top_crv.GetBoundingBox(True)
        bsx = bbb.Max.X - bbb.Min.X
        tsx = tbb.Max.X - tbb.Min.X
        bsy = bbb.Max.Y - bbb.Min.Y
        tsy = tbb.Max.Y - tbb.Min.Y
        sx = (bsx + t * (tsx - bsx)) / bsx if bsx > 0 else 1.0
        sy = (bsy + t * (tsy - bsy)) / bsy if bsy > 0 else 1.0
        c2 = shaped_crv.DuplicateCurve()
        xf_s = rg.Transform.Scale(rg.Plane(bc, rg.Vector3d.ZAxis), sx, sy, 1.0)
        c2.Transform(xf_s)
        dx = t * (tc.X - bc.X)
        dy = t * (tc.Y - bc.Y)
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            c2.Translate(rg.Vector3d(dx, dy, 0))
        return c2

    crvs = []
    if s_type == 0:
        for i in range(nf + 1):
            crvs.append(_interp(i))
    elif s_type == 1:
        pf = max(1, min(p_podium_floors, nf - 1))
        for i in range(nf + 1):
            if i <= pf:
                crvs.append(_interp(i))
            else:
                interp = _interp(i)
                crvs.append(scale_curve(interp, p_tower_ratio, get_centroid(interp)))
    elif s_type == 2:
        interval = max(2, 5)
        depth = max(0.5, 2.0)
        for i in range(nf + 1):
            step_idx = i // interval if i > 0 else 0
            od = step_idx * depth
            sc = _interp(step_idx * interval)
            if od > 0:
                sc = offset_rect_inward(sc, od)
            crvs.append(sc)
    else:
        for i in range(nf + 1):
            crvs.append(_interp(i))

    # Save pre-twist copies
    notwist = [c.DuplicateCurve() for c in crvs]

    # Apply twist
    has_twist = abs(p_top_rotation) > 0.001
    if has_twist:
        for i in range(len(crvs)):
            t = float(i) / max(1, nf)
            angle = t * p_top_rotation
            if abs(angle) > 0.001:
                ci = get_centroid(crvs[i])
                crvs[i] = rotate_curve(crvs[i], angle, ci)

    # Pad
    while len(crvs) <= nf:
        crvs.append(crvs[-1].DuplicateCurve())
    while len(notwist) <= nf:
        notwist.append(notwist[-1].DuplicateCurve())

    return crvs, notwist


# ══════════════════════════════════════════════════════════════════════════════
# VOID COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def make_void_for_floor(fi, floor_crvs_notwist, p_type, is_courtyard,
                        p_courtyard_ratio, p_void_corner, p_void_ratio,
                        p_split_gap, p_bar_ratio):
    """Generate plan void curve for floor fi using UNTWISTED envelope."""
    env = floor_crvs_notwist[fi] if fi < len(floor_crvs_notwist) else floor_crvs_notwist[-1]
    ebb = env.GetBoundingBox(True)
    ew = ebb.Max.X - ebb.Min.X
    ed = ebb.Max.Y - ebb.Min.Y
    ec = get_centroid(env)

    if is_courtyard:
        inner_scale = math.sqrt(p_courtyard_ratio)
        vc = env.DuplicateCurve()
        xf_s = rg.Transform.Scale(rg.Plane(ec, rg.Vector3d.ZAxis),
                                   inner_scale, inner_scale, 1.0)
        vc.Transform(xf_s)
        return vc
    elif p_type == 4:  # L
        vw = ew * p_void_ratio
        vd = ed * p_void_ratio
        if p_void_corner == 0:   vx, vy = ebb.Max.X - vw/2, ebb.Max.Y - vd/2
        elif p_void_corner == 1: vx, vy = ebb.Min.X + vw/2, ebb.Max.Y - vd/2
        elif p_void_corner == 2: vx, vy = ebb.Min.X + vw/2, ebb.Min.Y + vd/2
        else:                    vx, vy = ebb.Max.X - vw/2, ebb.Min.Y + vd/2
        return make_rect_curve(vx, vy, vw, vd, 0)
    elif p_type == 5:  # U
        vw = ew * p_void_ratio
        vd = ed * p_void_ratio
        return make_rect_curve(ec.X, ebb.Max.Y - vd/2, vw, vd, 0)
    elif p_type == 6:  # Split
        gap = min(p_split_gap, ew - ew * p_bar_ratio * 2)
        if gap < 1.0:
            gap = 1.0
        return make_rect_curve(ec.X, ec.Y, gap, ed + 2, 0)
    return None


# ══════════════════════════════════════════════════════════════════════════════
# BEAM LINE TRIMMING
# ══════════════════════════════════════════════════════════════════════════════

def trim_line_by_curve(line_crv, boundary_crv, keep_inside=True):
    """Trim a line by a closed boundary curve.
    When keep_inside=False, uses strict Inside check to preserve boundary-touching beams."""
    if not boundary_crv.IsClosed:
        return [line_crv]
    ix = rg.Intersect.Intersection.CurveCurve(line_crv, boundary_crv, 0.01, 0.01)
    if ix is None or ix.Count == 0:
        mid = line_crv.PointAtNormalizedLength(0.5)
        mid_2d = rg.Point3d(mid.X, mid.Y, 0)
        cont = boundary_crv.Contains(mid_2d, rg.Plane.WorldXY, 0.01)
        if keep_inside:
            is_inside = (cont != rg.PointContainment.Outside)
        else:
            is_inside = (cont == rg.PointContainment.Inside)
        if is_inside == keep_inside:
            return [line_crv]
        return []
    dom = line_crv.Domain
    params = sorted(set([dom.Min, dom.Max] + [ix[i].ParameterA for i in range(ix.Count)]))
    result = []
    for i in range(len(params) - 1):
        seg = line_crv.Trim(params[i], params[i + 1])
        if seg is None or seg.GetLength() < 0.1:
            continue
        mid = seg.PointAtNormalizedLength(0.5)
        mid_2d = rg.Point3d(mid.X, mid.Y, 0)
        cont = boundary_crv.Contains(mid_2d, rg.Plane.WorldXY, 0.01)
        if keep_inside:
            is_inside = (cont != rg.PointContainment.Outside)
        else:
            is_inside = (cont == rg.PointContainment.Inside)
        if is_inside == keep_inside:
            result.append(seg)
    return result


def trim_line_to_curve(line_crv, boundary_crv):
    return trim_line_by_curve(line_crv, boundary_crv, keep_inside=True)


# ══════════════════════════════════════════════════════════════════════════════
# BEAM GENERATION (per floor)
# ══════════════════════════════════════════════════════════════════════════════

def generate_beams_for_floor(fi_crv, z, floor_void_crv, use_radial, span, is_courtyard=False):
    """Generate beam lines for one floor.
    Returns (ring_beams, radial_beams)."""
    ring_beams = []
    radial_beams = []
    fi_bb = fi_crv.GetBoundingBox(True)
    fi_W = fi_bb.Max.X - fi_bb.Min.X
    fi_D = fi_bb.Max.Y - fi_bb.Min.Y
    fi_c = get_centroid(fi_crv)

    if fi_W < 0.5 or fi_D < 0.5:
        return (ring_beams, radial_beams)

    flat_crv = flatten_crv(fi_crv)
    fv = ensure_ccw(floor_void_crv) if floor_void_crv is not None else None

    # Outer boundary beam(s): for L/U/Split, use the actual building outline
    # (floor curve - void = L/U/Split shape) instead of the full rectangle.
    # This removes beams from the void area while maintaining Karamba connectivity.
    # For courtyard and solid plans, use the full envelope curve.
    _outline_added = False
    if fv is not None and not is_courtyard:
        # L/U/Split: compute actual slab outline = floor - void
        try:
            flat_outer = flatten_crv(fi_crv)
            flat_void = flatten_crv(fv)
            diff = rg.Curve.CreateBooleanDifference(flat_outer, flat_void, 0.001)
            if diff and len(diff) > 0:
                for dc in diff:
                    dc_z = dc.DuplicateCurve()
                    dc_z.Translate(rg.Vector3d(0, 0, z))
                    ring_beams.append(dc_z)
                _outline_added = True
        except:
            pass
        if not _outline_added:
            # Boolean failed — fall back to full outer + void boundary will be added later
            outer_at_z = fi_crv.DuplicateCurve()
            outer_bb = outer_at_z.GetBoundingBox(True)
            outer_at_z.Translate(rg.Vector3d(0, 0, z - outer_bb.Min.Z))
            ring_beams.append(outer_at_z)
    else:
        outer_at_z = fi_crv.DuplicateCurve()
        outer_bb = outer_at_z.GetBoundingBox(True)
        outer_at_z.Translate(rg.Vector3d(0, 0, z - outer_bb.Min.Z))
        ring_beams.append(outer_at_z)

    def _pt_in_fv(pt):
        """Strictly inside void (not on boundary). Keeps beams touching void edge."""
        if fv is None:
            return False
        return fv.Contains(rg.Point3d(pt.X, pt.Y, 0),
                           rg.Plane.WorldXY, 0.01) == rg.PointContainment.Inside

    def _beam_crosses_fv(p0, p1):
        if fv is None:
            return False
        mid = rg.Point3d((p0.X+p1.X)/2, (p0.Y+p1.Y)/2, 0)
        if _pt_in_fv(mid):
            return True
        q1 = rg.Point3d(p0.X*0.75+p1.X*0.25, p0.Y*0.75+p1.Y*0.25, 0)
        q3 = rg.Point3d(p0.X*0.25+p1.X*0.75, p0.Y*0.25+p1.Y*0.75, 0)
        if _pt_in_fv(q1) or _pt_in_fv(q3):
            return True
        beam_2d = rg.LineCurve(rg.Point3d(p0.X, p0.Y, 0), rg.Point3d(p1.X, p1.Y, 0))
        ix = rg.Intersect.Intersection.CurveCurve(beam_2d, fv, 0.1, 0.1)
        if ix is not None and ix.Count > 0:
            return True
        return False

    if use_radial:
        # Ring beams (primary) — skip ri=0 as outer boundary is already added above
        r_max = max(fi_W, fi_D) / 2.0
        n_rings = max(3, int(math.ceil(r_max / span)) + 1)
        for ri in range(1, n_rings):
            sf = 1.0 - (float(ri) / n_rings)
            if sf < 0.05:
                continue
            ring_crv = scale_curve(fi_crv, sf, fi_c)
            ring_at_z = ring_crv.DuplicateCurve()
            ring_bb = ring_at_z.GetBoundingBox(True)
            ring_at_z.Translate(rg.Vector3d(0, 0, z - ring_bb.Min.Z))

            if fv is not None:
                flat_ring = flatten_crv(ring_crv)
                ix = rg.Intersect.Intersection.CurveCurve(flat_ring, fv, 0.01, 0.01)
                if ix is not None and ix.Count >= 2:
                    split_params = sorted([ix[i].ParameterA for i in range(ix.Count)])
                    splits = flat_ring.Split(split_params)
                    if splits:
                        for seg in splits:
                            mid = seg.PointAtNormalizedLength(0.5)
                            if not _pt_in_fv(rg.Point3d(mid.X, mid.Y, 0)):
                                seg_z = seg.DuplicateCurve()
                                seg_z.Translate(rg.Vector3d(0, 0, z))
                                ring_beams.append(seg_z)
                        continue
                else:
                    # 0 or 1 intersections: ring is fully inside or outside void
                    ring_mid = ring_crv.PointAtNormalizedLength(0.5)
                    if _pt_in_fv(rg.Point3d(ring_mid.X, ring_mid.Y, 0)):
                        continue
            ring_beams.append(ring_at_z)

        # Add void boundary as ring beam (only if outline wasn't already added)
        if fv is not None and fv.IsClosed:
            if is_courtyard:
                # Courtyard: full void boundary (inner edge beam)
                fv_at_z = fv.DuplicateCurve()
                fv_bb = fv_at_z.GetBoundingBox(True)
                fv_at_z.Translate(rg.Vector3d(0, 0, z - fv_bb.Min.Z))
                ring_beams.append(fv_at_z)
            elif not _outline_added:
                # L/U/Split fallback: void edge beams only where inside floor curve
                flat_fv = flatten_crv(fv)
                ix_ve = rg.Intersect.Intersection.CurveCurve(flat_fv, flat_crv, 0.01, 0.01)
                if ix_ve is not None and ix_ve.Count >= 2:
                    vp = sorted([ix_ve[i].ParameterA for i in range(ix_ve.Count)])
                    v_splits = flat_fv.Split(vp)
                    if v_splits:
                        for vs in v_splits:
                            vmid = vs.PointAtNormalizedLength(0.5)
                            vmid_2d = rg.Point3d(vmid.X, vmid.Y, 0)
                            if flat_crv.Contains(vmid_2d, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                                vs_z = vs.DuplicateCurve()
                                vs_z.Translate(rg.Vector3d(0, 0, z))
                                ring_beams.append(vs_z)

        # Radial beams (secondary)
        a_ell, b_ell = fi_W / 2.0, fi_D / 2.0
        perim = math.pi * (3*(a_ell+b_ell) - math.sqrt((3*a_ell+b_ell)*(a_ell+3*b_ell)))
        n_radials = max(8, min(48, int(math.ceil(perim / span))))
        diag = math.sqrt(fi_W**2 + fi_D**2) / 2.0 + 1.0

        for rj in range(n_radials):
            angle = rj * 2.0 * math.pi / n_radials
            far_x = fi_c.X + diag * math.cos(angle)
            far_y = fi_c.Y + diag * math.sin(angle)
            raw_line = rg.LineCurve(
                rg.Point3d(fi_c.X, fi_c.Y, 0),
                rg.Point3d(far_x, far_y, 0))
            trimmed = trim_line_to_curve(raw_line, flat_crv)
            for seg in trimmed:
                if fv is not None:
                    void_trimmed = trim_line_by_curve(seg, fv, keep_inside=False)
                    for vs in void_trimmed:
                        if vs.GetLength() > 0.1:
                            vs_z = vs.DuplicateCurve()
                            vs_z.Translate(rg.Vector3d(0, 0, z))
                            radial_beams.append(vs_z)
                else:
                    seg_z = seg.DuplicateCurve()
                    seg_z.Translate(rg.Vector3d(0, 0, z))
                    radial_beams.append(seg_z)
    else:
        # Orthogonal grid (all → secondary)
        nx = max(2, int(math.ceil(fi_W / span)))
        ny = max(2, int(math.ceil(fi_D / span)))
        sx = fi_W / nx
        sy = fi_D / ny

        def _add_ortho(seg):
            if fv is not None:
                vt = trim_line_by_curve(seg, fv, keep_inside=False)
                for vs in vt:
                    if vs.GetLength() > 0.1:
                        vs_z = vs.DuplicateCurve()
                        vs_z.Translate(rg.Vector3d(0, 0, z))
                        radial_beams.append(vs_z)
            else:
                seg_z = seg.DuplicateCurve()
                seg_z.Translate(rg.Vector3d(0, 0, z))
                radial_beams.append(seg_z)

        for iy in range(1, ny):
            y = fi_bb.Min.Y + iy * sy
            raw = rg.LineCurve(rg.Point3d(fi_bb.Min.X - 0.1, y, 0),
                               rg.Point3d(fi_bb.Max.X + 0.1, y, 0))
            for seg in trim_line_to_curve(raw, flat_crv):
                _add_ortho(seg)
        for ix_i in range(1, nx):
            x = fi_bb.Min.X + ix_i * sx
            raw = rg.LineCurve(rg.Point3d(x, fi_bb.Min.Y - 0.1, 0),
                               rg.Point3d(x, fi_bb.Max.Y + 0.1, 0))
            for seg in trim_line_to_curve(raw, flat_crv):
                _add_ortho(seg)

        # Add void boundary as ring beam
        # For L/U/Split: the outer ring already includes the voided outline
        # (boolean diff was done above), so only add void boundary for courtyard.
        if fv is not None and fv.IsClosed:
            if is_courtyard:
                fv_at_z = fv.DuplicateCurve()
                fv_bb = fv_at_z.GetBoundingBox(True)
                fv_at_z.Translate(rg.Vector3d(0, 0, z - fv_bb.Min.Z))
                ring_beams.append(fv_at_z)
            elif not _outline_added:
                # L/U/Split fallback: void edge beams only where inside floor curve
                # (only needed if boolean diff failed above)
                flat_fv = flatten_crv(fv)
                ix_ve = rg.Intersect.Intersection.CurveCurve(flat_fv, flat_crv, 0.01, 0.01)
                if ix_ve is not None and ix_ve.Count >= 2:
                    vp = sorted([ix_ve[i].ParameterA for i in range(ix_ve.Count)])
                    v_splits = flat_fv.Split(vp)
                    if v_splits:
                        for vs in v_splits:
                            vmid = vs.PointAtNormalizedLength(0.5)
                            vmid_2d = rg.Point3d(vmid.X, vmid.Y, 0)
                            if flat_crv.Contains(vmid_2d, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                                vs_z = vs.DuplicateCurve()
                                vs_z.Translate(rg.Vector3d(0, 0, z))
                                ring_beams.append(vs_z)

    return (ring_beams, radial_beams)


# ══════════════════════════════════════════════════════════════════════════════
# SLAB BOUNDARY EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def build_slab_boundaries(fs_list):
    """Build per-Z boundary curves from floor slab Breps.
    Returns dict: z → list of closed CCW curves."""
    edges_by_z = {}
    for slab in fs_list:
        bb = slab.GetBoundingBox(True)
        sz = round(bb.Min.Z, 1)
        if sz not in edges_by_z:
            edges_by_z[sz] = []
        edges = slab.Edges
        if edges:
            for ei in range(edges.Count):
                ec = edges[ei].DuplicateCurve()
                if ec and ec.GetLength() > 0.1:
                    edges_by_z[sz].append(ec)

    result = {}
    for sz, edge_list in edges_by_z.items():
        flat_edges = []
        for ec in edge_list:
            fec = ec.DuplicateCurve()
            ec_bb = fec.GetBoundingBox(True)
            if abs(ec_bb.Min.Z) > 0.001:
                fec.Translate(rg.Vector3d(0, 0, -ec_bb.Min.Z))
            flat_edges.append(fec)
        joined = rg.Curve.JoinCurves(flat_edges, 0.5)
        if joined:
            closed = [ensure_ccw(jc) for jc in joined if jc.IsClosed]
            if closed:
                result[sz] = closed
    return result


# ══════════════════════════════════════════════════════════════════════════════
# SECONDARY BEAM RE-TRIMMING
# ══════════════════════════════════════════════════════════════════════════════

def retrim_secondary_beams(all_radial_lns, slab_crvs_by_z):
    """Re-trim secondary beams to actual slab boundaries (multi-bar support)."""
    trimmed = []
    for sb in all_radial_lns:
        sz = round(sb.PointAtStart.Z, 1)
        boundaries = slab_crvs_by_z.get(sz)
        if boundaries is None or len(boundaries) == 0:
            trimmed.append(sb)
            continue
        s = sb.PointAtStart
        e = sb.PointAtEnd
        if sb.IsLinear():
            flat_sb = rg.LineCurve(rg.Point3d(s.X, s.Y, 0), rg.Point3d(e.X, e.Y, 0))
            for bdy in boundaries:
                for seg in trim_line_to_curve(flat_sb, bdy):
                    if seg.GetLength() > 0.1:
                        seg_z = seg.DuplicateCurve()
                        seg_z.Translate(rg.Vector3d(0, 0, s.Z))
                        trimmed.append(seg_z)
        else:
            mid = sb.PointAtNormalizedLength(0.5)
            mid_2d = rg.Point3d(mid.X, mid.Y, 0)
            for bdy in boundaries:
                if bdy.Contains(mid_2d, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                    trimmed.append(sb)
                    break
    return trimmed


def subdivide_beams(beam_list, max_seg_len=0.5):
    """Subdivide all beams into short straight segments so Karamba
    can merge endpoints within its limit distance.
    Explodes PolyCurves, then divides each segment into chunks <= max_seg_len."""
    result = []
    for crv in beam_list:
        # Explode PolyCurves into individual segments
        segs = [crv]
        try:
            ds = crv.DuplicateSegments()
            if ds and len(ds) > 0:
                segs = list(ds)
        except:
            pass

        for seg in segs:
            seg_len = seg.GetLength()
            if seg_len < 0.05:
                continue
            n = max(1, int(math.ceil(seg_len / max_seg_len)))
            for i in range(n):
                t0 = float(i) / n
                t1 = float(i + 1) / n
                p0 = seg.PointAtNormalizedLength(t0)
                p1 = seg.PointAtNormalizedLength(min(t1, 1.0))
                if p0.DistanceTo(p1) > 0.01:
                    result.append(rg.LineCurve(p0, p1))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# COLUMN GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_columns(nf, fh, span, s_type, p_top_rotation, floor_crvs_flat,
                     all_beams, primary_beams, secondary_beams,
                     void_col_floors, make_void_fn=None, b_shape=0,
                     core_cx=None, core_cy=None, core_size=0,
                     stilt_col_span=None):
    """Generate column lines for all floors.
    make_void_fn(fi) returns a plan-void curve (L/U/courtyard) or None.
    b_shape: base shape index for radial vs orthogonal grid in void zones.
    core_cx/cy/size: RC Core center and size — stilt columns inside core are excluded.
    stilt_col_span: column spacing for stilt/sky-garden void zones (matches massing grid).
    Returns (col_lines, col_points)."""
    col_lns = []
    col_pts = []
    col_hash = set()
    has_twist = abs(p_top_rotation) > 0.001

    # Neighbor-aware dedup — prevents near-duplicate columns.
    # Uses grid cells + neighbor check to handle grid-boundary cases.
    _SNAP = 0.5
    _SNAP_SQ = _SNAP * _SNAP

    def _sk(x, y):
        return (round(x / _SNAP) * _SNAP, round(y / _SNAP) * _SNAP)

    def _nearby(pts, x, y):
        """Return key of existing point within _SNAP, or None."""
        rk = _sk(x, y)
        for dx in (-_SNAP, 0, _SNAP):
            for dy in (-_SNAP, 0, _SNAP):
                nk = (rk[0] + dx, rk[1] + dy)
                if nk in pts:
                    ep = pts[nk]
                    if (ep.X - x) ** 2 + (ep.Y - y) ** 2 < _SNAP_SQ:
                        return nk
        return None

    def _put(pts, x, y, pt, force=False):
        """Insert pt into pts dict. If force, overwrite nearby point."""
        rk = _sk(x, y)
        nk = _nearby(pts, x, y)
        if nk is not None:
            if force and nk != rk:
                del pts[nk]  # remove old neighbor, replace with exact pos
            elif not force:
                return  # too close to existing, skip
        pts[rk] = pt

    for fi in range(nf):
        z_bot = fi * fh
        z_top = (fi + 1) * fh

        if fi in void_col_floors:
            continue

        pts_at_floor = {}
        _n_beams_at_z = 0

        # Beam endpoints at this floor
        for b in all_beams:
            if abs(b.PointAtStart.Z - z_bot) > 0.05:
                continue
            _n_beams_at_z += 1
            for pt in [b.PointAtStart, b.PointAtEnd]:
                _put(pts_at_floor, pt.X, pt.Y, pt)

        # Twist computation
        if has_twist:
            t_bot = float(fi) / max(1, nf)
            t_top = float(fi + 1) / max(1, nf)
            delta_deg = (t_top - t_bot) * p_top_rotation
            fi_center = get_centroid(floor_crvs_flat[fi])
        else:
            delta_deg = 0.0
            fi_center = None

        # Primary beam division at span intervals
        for pb in primary_beams:
            if pb is None:
                continue
            if abs(pb.PointAtStart.Z - z_bot) > 0.05:
                continue
            pb_len = pb.GetLength()
            if pb_len < 0.1:
                continue
            n_div = max(1, int(math.ceil(pb_len / span)))
            for di in range(n_div + 1):
                t_norm = float(di) / n_div
                pt = pb.PointAtNormalizedLength(t_norm) if t_norm < 1.0 else pb.PointAtEnd
                _put(pts_at_floor, pt.X, pt.Y, pt)

        # Secondary beam division at span intervals
        _sec_at_z = []
        for sb in secondary_beams:
            if sb is None:
                continue
            if abs(sb.PointAtStart.Z - z_bot) > 0.05:
                continue
            _sec_at_z.append(sb)
            sb_len = sb.GetLength()
            if sb_len < 0.1:
                continue
            n_div = max(1, int(math.ceil(sb_len / span)))
            for di in range(n_div + 1):
                t_norm = float(di) / n_div
                pt = sb.PointAtNormalizedLength(t_norm) if t_norm < 1.0 else sb.PointAtEnd
                _put(pts_at_floor, pt.X, pt.Y, pt)

        # Ring x Radial intersection points (internal grid crossings)
        _pri_at_z = [pb for pb in primary_beams if pb is not None
                     and abs(pb.PointAtStart.Z - z_bot) < 0.05]
        for pb in _pri_at_z:
            for sb in _sec_at_z:
                try:
                    ix = rg.Intersect.Intersection.CurveCurve(pb, sb, 0.1, 0.1)
                    if ix:
                        for ii in range(ix.Count):
                            ipt = ix[ii].PointA
                            _put(pts_at_floor, ipt.X, ipt.Y, ipt)
                except:
                    pass

        # _void_crv is computed later (after perimeter sampling, before purge).
        # This ensures next-floor projection and perimeter sampling run
        # without void filtering — only the purge and Stage 2 check filter.
        _void_crv = None

        def _not_in_void(bpt):
            """Check point is not inside void. Rect uses strict check
            (boundary = void). Ellipse uses lenient (boundary = slab edge)."""
            if _void_crv is None:
                return True
            _tv = rg.Point3d(bpt.X, bpt.Y, 0)
            if b_shape == 0:
                # Rect: boundary points are in void
                return _void_crv.Contains(_tv, rg.Plane.WorldXY, 0.05) == rg.PointContainment.Outside
            else:
                # Ellipse: only exclude strictly inside
                return _void_crv.Contains(_tv, rg.Plane.WorldXY, 0.001) != rg.PointContainment.Inside

        # Next-floor beam/slab endpoints projected down
        next_pri = []
        next_sec = []
        next_crvs = []
        for b in all_beams:
            if abs(b.PointAtStart.Z - z_top) > 0.05:
                continue
            next_crvs.append(b)
        for pb in primary_beams:
            if pb is None:
                continue
            if abs(pb.PointAtStart.Z - z_top) > 0.05:
                continue
            next_crvs.append(pb)
            next_pri.append(pb)
        for sb in secondary_beams:
            if sb is None:
                continue
            if abs(sb.PointAtStart.Z - z_top) > 0.05:
                continue
            next_sec.append(sb)

        for b in next_crvs:
            pts_to_add = [b.PointAtStart, b.PointAtEnd]
            b_len = b.GetLength()
            if b_len > span:
                n_div = max(1, int(math.ceil(b_len / span)))
                for di in range(1, n_div):
                    pts_to_add.append(b.PointAtNormalizedLength(float(di) / n_div))
            for pt in pts_to_add:
                if abs(delta_deg) > 0.001 and fi_center is not None:
                    rad = math.radians(-delta_deg)
                    cos_a, sin_a = math.cos(rad), math.sin(rad)
                    dx = pt.X - fi_center.X
                    dy = pt.Y - fi_center.Y
                    bot_pt = rg.Point3d(fi_center.X + dx*cos_a - dy*sin_a,
                                        fi_center.Y + dx*sin_a + dy*cos_a, z_bot)
                else:
                    bot_pt = rg.Point3d(pt.X, pt.Y, z_bot)
                if _not_in_void(bot_pt):
                    _put(pts_at_floor, bot_pt.X, bot_pt.Y, bot_pt)

        # Next-floor ring x radial intersections projected down
        for pb in next_pri:
            for sb in next_sec:
                try:
                    ix = rg.Intersect.Intersection.CurveCurve(pb, sb, 0.1, 0.1)
                    if ix:
                        for ii in range(ix.Count):
                            ipt = ix[ii].PointA
                            if abs(delta_deg) > 0.001 and fi_center is not None:
                                rad = math.radians(-delta_deg)
                                cos_a, sin_a = math.cos(rad), math.sin(rad)
                                dx = ipt.X - fi_center.X
                                dy = ipt.Y - fi_center.Y
                                bot_pt = rg.Point3d(fi_center.X + dx*cos_a - dy*sin_a,
                                                    fi_center.Y + dx*sin_a + dy*cos_a, z_bot)
                            else:
                                bot_pt = rg.Point3d(ipt.X, ipt.Y, z_bot)
                            if _not_in_void(bot_pt):
                                _put(pts_at_floor, bot_pt.X, bot_pt.Y, bot_pt)
                except:
                    pass

        # Compute plan void curve for this floor — after next-floor projection
        # (so _not_in_void is no-op) but before perimeter sampling (so _perim_ok
        # can filter void-area perimeter points like building corners in the void).
        if make_void_fn is not None:
            try:
                _vc = make_void_fn(fi)
                if _vc is not None:
                    _vc_flat = _vc.DuplicateCurve()
                    bb_vc = _vc_flat.GetBoundingBox(True)
                    if abs(bb_vc.Min.Z) > 0.01:
                        _vc_flat.Translate(rg.Vector3d(0, 0, -bb_vc.Min.Z))
                    _vc_flat = ensure_ccw(_vc_flat)
                    if has_twist:
                        t_v = float(fi) / max(1, nf)
                        tw_deg = t_v * p_top_rotation
                        if abs(tw_deg) > 0.001:
                            _vc_flat = rotate_curve(_vc_flat, tw_deg, get_centroid(floor_crvs_flat[fi]))
                    if _vc_flat.IsClosed:
                        _void_crv = _vc_flat
            except:
                pass

        # Explicit floor-curve perimeter sampling — guarantees edge columns.
        # Runs AFTER void computation so void-area points are filtered.
        # For rigid shapes (not ellipse/circle), perimeter points OVERWRITE
        # beam points so columns sit exactly on the plate edge.
        _rigid = b_shape not in (1, 2)
        if fi < len(floor_crvs_flat):
            _fc_edge = floor_crvs_flat[fi]
            if _fc_edge is not None and _fc_edge.IsClosed:
                _fc_len = _fc_edge.GetLength()
                if _fc_len > 1.0:
                    def _perim_ok(px, py):
                        """Check point is strictly outside plan void (not inside or on boundary)."""
                        if _void_crv is None:
                            return True
                        pv = rg.Point3d(px, py, 0)
                        return _void_crv.Contains(pv, rg.Plane.WorldXY, 0.05) == rg.PointContainment.Outside

                    # 1) Corner / kink / control points
                    try:
                        _t_disc = []
                        t_val = 0.0
                        while True:
                            ok, t_val = _fc_edge.GetNextDiscontinuity(
                                rg.Continuity.C1_locus_continuous, t_val, _fc_edge.Domain.Max)
                            if not ok:
                                break
                            _t_disc.append(t_val)
                        for _td in _t_disc:
                            _cp = _fc_edge.PointAt(_td)
                            if _perim_ok(_cp.X, _cp.Y):
                                _put(pts_at_floor, _cp.X, _cp.Y,
                                     rg.Point3d(_cp.X, _cp.Y, z_bot), force=_rigid)
                    except:
                        pass
                    # BB corners
                    _fc_bb = _fc_edge.GetBoundingBox(True)
                    for _corner in [rg.Point3d(_fc_bb.Min.X, _fc_bb.Min.Y, 0),
                                    rg.Point3d(_fc_bb.Max.X, _fc_bb.Min.Y, 0),
                                    rg.Point3d(_fc_bb.Max.X, _fc_bb.Max.Y, 0),
                                    rg.Point3d(_fc_bb.Min.X, _fc_bb.Max.Y, 0)]:
                        _cc = _fc_edge.Contains(_corner, rg.Plane.WorldXY, 0.05)
                        if _cc != rg.PointContainment.Outside and _perim_ok(_corner.X, _corner.Y):
                            _put(pts_at_floor, _corner.X, _corner.Y,
                                 rg.Point3d(_corner.X, _corner.Y, z_bot), force=_rigid)
                    # 2) Uniform arc-length samples along perimeter
                    _n_edge = max(8, int(math.ceil(_fc_len / span)))
                    for _ei in range(_n_edge):
                        _t_e = float(_ei) / _n_edge
                        _ep = _fc_edge.PointAtNormalizedLength(_t_e)
                        if _perim_ok(_ep.X, _ep.Y):
                            _put(pts_at_floor, _ep.X, _ep.Y,
                                 rg.Point3d(_ep.X, _ep.Y, z_bot), force=_rigid)

        # Purge beam-derived points that are strictly INSIDE the void.
        # Points ON the void boundary are kept — they sit on the L-shaped
        # outline beam and form valid structural connections.
        if _void_crv is not None:
            _to_remove = []
            for rk, pt in pts_at_floor.items():
                pv = rg.Point3d(pt.X, pt.Y, 0)
                if _void_crv.Contains(pv, rg.Plane.WorldXY, 0.05) == rg.PointContainment.Inside:
                    _to_remove.append(rk)
            for rk in _to_remove:
                del pts_at_floor[rk]

        # Transition filter
        _apply_filter = False
        _filter_crv = None
        # Backward: this floor smaller than previous (e.g. first tower floor)
        if fi > 0:
            prev_a = get_area(floor_crvs_flat[fi - 1])
            curr_a = get_area(floor_crvs_flat[fi])
            if prev_a > 0 and curr_a < prev_a * 0.85:
                _filter_crv = ensure_ccw(floor_crvs_flat[fi])
                _apply_filter = True
        # Forward: next floor smaller (podium+tower, etc.) — not for stepped
        if not _apply_filter and s_type != 2:
            if (fi + 1) < len(floor_crvs_flat):
                curr_f = get_area(floor_crvs_flat[fi])
                next_f = get_area(floor_crvs_flat[fi + 1])
                if curr_f > 0 and next_f < curr_f * 0.85:
                    _filter_crv = ensure_ccw(floor_crvs_flat[fi + 1])
                    _apply_filter = True
                    # Ensure tower beam grid points are in pts_at_floor
                    # (next-floor projection may miss points if grids don't align)
                    # Skip points that land inside or on boundary of plan void.
                    def _fwd_ok(bpt):
                        if _void_crv is None:
                            return True
                        _tv = rg.Point3d(bpt.X, bpt.Y, 0)
                        return _void_crv.Contains(_tv, rg.Plane.WorldXY, 0.05) == rg.PointContainment.Outside

                    _next_fi = fi + 1
                    _nz = _next_fi * fh
                    for pb in primary_beams:
                        if pb is None or abs(pb.PointAtStart.Z - _nz) > 0.05:
                            continue
                        pb_len = pb.GetLength()
                        if pb_len < 0.1:
                            continue
                        n_div = max(1, int(math.ceil(pb_len / span)))
                        for di in range(n_div + 1):
                            t_norm = float(di) / n_div
                            pt = pb.PointAtNormalizedLength(t_norm) if t_norm < 1.0 else pb.PointAtEnd
                            bot_pt = rg.Point3d(pt.X, pt.Y, z_bot)
                            if _fwd_ok(bot_pt):
                                _put(pts_at_floor, bot_pt.X, bot_pt.Y, bot_pt)
                    for sb in secondary_beams:
                        if sb is None or abs(sb.PointAtStart.Z - _nz) > 0.05:
                            continue
                        sb_len = sb.GetLength()
                        if sb_len < 0.1:
                            continue
                        n_div = max(1, int(math.ceil(sb_len / span)))
                        for di in range(n_div + 1):
                            t_norm = float(di) / n_div
                            pt = sb.PointAtNormalizedLength(t_norm) if t_norm < 1.0 else sb.PointAtEnd
                            bot_pt = rg.Point3d(pt.X, pt.Y, z_bot)
                            if _fwd_ok(bot_pt):
                                _put(pts_at_floor, bot_pt.X, bot_pt.Y, bot_pt)
                    # Ring x radial intersections from tower floor
                    _t_pri = [pb for pb in primary_beams if pb is not None
                              and abs(pb.PointAtStart.Z - _nz) < 0.05]
                    _t_sec = [sb for sb in secondary_beams if sb is not None
                              and abs(sb.PointAtStart.Z - _nz) < 0.05]
                    for pb in _t_pri:
                        for sb in _t_sec:
                            try:
                                ix = rg.Intersect.Intersection.CurveCurve(pb, sb, 0.1, 0.1)
                                if ix:
                                    for ii in range(ix.Count):
                                        ipt = ix[ii].PointA
                                        bot_pt = rg.Point3d(ipt.X, ipt.Y, z_bot)
                                        if _fwd_ok(bot_pt):
                                            _put(pts_at_floor, bot_pt.X, bot_pt.Y, bot_pt)
                            except:
                                pass

        # Fallback: if pts_at_floor is nearly empty for a non-void floor,
        # generate grid points from the floor curve itself
        if len(pts_at_floor) < 4 and fi < len(floor_crvs_flat):
            fc = floor_crvs_flat[fi]
            fc_bb = fc.GetBoundingBox(True)
            fc_W = fc_bb.Max.X - fc_bb.Min.X
            fc_D = fc_bb.Max.Y - fc_bb.Min.Y
            fc_c = get_centroid(fc)
            _use_rad = b_shape in (1, 2, 3, 4)
            if _use_rad:
                r_max = max(fc_W, fc_D) / 2.0
                n_r = max(2, int(math.ceil(r_max / span)))
                perim = math.pi * (3*(fc_W/2+fc_D/2) - math.sqrt((3*fc_W/2+fc_D/2)*(fc_W/2+3*fc_D/2)))
                n_a = max(8, int(math.ceil(perim / span)))
                for ri in range(n_r + 1):
                    sf = 1.0 - float(ri) / (n_r + 1) if ri < n_r else 0.05
                    ring_r = r_max * sf
                    for ai in range(n_a):
                        ang = ai * 2.0 * math.pi / n_a
                        px = fc_c.X + ring_r * math.cos(ang) * (fc_W / max(fc_W, fc_D))
                        py = fc_c.Y + ring_r * math.sin(ang) * (fc_D / max(fc_W, fc_D))
                        pt_chk = rg.Point3d(px, py, 0)
                        if fc.Contains(pt_chk, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                            _put(pts_at_floor, px, py, rg.Point3d(px, py, z_bot))
            else:
                nx_f = max(2, int(math.ceil(fc_W / span)))
                ny_f = max(2, int(math.ceil(fc_D / span)))
                for ix_f in range(nx_f + 1):
                    for iy_f in range(ny_f + 1):
                        px = fc_bb.Min.X + ix_f * fc_W / nx_f
                        py = fc_bb.Min.Y + iy_f * fc_D / ny_f
                        pt_chk = rg.Point3d(px, py, 0)
                        if fc.Contains(pt_chk, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                            _put(pts_at_floor, px, py, rg.Point3d(px, py, z_bot))

        _pre_filter = len(pts_at_floor)
        _col_added = 0

        # Create column segments
        for rk, pt in pts_at_floor.items():
            if abs(delta_deg) > 0.001 and fi_center is not None:
                rad = math.radians(delta_deg)
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                dx = pt.X - fi_center.X
                dy = pt.Y - fi_center.Y
                top_x = fi_center.X + dx*cos_a - dy*sin_a
                top_y = fi_center.Y + dx*sin_a + dy*cos_a
            else:
                top_x, top_y = pt.X, pt.Y

            if _apply_filter and _filter_crv is not None and _filter_crv.IsClosed:
                pt_2d = rg.Point3d(pt.X, pt.Y, 0)
                if _filter_crv.Contains(pt_2d, rg.Plane.WorldXY, 0.3) == rg.PointContainment.Outside:
                    continue

            # Skip columns strictly inside plan void (L/U/courtyard).
            if _void_crv is not None:
                pt_2d_v = rg.Point3d(pt.X, pt.Y, 0)
                if _void_crv.Contains(pt_2d_v, rg.Plane.WorldXY, 0.001) == rg.PointContainment.Inside:
                    continue

            ck = (rk[0], rk[1], round(z_bot, 1))
            if ck in col_hash:
                continue
            col_hash.add(ck)
            col_lns.append(rg.LineCurve(rg.Point3d(pt.X, pt.Y, z_bot),
                                         rg.Point3d(top_x, top_y, z_top)))
            if fi == 0:
                col_pts.append(rg.Point3d(pt.X, pt.Y, 0))
            _col_added += 1

        # Post-filter fallback: if ALL columns were filtered out, generate from
        # the current floor curve grid to ensure every floor has columns
        if _col_added == 0 and fi < len(floor_crvs_flat):
            fc = floor_crvs_flat[fi]
            fc = ensure_ccw(fc)
            fc_bb = fc.GetBoundingBox(True)
            fc_W = fc_bb.Max.X - fc_bb.Min.X
            fc_D = fc_bb.Max.Y - fc_bb.Min.Y
            if fc_W > 0.5 and fc_D > 0.5:
                fc_c = get_centroid(fc)
                _fb_use_rad = b_shape in (1, 2, 3, 4)
                _fb_pts = []
                if _fb_use_rad:
                    r_max = max(fc_W, fc_D) / 2.0
                    n_r = max(2, int(math.ceil(r_max / span)))
                    perim = math.pi * (3*(fc_W/2+fc_D/2) - math.sqrt((3*fc_W/2+fc_D/2)*(fc_W/2+3*fc_D/2)))
                    n_a = max(8, int(math.ceil(perim / span)))
                    for ri in range(n_r + 1):
                        sf = 1.0 - float(ri) / (n_r + 1) if ri < n_r else 0.05
                        ring_r = r_max * sf
                        for ai in range(n_a):
                            ang = ai * 2.0 * math.pi / n_a
                            px = fc_c.X + ring_r * math.cos(ang) * (fc_W / max(fc_W, fc_D))
                            py = fc_c.Y + ring_r * math.sin(ang) * (fc_D / max(fc_W, fc_D))
                            pt_chk = rg.Point3d(px, py, 0)
                            if fc.Contains(pt_chk, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                                _fb_pts.append((px, py))
                else:
                    nx_f = max(2, int(math.ceil(fc_W / span)))
                    ny_f = max(2, int(math.ceil(fc_D / span)))
                    for ix_f in range(nx_f + 1):
                        for iy_f in range(ny_f + 1):
                            px = fc_bb.Min.X + ix_f * fc_W / nx_f
                            py = fc_bb.Min.Y + iy_f * fc_D / ny_f
                            pt_chk = rg.Point3d(px, py, 0)
                            if fc.Contains(pt_chk, rg.Plane.WorldXY, 0.1) != rg.PointContainment.Outside:
                                _fb_pts.append((px, py))
                for (px, py) in _fb_pts:
                    # Skip if inside plan void
                    if _void_crv is not None:
                        pv = rg.Point3d(px, py, 0)
                        if _void_crv.Contains(pv, rg.Plane.WorldXY, 0.01) == rg.PointContainment.Inside:
                            continue
                    rk_fb = _sk(px, py)
                    ck_fb = (rk_fb[0], rk_fb[1], round(z_bot, 1))
                    if ck_fb in col_hash:
                        continue
                    col_hash.add(ck_fb)
                    if abs(delta_deg) > 0.001 and fi_center is not None:
                        rad = math.radians(delta_deg)
                        cos_a, sin_a = math.cos(rad), math.sin(rad)
                        dx = px - fi_center.X
                        dy = py - fi_center.Y
                        top_x = fi_center.X + dx*cos_a - dy*sin_a
                        top_y = fi_center.Y + dx*sin_a + dy*cos_a
                    else:
                        top_x, top_y = px, py
                    col_lns.append(rg.LineCurve(rg.Point3d(px, py, z_bot),
                                                 rg.Point3d(top_x, top_y, z_top)))
                    if fi == 0:
                        col_pts.append(rg.Point3d(px, py, 0))
                    _col_added += 1
                if _col_added > 0:
                    print("  Col fi={}: FALLBACK generated {} cols from floor curve".format(fi, _col_added))

        # Diagnostic: per-floor column count
        _filt_label = "back" if _apply_filter and fi > 0 and get_area(floor_crvs_flat[fi]) < get_area(floor_crvs_flat[fi-1]) * 0.85 else ("fwd" if _apply_filter else "none")
        print("  Col fi={}: beams={} pts={} filt={} ({}) cols={}".format(
            fi, _n_beams_at_z, _pre_filter, _filt_label,
            "void" if _void_crv is not None else "-", _col_added))

    # ── Stilt / SkyGarden void-zone columns ──────────────────────────────────
    # Use regular column positions from the cap floor (already in col_hash).
    # Every regular column at the cap floor gets a matching void-zone column
    # below it, ensuring exact Karamba node sharing and valid load paths.
    if void_col_floors:
        sorted_voids = sorted(void_col_floors)
        ranges = []
        rng_start = sorted_voids[0]
        rng_end = sorted_voids[0]
        for vi in sorted_voids[1:]:
            if vi == rng_end + 1:
                rng_end = vi
            else:
                ranges.append((rng_start, rng_end))
                rng_start = vi
                rng_end = vi
        ranges.append((rng_start, rng_end))

        for (v_start, v_end) in ranges:
            z_void_bot = v_start * fh
            z_void_top = (v_end + 1) * fh

            # Collect regular column positions at cap floor
            _cap_z_round = round(z_void_top, 1)
            col_positions = []
            for ck_entry in col_hash:
                if abs(ck_entry[2] - _cap_z_round) < 0.05:
                    col_positions.append((ck_entry[0], ck_entry[1]))

            # For sky garden, also include columns from floor below
            if v_start > 0:
                _below_z_round = round((v_start - 1) * fh, 1)
                _cap_set = set(col_positions)
                for ck_entry in col_hash:
                    if abs(ck_entry[2] - _below_z_round) < 0.05:
                        bp = (ck_entry[0], ck_entry[1])
                        if bp not in _cap_set:
                            col_positions.append(bp)

            print("  VoidCol range={}-{}: cap_col_positions={}".format(
                v_start, v_end, len(col_positions)))

            for (cx_c, cy_c) in col_positions:
                rk = _sk(cx_c, cy_c)
                ck = (rk[0], rk[1], round(z_void_bot, 1))
                if ck in col_hash:
                    continue
                col_hash.add(ck)
                col_lns.append(rg.LineCurve(
                    rg.Point3d(cx_c, cy_c, z_void_bot),
                    rg.Point3d(cx_c, cy_c, z_void_top)))
                if v_start == 0:
                    col_pts.append(rg.Point3d(cx_c, cy_c, 0))

    return col_lns, col_pts


# ══════════════════════════════════════════════════════════════════════════════
# LATERAL SYSTEM / CORE GEOMETRY
# ══════════════════════════════════════════════════════════════════════════════

def make_box(ox, oy, oz, sx, sy, sz):
    plane = rg.Plane(rg.Point3d(ox, oy, oz), rg.Vector3d.ZAxis)
    box = rg.Box(plane, rg.Interval(0, sx), rg.Interval(0, sy), rg.Interval(0, sz))
    return box.ToBrep()


def _crv_at_z(crv, z):
    """Duplicate curve and move to Z elevation."""
    c = crv.DuplicateCurve()
    c.Translate(rg.Vector3d(0, 0, z))
    return c


def _offset_inward(crv, dist):
    """Offset a closed CCW curve inward by dist. Returns offset curve or None."""
    crv = ensure_ccw(crv)
    flat = flatten_crv(crv)
    centroid = get_centroid(flat)
    try:
        offsets = flat.Offset(rg.Plane.WorldXY, -dist, 0.01,
                              rg.CurveOffsetCornerStyle.Sharp)
        if offsets and len(offsets) > 0:
            best = None
            for oc in offsets:
                if oc.IsClosed and get_area(oc) < get_area(flat):
                    best = oc
                    break
            if best is not None:
                return ensure_ccw(best)
    except:
        pass
    # Fallback: scale-based shrink
    try:
        ratio = 1.0 - (2.0 * dist / max(1.0, max(
            flat.GetBoundingBox(True).Max.X - flat.GetBoundingBox(True).Min.X,
            flat.GetBoundingBox(True).Max.Y - flat.GetBoundingBox(True).Min.Y)))
        if ratio < 0.1:
            return None
        dup = flat.DuplicateCurve()
        xf = rg.Transform.Scale(rg.Plane(centroid, rg.Vector3d.ZAxis), ratio, ratio, 1.0)
        dup.Transform(xf)
        return ensure_ccw(dup)
    except:
        return None


def make_wall_ring(outer_crv, wall_t, z_base, height):
    """Create wall Breps between outer_crv and its inward offset.
    Uses loft + planar caps. Returns list of Brep."""
    flat = flatten_crv(outer_crv)
    flat = ensure_ccw(flat)
    inner = _offset_inward(flat, wall_t)
    if inner is None:
        return []

    outer_bot = _crv_at_z(flat, z_base)
    outer_top = _crv_at_z(flat, z_base + height)
    inner_bot = _crv_at_z(inner, z_base)
    inner_top = _crv_at_z(inner, z_base + height)

    breps = []
    try:
        ol = rg.Brep.CreateFromLoft([outer_bot, outer_top],
                                     rg.Point3d.Unset, rg.Point3d.Unset,
                                     rg.LoftType.Straight, False)
        if ol:
            breps.extend(ol)
    except:
        pass
    try:
        il = rg.Brep.CreateFromLoft([inner_bot, inner_top],
                                     rg.Point3d.Unset, rg.Point3d.Unset,
                                     rg.LoftType.Straight, False)
        if il:
            breps.extend(il)
    except:
        pass
    # Annular caps (top + bottom)
    for (oc, ic) in [(outer_bot, inner_bot), (outer_top, inner_top)]:
        try:
            cap = rg.Brep.CreatePlanarBreps([oc, ic], 0.01)
            if cap:
                breps.extend(cap)
        except:
            pass
    # Join into solid(s)
    if len(breps) > 1:
        try:
            joined = rg.Brep.JoinBreps(breps, 0.01)
            if joined and len(joined) > 0:
                return list(joined)
        except:
            pass
    return breps

def hollow_core(cx, cy, cs, wt, h, z_base=0):
    """Single hollow core from z_base to z_base+h."""
    cs2 = cs / 2
    return [b for b in [
        make_box(cx - cs2, cy + cs2 - wt, z_base, cs, wt, h),
        make_box(cx - cs2, cy - cs2, z_base, cs, wt, h),
        make_box(cx + cs2 - wt, cy - cs2 + wt, z_base, wt, cs - 2*wt, h),
        make_box(cx - cs2, cy - cs2 + wt, z_base, wt, cs - 2*wt, h),
    ] if b]


def _solid_z_ranges(nf, fh, void_col_floors):
    """Compute Z ranges where structure is solid (non-void).
    Returns list of (z_bot, z_top) tuples."""
    if not void_col_floors:
        return [(0, nf * fh)]
    solid = []
    i = 0
    while i <= nf:
        # skip void floors
        if i in void_col_floors:
            i += 1
            continue
        # start of solid range
        start = i
        while i <= nf and i not in void_col_floors:
            i += 1
        # solid from start to i (but capped at nf)
        end = min(i, nf)
        if end > start:
            solid.append((start * fh, end * fh))
    return solid if solid else [(0, nf * fh)]


def build_lateral_system(lat, p_type, W, D, H, nf, fh,
                         cx, cy, x0, y0, x1, y1,
                         p_void_ratio, p_void_corner, p_bar_ratio,
                         p_split_gap, point_in_void_fn,
                         void_col_floors=None,
                         floor_crvs=None, b_shape=0,
                         make_void_fn=None, has_twist=False,
                         top_rotation=0.0):
    """Build lateral system geometry. Returns (core_geom, core_note).
    void_col_floors: set of floor indices where core geometry is voided.
    floor_crvs: per-floor curves for curve-based perimeter walls.
    """
    wall_t = max(0.20, round(fh / 15.0, 2))
    _vcf = void_col_floors if void_col_floors else set()
    core_geom = []
    ref_W = W * (1.0 - p_void_ratio * 0.5) if p_type >= 4 else W
    ref_D = D * (1.0 - p_void_ratio * 0.5) if p_type >= 4 else D
    is_split = (p_type == 6)
    bar_W = W * p_bar_ratio if is_split else W

    # Per-plan-type center adjustments
    l_cx, l_cy = cx, cy
    if p_type == 4:
        vw, vd = W * p_void_ratio, D * p_void_ratio
        if p_void_corner == 0:   l_cx, l_cy = cx - vw*0.3, cy - vd*0.3
        elif p_void_corner == 1: l_cx, l_cy = cx + vw*0.3, cy - vd*0.3
        elif p_void_corner == 2: l_cx, l_cy = cx + vw*0.3, cy + vd*0.3
        else:                    l_cx, l_cy = cx - vw*0.3, cy + vd*0.3
    u_cx, u_cy = cx, cy
    if p_type == 5:
        u_cy = cy - D * p_void_ratio * 0.3

    if is_split:
        bar_cx_l = cx - W/2 + bar_W/2
        bar_cx_r = cx + W/2 - bar_W/2

    if lat == 0:  # RC Core — always at massing center, full height
        cs = max(2.0, round(min(W, D) * 0.18, 2))
        return hollow_core(cx, cy, cs, wall_t, H), "core={:.2f}m".format(cs)

    elif lat == 1:  # Perimeter Walls — curve-based per floor
        if floor_crvs is not None and len(floor_crvs) > 0:
            # Batch consecutive identical-area floors into taller segments
            fi = 0
            while fi < nf:
                if fi in _vcf:
                    fi += 1
                    continue
                # Find how many consecutive non-void floors share the same area
                base_a = get_area(floor_crvs[fi])
                seg_end = fi + 1
                while seg_end < nf and seg_end not in _vcf:
                    next_a = get_area(floor_crvs[seg_end])
                    if base_a > 0 and abs(next_a - base_a) / base_a > 0.02:
                        break
                    seg_end += 1
                z_base = fi * fh
                seg_h = (seg_end - fi) * fh
                fi_crv = floor_crvs[fi]
                # Outer wall ring
                ring = make_wall_ring(fi_crv, wall_t, z_base, seg_h)
                core_geom.extend(ring)
                # For courtyard: inner wall ring around void
                if make_void_fn is not None and p_type in (1, 2, 3):
                    void_crv = make_void_fn(fi)
                    if void_crv is not None:
                        if has_twist and abs(top_rotation) > 0.001:
                            t = float(fi) / max(1, nf)
                            tw = t * top_rotation
                            if abs(tw) > 0.001:
                                void_crv = rotate_curve(void_crv, tw,
                                                        get_centroid(fi_crv))
                        inner_ring = make_wall_ring(void_crv, wall_t, z_base, seg_h)
                        core_geom.extend(inner_ring)
                fi = seg_end
            return [b for b in core_geom if b], "walls t={:.2f}m".format(wall_t)
        else:
            # Fallback: box-based for when no floor curves
            if W >= D:
                core_geom = [make_box(x0, y0, 0, wall_t, D, H),
                             make_box(x1 - wall_t, y0, 0, wall_t, D, H)]
            else:
                core_geom = [make_box(x0, y0, 0, W, wall_t, H),
                             make_box(x0, y1 - wall_t, 0, W, wall_t, H)]
            return [b for b in core_geom if b], "walls t={:.2f}m".format(wall_t)

    elif lat == 2:  # Moment Frame
        return [], "No shear walls"

    elif lat == 3:  # Reserved (Coupled Cores removed)
        return [], "No lateral (reserved)"

    return [], "Unknown"
