# Embodied Carbon Reference — Early-Stage Massing Decisions

## City of Vancouver Requirements

**Source:** City of Vancouver Embodied Carbon Guidelines, October 2023

- **CoV Absolute Benchmark: 400 kgCO₂e/m²** (VBBL Section 10.4)
- Based on rezoning submission data 2017–2023
- GFA excludes parkade area
- Required scope: cradle-to-grave (A1–A5, B1–B5, C1–C4)
- At rezoning/schematic stage: Class D Indicative Estimate is sufficient
- Compliance: proposed design must be ≤ benchmark × reduction factor
- Two compliance paths: Absolute Path (400 × GFA) or Baseline Path (functionally-equivalent baseline)
- Vancouver Climate Emergency target: 40% reduction by 2030

## Concrete GWP (BC Ready-Mix)

**Source:** Concrete BC Industry-Wide EPD (EPD 348, July 2022, valid to July 2027)

GWP per 1 m³ ready-mix concrete (A1–A3, cradle-to-gate):

| Strength | GU Baseline | With SCM (20-40%) | Notes |
|----------|------------|-------------------|-------|
| 15 MPa   | 179 kgCO₂e | 153–188 kgCO₂e   | Non-structural fills |
| 20 MPa   | 194 kgCO₂e | 152–186 kgCO₂e   | Residential slabs |
| 25 MPa   | 231 kgCO₂e | 180–213 kgCO₂e   | Typical slabs |
| 30 MPa   | 270 kgCO₂e | 214–249 kgCO₂e   | Columns, beams |
| 32 MPa   | 285 kgCO₂e | 226–263 kgCO₂e   | Transfer slabs |
| 35 MPa   | 311 kgCO₂e | 245–283 kgCO₂e   | High-rise columns |
| 40 MPa   | 344 kgCO₂e | 275–316 kgCO₂e   | Shear walls, cores |
| 45 MPa   | 356 kgCO₂e | 283–323 kgCO₂e   | High-rise cores |
| 50 MPa   | 380 kgCO₂e | 300–345 kgCO₂e   | Special elements |

- SCM = Supplementary Cementitious Materials (slag/fly ash)
- GUL (Portland Limestone Cement) reduces GWP ~5-10% vs GU
- Air-entrained vs non-air: minimal GWP difference (~1-3%)

## Softwood Lumber (BC)

**Source:** CWC EPD for Canadian Softwood Lumber, February 2025

- GWP Fossil (A1–A3): **41.5 kgCO₂e/m³**
- GWP Biogenic: net zero (carbon stored ≈ carbon released at end of life)
- Density ~450 kg/m³ → ~0.09 kgCO₂e/kg (fossil only)
- Significant carbon storage benefit if long-term sequestration is credited

## Default Material Assumptions (CoV Table 1)

For early-stage estimates when materials are not yet specified:

| Element | Default Material |
|---------|-----------------|
| Foundations | Steel-reinforced concrete |
| Subgrade walls | Steel-reinforced concrete |
| Superstructure (columns, beams, slabs) | Steel-reinforced concrete |
| Long-span elements | Steel trusses |
| Exterior walls (office/commercial) | Aluminum curtain wall |
| Exterior walls (residential 7+ storeys) | Aluminum window wall |
| Exterior walls (other) | Steel-framed wall |
| Insulation (cavity) | Mineral wool batt |
| Insulation (continuous) | Heavy density mineral wool |

## Early-Stage Estimator Parameters

Parameters that influence embodied carbon at massing stage (no material selections needed):

### Structure (largest contributor, ~60-70% of total)
- **Floor count**: More floors = thicker core walls + deeper foundations. High-rise (>20F) ~15% more carbon/m² than mid-rise (6-12F)
- **Structural span**: Longer span = thicker slabs, heavier beams. Each metre beyond 8m adds ~8 kgCO₂e/m²
- **Floor plate area**: Larger plates = slightly more efficient (less core % per floor area)
- **Lateral system**: RC core is baseline at ~450 kgCO₂e/m² for mid-rise Vancouver

### Envelope (~15-25% of total)
- **WWR (window-to-wall ratio)**: Glazing ~2x more carbon per m² than opaque wall. Each 10% WWR increase adds ~12 kgCO₂e/m²
- **Plan shape**: Courtyard/L-shape = more envelope perimeter per GFA = more carbon
- **Window type**: Curtain wall > window wall > punched openings (in carbon terms)

### Other (~10-15%)
- Courtyard ratio and void ratio increase surface area
- Foundation depth (driven by height and soil conditions)
- Parkade (included in assessment scope but excluded from GFA denominator)

## Typical Ranges for RC Buildings in Vancouver

| Building Type | Typical Range | CoV Benchmark |
|---------------|--------------|---------------|
| Low-rise (1-6F) | 300–400 kgCO₂e/m² | 400 |
| Mid-rise (7-12F) | 380–480 kgCO₂e/m² | 400 |
| High-rise (13-20F) | 420–520 kgCO₂e/m² | 400 |
| Tall (20F+) | 480–600 kgCO₂e/m² | 400 |

Note: Ranges based on RC core structural system, typical Vancouver construction.
Higher buildings struggle to meet the 400 benchmark without SCM concrete or hybrid timber.
