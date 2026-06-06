"""
ZONING ENVELOPE GENERATOR — GHPython Component
================================================
Paste this into a GHPython component in Grasshopper.

INPUTS (right-click component → Manage Inputs):
  siteWidth        float   Site width in metres (X direction)
  siteDepth        float   Site depth in metres (Y direction)
  zoneMaxHeight    float   Maximum building height (m)
  zoneMaxFSR       float   Maximum floor space ratio
  zoneFrontSetback float   Front setback (m) — south edge (Y=0)
  zoneSideSetback  float   Side setback (m) — east/west edges
  zoneRearSetback  float   Rear setback (m) — north edge (Y=max)
  zoneMaxCoverage  float   Maximum site coverage (%)
  floor_height     float   Typical floor-to-floor height (m)

OUTPUTS (right-click component → Manage Outputs):
  out                string    Summary text (connect to Panel)
  siteBoundary       Curve     Site boundary rectangle
  buildableFootprint Curve     Buildable area after setbacks
  zoningEnvelope     Brep      3D zoning envelope (extruded)
  setbackLines       Curve[]   Individual setback offset lines
  siteArea           float     Total site area (m2)
  buildableArea      float     Buildable footprint area (m2)
  maxGFA             float     Max gross floor area (m2)
  maxFloors          int       Max floors within height limit
  envelopeVolume     float     Zoning envelope volume (m3)
  export_json        string    JSON bundle of all zoning data (connect to gh-params-export)
"""

import Rhino.Geometry as rg
import math
import json

# ── Safe coercion ─────────────────────────────────────────
def sf(val, default):
    if val is None or str(val) == "None":
        return default
    try:
        return float(val)
    except:
        return default

# ── Defaults ──────────────────────────────────────────────
siteWidth       = sf(siteWidth, 30.0)
siteDepth       = sf(siteDepth, 40.0)
zoneMaxHeight   = sf(zoneMaxHeight, 36.0)
zoneMaxFSR      = sf(zoneMaxFSR, 3.0)
zoneFrontSetback = sf(zoneFrontSetback, 0.0)
zoneSideSetback  = sf(zoneSideSetback, 0.0)
zoneRearSetback  = sf(zoneRearSetback, 0.0)
zoneMaxCoverage  = sf(zoneMaxCoverage, 100.0)
floor_height     = sf(floor_height, 3.6)

# ── Helper: join 4 lines into a closed PolyCurve ─────────
# PolyCurve (joined segments) is what Rhino rectangles produce.
# Downstream scripts rely on DuplicateSegments() returning 4 edges
# and Extrusion.Create() needs a proper closed planar curve.
def make_rect(a, b, c, d):
    segs = [
        rg.LineCurve(a, b),
        rg.LineCurve(b, c),
        rg.LineCurve(c, d),
        rg.LineCurve(d, a)
    ]
    joined = rg.Curve.JoinCurves(segs)
    if joined and len(joined) > 0:
        return joined[0]
    # Fallback
    return rg.Polyline([a, b, c, d, a]).ToNurbsCurve()

# ── Step 1: Site Boundary ─────────────────────────────────
# Rectangle at origin — front = south edge (Y=0)
p0 = rg.Point3d(0, 0, 0)
p1 = rg.Point3d(siteWidth, 0, 0)
p2 = rg.Point3d(siteWidth, siteDepth, 0)
p3 = rg.Point3d(0, siteDepth, 0)

siteBoundary = make_rect(p0, p1, p2, p3)
siteArea = siteWidth * siteDepth

# ── Step 2: Per-Edge Setback → Buildable Footprint ───────
# Front = south (Y=0) → offset inward = +Y
# Rear  = north (Y=siteDepth) → offset inward = -Y
# Left  = west  (X=0) → offset inward = +X
# Right = east  (X=siteWidth) → offset inward = -X

bx0 = zoneSideSetback              # left edge inward
bx1 = siteWidth - zoneSideSetback  # right edge inward
by0 = zoneFrontSetback             # front edge inward
by1 = siteDepth - zoneRearSetback  # rear edge inward

# Clamp to prevent negative/zero buildable area
bx0 = min(bx0, siteWidth / 2.0 - 0.1)
bx1 = max(bx1, siteWidth / 2.0 + 0.1)
by0 = min(by0, siteDepth / 2.0 - 0.1)
by1 = max(by1, siteDepth / 2.0 + 0.1)

bp0 = rg.Point3d(bx0, by0, 0)
bp1 = rg.Point3d(bx1, by0, 0)
bp2 = rg.Point3d(bx1, by1, 0)
bp3 = rg.Point3d(bx0, by1, 0)

buildableFootprint = make_rect(bp0, bp1, bp2, bp3)
buildableWidth = bx1 - bx0
buildableDepth = by1 - by0
buildableArea = buildableWidth * buildableDepth

# ── Step 3: Setback visualization lines ──────────────────
# Lines showing the setback offset from each site edge
setbackLines = []
if zoneFrontSetback > 0:
    setbackLines.append(rg.Line(rg.Point3d(0, by0, 0), rg.Point3d(siteWidth, by0, 0)).ToNurbsCurve())
if zoneRearSetback > 0:
    setbackLines.append(rg.Line(rg.Point3d(0, by1, 0), rg.Point3d(siteWidth, by1, 0)).ToNurbsCurve())
if zoneSideSetback > 0:
    setbackLines.append(rg.Line(rg.Point3d(bx0, 0, 0), rg.Point3d(bx0, siteDepth, 0)).ToNurbsCurve())
    setbackLines.append(rg.Line(rg.Point3d(bx1, 0, 0), rg.Point3d(bx1, siteDepth, 0)).ToNurbsCurve())

# ── Step 4: Calculate Metrics ────────────────────────────
maxFloors = int(math.floor(zoneMaxHeight / floor_height)) if floor_height > 0 else 0
maxGFA = siteArea * zoneMaxFSR

# ── Step 5: Apply Coverage + FSR limits to footprint ─────
# Coverage limit
maxFootprint_by_coverage = siteArea * (zoneMaxCoverage / 100.0)

# FSR limit: maxGFA / maxFloors = max footprint per floor
if maxFloors > 0:
    maxFootprint_by_FSR = maxGFA / maxFloors
else:
    maxFootprint_by_FSR = 0.0

# Effective footprint = smallest of setback area, coverage, FSR
effectiveFootprint = min(buildableArea, maxFootprint_by_coverage, maxFootprint_by_FSR)

# Determine which constraint is active
if effectiveFootprint >= buildableArea - 0.01:
    footprintLimitedBy = "Setback"
elif effectiveFootprint >= maxFootprint_by_coverage - 0.01:
    footprintLimitedBy = "Coverage"
else:
    footprintLimitedBy = "FSR"

# If coverage or FSR shrinks the footprint, scale the buildable rect inward
if effectiveFootprint < buildableArea - 0.01:
    _scale = math.sqrt(effectiveFootprint / buildableArea)
    _cx = (bx0 + bx1) / 2.0
    _cy = (by0 + by1) / 2.0
    _hw = buildableWidth / 2.0 * _scale
    _hd = buildableDepth / 2.0 * _scale
    fp0 = rg.Point3d(_cx - _hw, _cy - _hd, 0)
    fp1 = rg.Point3d(_cx + _hw, _cy - _hd, 0)
    fp2 = rg.Point3d(_cx + _hw, _cy + _hd, 0)
    fp3 = rg.Point3d(_cx - _hw, _cy + _hd, 0)
    buildableFootprint = make_rect(fp0, fp1, fp2, fp3)
    buildableWidth = _hw * 2
    buildableDepth = _hd * 2
    buildableArea = effectiveFootprint

# ── Step 6: Extrude to Zoning Envelope ───────────────────
_ebb = buildableFootprint.GetBoundingBox(True)
_ex0, _ey0 = _ebb.Min.X, _ebb.Min.Y
_ex1, _ey1 = _ebb.Max.X, _ebb.Max.Y

# Use simple box from buildable footprint bounding box (most reliable)
box = rg.Box(
    rg.Plane.WorldXY,
    rg.Interval(_ex0, _ex1),
    rg.Interval(_ey0, _ey1),
    rg.Interval(0, zoneMaxHeight)
)
zoningEnvelope = rg.Brep.CreateFromBox(box)
envelopeVolume = buildableArea * zoneMaxHeight

print("DEBUG envelope: footprint BB = ({:.1f},{:.1f}) to ({:.1f},{:.1f}), h={:.1f}".format(
    _ex0, _ey0, _ex1, _ey1, zoneMaxHeight))

# ── Summary Output ───────────────────────────────────────
print("ZONING ENVELOPE")
print("Site: {} x {} m = {:.1f} m2".format(siteWidth, siteDepth, siteArea))
print("Setbacks F/S/R: {}/{}/{} m".format(zoneFrontSetback, zoneSideSetback, zoneRearSetback))
print("Buildable: {:.1f} x {:.1f} m = {:.1f} m2 (limited by {})".format(
    buildableWidth, buildableDepth, buildableArea, footprintLimitedBy))
print("Max Height: {:.1f} m | Max Floors: {} @ {:.1f} m".format(zoneMaxHeight, maxFloors, floor_height))
print("Max FSR: {} → Max GFA: {:.1f} m2 → Max Footprint/floor: {:.1f} m2".format(
    zoneMaxFSR, maxGFA, maxFootprint_by_FSR))
print("Max Coverage: {:.0f}% → Max Footprint: {:.1f} m2".format(zoneMaxCoverage, maxFootprint_by_coverage))
print("Envelope Vol: {:.1f} m3".format(envelopeVolume))

# ── Export JSON bundle (connect to gh-params-export zoning input) ─
export_json = json.dumps({
    "siteWidth": float(siteWidth),
    "siteDepth": float(siteDepth),
    "zoneMaxHeight": float(zoneMaxHeight),
    "zoneMaxFSR": float(zoneMaxFSR),
    "zoneFrontSetback": float(zoneFrontSetback),
    "zoneSideSetback": float(zoneSideSetback),
    "zoneRearSetback": float(zoneRearSetback),
    "zoneMaxCoverage": float(zoneMaxCoverage),
    "floorHeight": float(floor_height),
    "siteArea": round(siteArea, 2),
    "buildableArea": round(buildableArea, 2),
    "maxGFA": round(maxGFA, 2),
    "maxFloors": maxFloors,
    "maxFootprintByFSR": round(maxFootprint_by_FSR, 2),
    "maxFootprintByCoverage": round(maxFootprint_by_coverage, 2),
    "effectiveFootprint": round(effectiveFootprint, 2),
    "footprintLimitedBy": footprintLimitedBy,
    "envelopeVolume": round(envelopeVolume, 2)
})
