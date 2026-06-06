/**
 * BCBC Part 1 — Trigger Keyword System
 * Division A, Part 1 Compliance (Sections 1.1 – 1.5 + Notes)
 *
 * Usage:
 *   const result = detectPart1Triggers(userMessage);
 *   if (result) {
 *     // Ask user: result.loadQuestion
 *     // If confirmed, fetch: result.mdPath
 *   }
 *
 * Data source: BCBC 2024, Division A, Part 1
 */

export const BCBC_PART1_TRIGGERS = [
  {
    section: "1.1",
    title: "Section 1.1. General — Application of this Code",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/1.1 General/1.1 General.md",
    loadQuestion: "Are you asking about what the BCBC applies to, or about heritage/secondary suite alternate compliance methods? I can load BCBC 1.1 for reference.",
    triggers: [
      "does the code apply",
      "code applies to",
      "new building",
      "change in occupancy",
      "alteration to building",
      "alteration of building",
      "heritage building code",
      "heritage alternate compliance",
      "secondary suite alteration",
      "existing building",
      "farm building",
      "temporary building",
      "accessory building",
      "10 m2",
      "factory-constructed",
      "relocated building",
      "book i",
      "book ii",
      "plumbing systems code",
      "notes have no legal effect",
      "reconstruction after fire",
      "demolition",
      "safety during construction",
      "table 1.1.1.1",
      "heritage table",
      "secondary suite compliance methods",
    ]
  },
  {
    section: "1.2",
    title: "Section 1.2. Compliance",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/1.2 Compliance/Section 1.2. Compliance.md",
    loadQuestion: "Are you asking about BCBC compliance methods (acceptable vs alternative solutions) or owner/plumber responsibilities? I can load BCBC 1.2 for reference.",
    triggers: [
      "alternative solution",
      "acceptable solution",
      "performance-based",
      "comply with code",
      "code compliance method",
      "owner responsible",
      "owner responsibility",
      "used materials",
      "reuse material",
      "recycled material",
      "plumbing qualification",
      "plumber certification",
      "tradesperson",
      "who is responsible",
      "building permit responsibility",
      "ahj acceptance",
      "alternative design",
      "performance level",
    ]
  },
  {
    section: "1.3",
    title: "Section 1.3. Divisions A, B and C — Which Part Applies",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/1.3 Divisions A, B and C of this Code/Section 1.3. Divisions A, B and C of this Code.md",
    loadQuestion: "Are you asking which Division or Part of the BCBC applies to your building? I can load BCBC 1.3 for reference.",
    triggers: [
      "which part applies",
      "part 3 or part 9",
      "part 9 applies",
      "does part 3 apply",
      "600 m2",
      "600m2",
      "3 storeys",
      "3-storey",
      "three storey",
      "building area limit",
      "which division",
      "scope of division",
      "assembly occupancy part",
      "post-disaster which part",
      "firewall divide building",
      "separate building firewall",
      "sloping site height",
      "building height determination",
      "division a scope",
      "division b scope",
      "division c scope",
      "part 3 building",
      "part 9 building",
      "group a part",
      "group b part",
      "group c part",
      "group d part",
      "group e part",
      "group f part",
    ]
  },
  {
    section: "1.4",
    title: "Section 1.4. Terms and Abbreviations",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/1.4 Terms and Abbreviations/Section 1.4. Terms and Abbreviations.md",
    loadQuestion: "Are you asking about the definition of a specific BCBC term? I can load BCBC 1.4 (Terms and Abbreviations) for reference.",
    triggers: [
      "definition of",
      "what is a storey",
      "what is a suite",
      "what is floor area",
      "what is building area",
      "what is building height",
      "what is grade",
      "what is a basement",
      "what is a mezzanine",
      "what is an exit",
      "what is an occupancy",
      "what is a firewall",
      "what is a fire separation",
      "what is fire-resistance rating",
      "what is frr",
      "major occupancy",
      "ahj definition",
      "authority having jurisdiction",
      "registered professional",
      "post-disaster building",
      "means of egress",
      "access to exit",
      "limiting distance",
      "sprinklered definition",
      "noncombustible definition",
      "combustible definition",
      "encapsulated mass timber",
      "first storey definition",
      "what does astc mean",
      "what does stc mean",
      "what is a guard",
      "what is a ramp",
      "what is a flight",
      "dwelling unit definition",
      "secondary suite definition",
      "fire compartment",
      "occupancy group",
      "group a definition",
      "group b definition",
      "group c definition",
      "group d definition",
      "group e definition",
      "group f definition",
      "assembly occupancy definition",
      "residential occupancy definition",
      "care occupancy definition",
      "detention occupancy definition",
      "treatment occupancy definition",
      "mercantile occupancy definition",
      "industrial occupancy definition",
    ]
  },
  {
    section: "1.5",
    title: "Section 1.5. Referenced Documents and Organizations",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/1.5 Referenced Documents and Organizations/Section 1.5. Referenced Documents and.md",
    loadQuestion: "Are you asking about how referenced standards (CSA, ULC, NFPA, etc.) apply within the BCBC? I can load BCBC 1.5 for reference.",
    triggers: [
      "referenced standard",
      "which edition applies",
      "standard edition",
      "applicable edition",
      "conflict between code and standard",
      "standard conflicts with code",
      "csa applies",
      "ulc applies",
      "nfpa applies",
      "referenced document",
      "can/ulc",
      "organization abbreviation",
      "astm applies",
      "csa standard",
      "ulc standard",
      "nfpa standard",
    ]
  },
  {
    section: "Notes to Part 1",
    title: "Notes to Part 1 — Compliance",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 1 Compliance/Notes to Part 1/Notes to Part 1.md",
    loadQuestion: "Are you asking about an explanatory note or figure from BCBC Part 1? I can load the Notes to Part 1 for reference.",
    triggers: [
      "factory-constructed building note",
      "heritage building note",
      "secondary suite note",
      "existing building note",
      "alternative solution note",
      "sloping site",
      "stepped building",
      "building on slope",
      "post-disaster note",
      "care occupancy note",
      "fire separation note",
      "dangerous goods classification",
      "astc stc note",
      "secondary suite permitted",
      "suite definition note",
      "vapour barrier vs air barrier",
      "referenced documents note",
      "owner responsibility note",
      "firewall note",
      "figure a-1",
      "note a-1",
      "a-1.1",
      "a-1.2",
      "a-1.3",
      "a-1.4",
      "a-1.5",
    ]
  }
];

/**
 * Detects which BCBC Part 1 section(s) may be relevant to a user message.
 *
 * @param {string} userMessage - The raw user input text
 * @returns {Array} - Array of matching section objects (may be empty)
 */
export function detectPart1Triggers(userMessage) {
  const msg = userMessage.toLowerCase();
  const matches = [];

  for (const section of BCBC_PART1_TRIGGERS) {
    const matched = section.triggers.some(trigger => msg.includes(trigger));
    if (matched) {
      matches.push(section);
    }
  }

  return matches;
}

/**
 * Build a system prompt injection with content loaded from a matched section.
 * Call this after user confirms they want the section loaded.
 *
 * @param {string} mdContent - The raw markdown content of the section
 * @param {string} sectionTitle - Title of the section (for context)
 * @returns {string} - A formatted string to prepend to the LLM system prompt
 */
export function buildBcbcContext(mdContent, sectionTitle) {
  return `
=== BCBC REFERENCE LOADED: ${sectionTitle} ===
The following is the authoritative BCBC content for this query.
Use this content accurately. Do not guess or paraphrase rules — quote the exact requirements.

${mdContent}
=== END BCBC REFERENCE ===
`.trim();
}
