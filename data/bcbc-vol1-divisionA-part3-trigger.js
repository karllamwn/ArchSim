/**
 * BCBC Part 3 — Trigger Keyword System
 * Division A, Part 3 Functional Statements (Sections 3.1, 3.2, Notes)
 *
 * Usage:
 *   const result = detectPart3Triggers(userMessage);
 *   if (result.length > 0) {
 *     // Auto-load: result[0].mdPath
 *   }
 *
 * Data source: BCBC 2024, Division A, Part 3
 */

export const BCBC_PART3_TRIGGERS = [
  {
    section: "3.1",
    title: "Application of Part 3",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 3 Functional Statements/3.1. Application/3.1. Application.md",
    loadQuestion: "Are you asking about which functional statements apply to your building? I can load Part 3 Application (Section 3.1) for reference.",
    triggers: [
      "which functional statements apply",
      "do functional statements apply",
      "part 3 application",
      "f56 application",
      "f73 application",
      "f74 application",
      "functional statement apply to",
      "functional statement dwelling unit",
      "functional statement group f",
      "accessibility functional statement",
      "noise functional statement",
      "3.1 application",
      "functional statement limitation",
    ]
  },
  {
    section: "3.2",
    title: "Functional Statements",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 3 Functional Statements/3.2. Functional Statements/3.2. Functional Statements.md",
    loadQuestion: "Are you asking about BCBC functional statements (F-codes)? I can load Section 3.2 Functional Statements for reference.",
    triggers: [
      "f01",
      "f02",
      "f03",
      "f04",
      "f05",
      "f06",
      "f10",
      "f11",
      "f12",
      "f13",
      "f20",
      "f21",
      "f22",
      "f23",
      "f30",
      "f31",
      "f32",
      "f33",
      "f34",
      "f35",
      "f36",
      "f40",
      "f41",
      "f42",
      "f43",
      "f44",
      "f45",
      "f46",
      "f50",
      "f51",
      "f52",
      "f53",
      "f54",
      "f55",
      "f56",
      "f60",
      "f61",
      "f62",
      "f63",
      "f70",
      "f71",
      "f72",
      "f73",
      "f74",
      "f75",
      "f80",
      "f81",
      "f82",
      "f90",
      "f91",
      "f92",
      "f93",
      "f94",
      "f95",
      "f96",
      "f97",
      "f98",
      "f99",
      "f100",
      "f101",
      "functional statement fire",
      "functional statement egress",
      "functional statement structural",
      "functional statement safety in use",
      "functional statement indoor air",
      "functional statement indoor conditions",
      "functional statement moisture",
      "functional statement plumbing",
      "functional statement accessibility",
      "functional statement durability",
      "functional statement energy",
      "list of functional statements",
      "bcbc functional statements",
      "f-code",
      "f code list",
      "3.2 functional statements",
    ]
  },
  {
    section: "Notes to Part 3",
    title: "Notes to Part 3 — Functional Statements",
    mdPath: "reference/bcbc/Volume 1/Division A Compliance, Objectives and Functional Statements/Part 3 Functional Statements/Notes to Part 3/Notes to Part 3.md",
    loadQuestion: "Are you asking about an explanatory note from BCBC Part 3 Functional Statements? I can load the Notes to Part 3 for reference.",
    triggers: [
      "notes to part 3",
      "a-3.2.1.1",
      "functional statement numbering gaps",
      "f-code gaps",
      "why are there gaps in f numbers",
      "functional statement master list",
      "book i book ii f-code",
      "functional statement across codes",
      "f number gap",
      "note a-3",
    ]
  }
];

/**
 * Detects which BCBC Part 3 section(s) may be relevant to a user message.
 *
 * @param {string} userMessage - The raw user input text
 * @returns {Array} - Array of matching section objects (may be empty)
 */
export function detectPart3Triggers(userMessage) {
  const msg = userMessage.toLowerCase();
  const matches = [];

  for (const section of BCBC_PART3_TRIGGERS) {
    const matched = section.triggers.some(trigger => msg.includes(trigger));
    if (matched) {
      matches.push(section);
    }
  }

  return matches;
}
