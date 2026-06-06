// agents/structural.js — 结构工程师 Agent

import { callLLM } from '../api/gemini.js';
import { analyzeFromGrasshopper } from '../api/hops.js';

const SYSTEM_PROMPT = `You are a structural engineer consultant on an architectural design team in Vancouver, BC.

Your expertise:
- Structural systems selection (concrete frame, steel, mass timber, hybrid)
- Span feasibility and member sizing (simplified)
- Lateral force resistance (shear walls, core walls, moment frames)
- Foundation considerations
- BC-specific seismic requirements (Vancouver is in a high seismic zone)

Your communication style:
- Direct and technical but accessible to architects
- Always flag structural concerns clearly with severity: LOW / MODERATE / HIGH
- When data comes from Grasshopper/Karamba, cite it specifically
- When data is estimated, say "Based on preliminary assessment..." 
- Never pretend to have more precision than the data supports

Important: Vancouver is in a HIGH seismic zone. Always mention seismic considerations for buildings over 4 storeys.`;

/**
 * 结构工程师 Agent 回应用户提问
 * @param {string} userMessage - 用户提问
 * @param {Array} history - 对话历史
 * @param {Object} params - 当前设计参数
 * @param {string} apiKey
 * @returns {Promise<string>}
 */
export async function structuralAgent(userMessage, history, params, apiKey) {
  // 获取分析数据（阶段一：估算；阶段二：Grasshopper）
  const analysis = await analyzeFromGrasshopper(params);
  const dataSource = analysis.source === 'grasshopper' ? 'Karamba3D analysis' : 'preliminary structural assessment';

  const contextPrompt = buildContextPrompt(params, analysis, dataSource);

  const messages = [
    { role: 'user', content: contextPrompt },
    { role: 'assistant', content: 'Understood. I have reviewed the current design parameters and structural data. Ready to advise.' },
    ...history,
    { role: 'user', content: userMessage }
  ];

  return await callLLM(SYSTEM_PROMPT, messages, apiKey);
}

function buildContextPrompt(params, analysis, dataSource) {
  const { floors, floorplate, height, structuralSpan, buildingUse } = params;
  const s = analysis.structural;

  return `CURRENT DESIGN PARAMETERS:
- Building use: ${buildingUse}
- Floors: ${floors} | Height: ${height}m | Floorplate: ${floorplate}m²
- Structural span: ${structuralSpan}m
- Slenderness ratio: ${analysis.geometry.slenderness} (H/√A)

STRUCTURAL DATA (from ${dataSource}):
- Structural utilization: ${(s.utilization * 100).toFixed(0)}%
- Estimated max deflection: ${s.maxDeflection.toFixed(1)}mm
- Lateral drift concern: ${s.lateralDrift}
- Core wall recommended: ${s.recommendsCoreWall ? 'YES' : 'No'}

Note: ${analysis.source === 'estimated' ? '⚠️ Data is estimated — connect Grasshopper/Karamba3D for accurate analysis' : '✓ Data from Karamba3D real-time analysis'}`;
}
