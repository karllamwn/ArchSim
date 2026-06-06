// agents/code.js — 规范顾问 Agent (BCBC)

import { callLLM } from '../api/gemini.js';
import { BCBC } from '../data/bcbc-rules.js';

const SYSTEM_PROMPT = `You are a building code consultant specializing in the BC Building Code (BCBC 2024) on an architectural design team in Vancouver, BC.

Your expertise:
- BC Building Code 2024 compliance
- City of Vancouver Zoning and Development By-law
- Part 3 and Part 9 buildings
- Occupancy classifications and fire separations
- Means of egress and accessibility (BCBC Part 3.8)
- BC Energy Step Code
- Vancouver-specific requirements (Green Buildings Policy, etc.)

Your communication style:
- Always cite specific BCBC article numbers (e.g., "BCBC 3.2.2.20")
- Distinguish between BCBC requirements and City of Vancouver by-law requirements
- Flag non-compliance clearly as: ⚠️ NON-COMPLIANT or ✓ COMPLIANT
- Note when you're uncertain and recommend consulting the AHJ (Authority Having Jurisdiction)
- Be precise — building code is not a place for vague advice

Important: Always remind the architect that code compliance must be confirmed with the local AHJ. Your assessment is preliminary only.`;

export async function codeAgent(userMessage, history, params, apiKey) {
  const issues = BCBC.check(params);
  const contextPrompt = buildContextPrompt(params, issues);

  const messages = [
    { role: 'user', content: contextPrompt },
    { role: 'assistant', content: 'Understood. I have reviewed the BCBC compliance status for the current design parameters. Ready to advise.' },
    ...history,
    { role: 'user', content: userMessage }
  ];

  return await callLLM(SYSTEM_PROMPT, messages, apiKey);
}

function buildContextPrompt(params, issues) {
  const { floors, floorplate, wwRatio, buildingUse } = params;
  const totalArea = floors * floorplate;
  const applicablePart = BCBC.getApplicablePart(floors, totalArea);
  const occ = BCBC.occupancy[buildingUse];

  return `CURRENT DESIGN PARAMETERS:
- Building use: ${buildingUse} → Occupancy Group ${occ?.class || 'TBD'} (${occ?.description || ''})
- Floors: ${floors} | Total GFA: ${totalArea.toLocaleString()}m²
- Window-to-wall ratio: ${(wwRatio * 100).toFixed(0)}%
- Applicable Code: BCBC 2024 Part ${applicablePart}
- Location: Vancouver, BC

PRELIMINARY COMPLIANCE CHECKS:
${issues.map(i => `${i.level === 'warning' ? '⚠️' : 'ℹ️'} [${i.rule}] ${i.message}`).join('\n')}

REMINDER: This is a preliminary assessment only. All code compliance must be confirmed with the City of Vancouver Building Department (AHJ).`;
}
