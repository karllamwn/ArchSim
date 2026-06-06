# ArchSim Ladybug Result Extractor
# ─────────────────────────────────────────────────────────────────────────────
# Extracts usable numbers from a Ladybug analysis and bundles them into
# export_json for gh-params-export.py. Mirrors gh-karamba-extract.py.
#
# Feed this node the outputs of your Ladybug components (Incident Radiation,
# Direct Sun Hours, etc). All inputs are lists of numbers — one value per
# analysis point on the facade / roof mesh.
#
# INPUTS (wire from your Ladybug definition):
#   radiation_values  List<Number> — annual radiation per facade point, kWh/m²
#                                    (from LB Incident Radiation "results")
#   sun_hours         List<Number> — annual direct sun hours per facade point
#                                    (from LB Direct Sun Hours "results")
#   face_areas        List<Number> — area of each analysis face, m² (optional;
#                                    enables area-weighted averages). If empty,
#                                    a simple arithmetic mean is used.
#
# OUTPUTS (rename slots on the component to match these names):
#   lb_annualSolarHours   Number — avg annual direct sun hours on facade
#   lb_avgRadiation       Number — avg annual radiation on facade, kWh/m²
#   lb_peakRadiation      Number — peak facade radiation, kWh/m²
#   lb_overheatingRisk    String — "LOW"/"MODERATE"/"HIGH"
#   export_json           String — JSON bundle (→ gh-params-export ladybug input)
#   summary               String — human-readable summary
#
# NOTE: EUI is NOT computed here — that depends on buildingUse and belongs
# on the JS side (hops.js / mep.js) where buildingUse is already in params.
# This extractor only outputs what Ladybug actually measures.
# ─────────────────────────────────────────────────────────────────────────────

import json

def _flt_list(src):
    if src is None:
        return []
    result = []
    try:
        it = list(src)
    except:
        it = [src]
    for v in it:
        if v is None:
            continue
        try:
            result.append(float(v))
        except:
            pass
    return result

_rad   = _flt_list(radiation_values)
_sun   = _flt_list(sun_hours)
_areas = _flt_list(face_areas)

def _mean(vals, weights=None):
    if not vals:
        return 0.0
    if weights and len(weights) == len(vals):
        wsum = sum(weights)
        if wsum > 0:
            return sum(v * w for v, w in zip(vals, weights)) / wsum
    return sum(vals) / len(vals)

# ── Solar / radiation metrics ────────────────────────────────────────────────
lb_annualSolarHours = round(_mean(_sun, _areas if _areas else None), 0)
lb_avgRadiation     = round(_mean(_rad, _areas if _areas else None), 1)
lb_peakRadiation    = round(max(_rad), 1) if _rad else 0.0

# ── Overheating risk from avg facade radiation ──────────────────────────────
# Vancouver climate (climate zone 5). Typical annual facade radiation ranges:
#   < 400 kWh/m²     → LOW  (mostly shaded / north-facing dominant)
#   400-700 kWh/m²   → MODERATE
#   > 700 kWh/m²     → HIGH (south/west-heavy, high glazing ratio)
if lb_avgRadiation >= 700:
    lb_overheatingRisk = "HIGH"
elif lb_avgRadiation >= 400:
    lb_overheatingRisk = "MODERATE"
else:
    lb_overheatingRisk = "LOW"

# ── Summary ──────────────────────────────────────────────────────────────────
summary = (
    "Facade points analysed: {} (rad) / {} (sun)\n"
    "Avg radiation: {} kWh/m2   Peak: {} kWh/m2\n"
    "Avg sun hours: {} hrs/year\n"
    "Overheating risk: {}"
).format(
    len(_rad), len(_sun),
    lb_avgRadiation, lb_peakRadiation,
    int(lb_annualSolarHours),
    lb_overheatingRisk
)

if not _rad and not _sun:
    summary = "WARNING: no Ladybug data wired in (radiation_values / sun_hours both empty)\n\n" + summary

# Also assign to print buffer so it shows in the default `out` output too
print(summary)

# ── Export JSON bundle (connect to gh-params-export ladybug input) ──────────
export_json = json.dumps({
    "annualSolarHours":  lb_annualSolarHours,
    "avgRadiation":      lb_avgRadiation,
    "peakRadiation":     lb_peakRadiation,
    "overheatingRisk":   lb_overheatingRisk,
    "pointCount":        len(_rad),
    "source":            "ladybug"
})
