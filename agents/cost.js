// agents/cost.js — 造价顾问 Agent

import { callLLM } from '../api/gemini.js';
import { BCCosts } from '../data/bc-costs.js';

const SYSTEM_PROMPT = `You are a cost consultant (Quantity Surveyor) on an architectural design team in Vancouver, BC.

Your expertise:
- Building construction cost estimating for BC projects
- Cost implications of design decisions
- Value engineering suggestions
- Development pro-forma basics
- Understanding of BC construction market (labour, materials)

Your communication style:
- Always provide cost ranges (low/mid/high), never a single number
- Clearly state assumptions and exclusions
- Translate design changes into dollar impacts ("increasing span from 9m to 12m adds approximately...")
- Be direct about cost risks
- Reference current BC market conditions (2024)

Important: Always clarify your estimates are Class D / budgetary only. Recommend quantity surveyor engagement for Class B estimates before design development.`;

export async function costAgent(userMessage, history, params, apiKey) {
  const estimate = BCCosts.estimate(params);
  const contextPrompt = buildContextPrompt(params, estimate);

  const messages = [
    { role: 'user', content: contextPrompt },
    { role: 'assistant', content: 'Understood. I have reviewed the cost estimate for the current design. Ready to advise on cost implications.' },
    ...history,
    { role: 'user', content: userMessage }
  ];

  return await callLLM(SYSTEM_PROMPT, messages, apiKey);
}

function buildContextPrompt(params, estimate) {
  const { floors, floorplate, buildingUse, structuralSpan } = params;

  return `CURRENT DESIGN PARAMETERS:
- Building use: ${buildingUse}
- Floors: ${floors} | Floorplate: ${floorplate}m²
- GFA: ${estimate.gfa_m2.toLocaleString()}m² (${estimate.gfa_sqft.toLocaleString()} sqft)
- Structural span: ${structuralSpan}m
- Height premium: ${estimate.heightPremium}

COST ESTIMATE (Class D Budgetary — BC Market 2024):
- Unit rate range: $${estimate.unitRate.low}–$${estimate.unitRate.high} CAD/sqft
- Hard cost: ${estimate.hardCost.low} – ${estimate.hardCost.high}
- Total project cost (incl. soft costs): ${estimate.totalProjectCost.low} – ${estimate.totalProjectCost.high}
- Cost per m²: ${estimate.costPerM2.low} – ${estimate.costPerM2.mid}

EXCLUSIONS: ${estimate.note}`;
}
