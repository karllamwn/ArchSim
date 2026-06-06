// data/bcbc-zoning.js — City of Vancouver Zoning and Development By-law
// ────────────────────────────────────────────────────────────────────────
// HOW TO FILL THIS FILE:
//   Source: City of Vancouver Zoning and Development By-law (CoV website)
//   This is NOT part of BCBC — it is a separate municipal by-law.
//   URL: https://vancouver.ca/home-property-development/zoning-and-development-bylaw.aspx
//
// SECTIONS TO INCLUDE (vary by zoning district — fill in for your project's zone):
//   Section 2    — Definitions (FSR, Site Coverage, Height)
//   Section 4    — Outright Approval Uses (permitted uses without rezoning)
//   Section 4.x  — Conditional Approval Uses
//   Section 5    — Regulations (FSR limits, height limits, setbacks, site coverage)
//   Section 6    — Heritage (if applicable — heritage overlay requirements)
//
// KEY METRICS TO INCLUDE for your typical zone (e.g. CD-1, DD, C-6, RM-X):
//   - Maximum FSR (Floor Space Ratio) — e.g. 5.0 for downtown
//   - Maximum building height (m or storeys)
//   - Required setbacks (front, rear, side)
//   - Maximum site coverage (%)
//   - Parking requirements (stalls per 100m² GFA by use)
//   - Bicycle parking requirements
//   - Loading bay requirements
//   - Amenity space requirements (if any)
//
// NOTE: Zoning varies heavily by site — this file should be updated per project.
// For a generic starting point, include DD (Downtown District) or CD-1 regulations.
//
// TOKEN BUDGET: ~800–1500 words.
// ────────────────────────────────────────────────────────────────────────

export const BCBC_CONTENT = `
[PASTE ZONING CONTENT HERE]

Instructions: Paste the relevant zoning regulations for your project's district.

For a typical Downtown Vancouver mixed-use project, include:
- DD (Downtown District) or the specific CD-1 by-law for your site
- FSR limits (typically 5.0–9.0 in downtown zones)
- Height limits (check for view cone restrictions)
- Setback requirements
- Parking requirements table (by use type)
- Any Green Buildings Policy for Rezonings requirements

Also include any heritage overlay rules if the project has a heritage context.

Note: Always verify against the current CoV Zoning Map and specific site address.
`;
