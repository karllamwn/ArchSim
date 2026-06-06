/**
 * BCBC Part 2 — Trigger Keyword System
 * Division A, Part 2 Objectives (Sections 2.1, 2.2, Notes)
 *
 * Usage:
 *   const result = detectPart2Triggers(userMessage);
 *   if (result.length > 0) {
 *     // Auto-load: result[0].mdPath
 *   }
 *
 * Data source: BCBC 2024, Division A, Part 2
 */

export const BCBC_PART2_TRIGGERS = [
  {
    section: "2.1",
    title: "Application of Part 2",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 2 Objectives/2.1. Application/2.1. Application.md",
    loadQuestion: "Are you asking about which BCBC objectives apply to your building type? I can load Part 2 Application (Section 2.1) for reference.",
    triggers: [
      "which objectives apply",
      "do objectives apply",
      "part 2 application",
      "os4 application",
      "os4 dwelling unit",
      "oh3 application",
      "oh3 dwelling unit",
      "oh5 application",
      "oa application",
      "accessibility objective apply",
      "oe application",
      "energy objective application",
      "group f division 1 objectives",
      "objectives for my building",
      "which objectives",
      "objective apply to",
      "2.1 application",
      "objectives not apply",
      "unwanted entry objective",
      "noise protection objective",
      "environment objective",
    ]
  },
  {
    section: "2.2",
    title: "Objectives",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 2 Objectives/2.2. Objectives/2.2. Objectives.md",
    loadQuestion: "Are you asking about the BCBC objectives (OS, OH, OA, OP, OE)? I can load Section 2.2 Objectives for reference.",
    triggers: [
      "os1 fire safety objective",
      "os2 structural safety objective",
      "os3 safety in use objective",
      "os4 unwanted entry objective",
      "os5 construction site safety",
      "oh1 indoor conditions objective",
      "oh2 sanitation objective",
      "oh3 noise protection objective",
      "oh4 vibration objective",
      "oh5 hazardous substances objective",
      "oa accessibility objective",
      "oa1 barrier-free objective",
      "op1 fire protection objective",
      "op2 structural protection objective",
      "op3 moisture protection objective",
      "op4 adjacent building protection",
      "oe1 energy efficiency objective",
      "oe2 greenhouse gas objective",
      "list of objectives",
      "bcbc objectives",
      "os objective",
      "oh objective",
      "oa objective",
      "op objective",
      "oe objective",
      "fire safety objective",
      "structural objective",
      "health objective",
      "energy objective",
      "2.2 objectives",
    ]
  },
  {
    section: "Notes to Part 2",
    title: "Notes to Part 2 — Objectives",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 2 Objectives/Notes to Part 2/Notes to Part 2.md",
    loadQuestion: "Are you asking about an explanatory note from BCBC Part 2 Objectives? I can load the Notes to Part 2 for reference.",
    triggers: [
      "notes to part 2",
      "a-2.1.1.2",
      "a-2.2.1.1",
      "objective numbering gaps",
      "oe note",
      "section 9.36 note",
      "emergency definition note",
      "person in os1 note",
      "building definition note objectives",
      "objective gap numbering",
      "os1 person includes firefighter",
      "note a-2",
      "figure a-2",
    ]
  }
];

/**
 * Detects which BCBC Part 2 section(s) may be relevant to a user message.
 *
 * @param {string} userMessage - The raw user input text
 * @returns {Array} - Array of matching section objects (may be empty)
 */
export function detectPart2Triggers(userMessage) {
  const msg = userMessage.toLowerCase();
  const matches = [];

  for (const section of BCBC_PART2_TRIGGERS) {
    const matched = section.triggers.some(trigger => msg.includes(trigger));
    if (matched) {
      matches.push(section);
    }
  }

  return matches;
}
