// agents/orchestrator.js — Orchestrator / Planner Agent

import { callLLMforJSON, callLLM } from '../api/gemini.js';

const SYSTEM_PROMPT = `You are the Orchestrator — the project manager and strategic planner for an architectural design team.

Your role:
1. Parse the client brief written by the architect
2. Extract key design constraints, goals, and requirements
3. Recommend which specialist agents the architect should consult and in what order
4. Set initial design parameters based on the brief
5. Track design progress and provide final synthesis

You represent the project management layer — you don't design, but you make sure the right questions get asked in the right order.

Always respond in the same language the architect uses. Be concise and professional.`;

/**
 * 解析 Client Brief，生成规划报告
 * @param {string} briefText - 用户输入的自然语言 Brief
 * @param {string} apiKey
 * @returns {Promise<Object>} - 结构化规划数据
 */
export async function parseBrief(briefText, apiKey) {
  const prompt = `Parse this architectural client brief and extract structured information.

CLIENT BRIEF:
"${briefText}"

Return a JSON object with this exact structure:
{
  "summary": "2-3 sentence summary of the project",
  "projectType": "office | residential | mixed | other",
  "keyRequirements": ["requirement 1", "requirement 2"],
  "designConstraints": ["constraint 1", "constraint 2"],
  "suggestedAgents": [
    { "agent": "structural", "reason": "why this agent is needed", "priority": 1 },
    { "agent": "cost", "reason": "why this agent is needed", "priority": 2 },
    { "agent": "code", "reason": "why this agent is needed", "priority": 3 },
    { "agent": "mep", "reason": "why this agent is needed", "priority": 4 }
  ],
  "initialParams": {
    "floors": 10,
    "floorplate": 800,
    "height": 36,
    "structuralSpan": 9,
    "wwRatio": 0.4,
    "orientation": 0,
    "buildingUse": "office"
  },
  "openingStatement": "A natural language statement (2-3 sentences) that the Orchestrator says to the architect to kick off the session"
}

Base the initialParams on reasonable assumptions from the brief. If the brief mentions specific numbers, use them.`;

  const result = await callLLMforJSON(SYSTEM_PROMPT, prompt, apiKey);
  return result;
}

/**
 * 生成最终综合评审报告
 * @param {Object} state - 完整的 AppState
 * @param {string} apiKey
 * @returns {Promise<string>} - 自然语言评审报告
 */
export async function generateFinalReview(state, apiKey) {
  const prompt = `Generate a final design review synthesis based on this design session.

BRIEF SUMMARY: ${state.brief.summary}

FINAL DESIGN PARAMETERS:
${JSON.stringify(state.params, null, 2)}

CONSULTATION HISTORY (${state.conversations.length} exchanges):
${state.conversations.slice(-10).map(c => `[${c.agent.toUpperCase()}] ${c.role}: ${c.content.slice(0, 200)}`).join('\n')}

Write a professional 3-4 paragraph synthesis covering:
1. How the design evolved from the brief
2. Key structural and performance considerations
3. Cost and code compliance status
4. Recommended next steps

Be specific and reference actual parameter values where relevant.`;

  return await callLLM(SYSTEM_PROMPT, [{ role: 'user', content: prompt }], apiKey);
}
