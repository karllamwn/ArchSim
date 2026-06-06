# ArchSim Karamba Result Extractor
# ─────────────────────────────────────────────────────────────────────────────
# Extracts usable numbers from Karamba analysis for ArchSim Export.
#
# INPUTS:
#   max_disp        Number  — from Analyse "Maximum Displacement [cm]"
#   floors          Integer — number of floors (same slider as structure script)
#   floor_height    Number  — floor-to-floor height m (same slider)
#
# OUTPUTS:
#   k_utilization      Number — estimated structural utilization 0-1
#   k_maxDeflection    Number — max displacement in mm
#   k_lateralDrift     String — "LOW" / "MODERATE" / "HIGH"
#   export_json        String — JSON bundle of karamba data (connect to gh-params-export)
#   out                String — summary
# ─────────────────────────────────────────────────────────────────────────────

import json

nf = int(floors) if floors is not None else 10
fh = float(floor_height) if floor_height is not None else 3.6
H = nf * fh  # total height in meters

# Max displacement (Karamba outputs in cm)
disp_cm = float(max_disp) if max_disp is not None else 0.0
k_maxDeflection = disp_cm * 10.0  # convert cm to mm

# Rigid body modes (0 = stable)
_rigid = 0
if "rigid_modes" in dir() and rigid_modes is not None:
    try:
        _rigid = int(rigid_modes)
    except:
        _rigid = 0

# Lateral drift assessment: H/delta ratio
# H in mm, disp in mm
if k_maxDeflection > 0.001:
    H_mm = H * 1000.0
    drift_ratio = H_mm / k_maxDeflection
    if drift_ratio > 500:
        k_lateralDrift = "LOW"
    elif drift_ratio > 250:
        k_lateralDrift = "MODERATE"
    else:
        k_lateralDrift = "HIGH"
else:
    drift_ratio = 99999
    k_lateralDrift = "LOW"

# Utilization estimate from deflection limit
# Allowable = H/500 for office (serviceability)
allowable_mm = H * 1000.0 / 500.0
k_utilization = round(min(k_maxDeflection / allowable_mm, 1.0), 3) if allowable_mm > 0 else 0.0

out = (
    "Deflection: {:.1f} mm ({:.2f} cm)\n"
    "Allowable (H/500): {:.1f} mm\n"
    "Utilization: {:.1%}\n"
    "Drift ratio: H/{:.0f} -> {}"
).format(
    k_maxDeflection, disp_cm,
    allowable_mm,
    k_utilization,
    drift_ratio, k_lateralDrift
)

if _rigid > 0:
    out = "WARNING: {} rigid body modes (unstable)\n\n{}".format(_rigid, out)

# ── Export JSON bundle (connect to gh-params-export karamba input) ─
export_json = json.dumps({
    "utilization": k_utilization,
    "maxDeflection": round(k_maxDeflection, 2),
    "lateralDrift": k_lateralDrift,
    "driftRatio": round(drift_ratio, 1),
    "rigidBodyModes": _rigid,
    "stable": _rigid == 0
})
