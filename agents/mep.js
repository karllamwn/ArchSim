// agents/mep.js — MEP 顾问 Agent

import { callLLM } from '../api/gemini.js';
import { analyzeFromGrasshopper } from '../api/hops.js';

const SYSTEM_PROMPT = `You are an MEP (Mechanical, Electrical, Plumbing) and sustainability consultant on an architectural design team in Vancouver, BC.

Your expertise:
- Daylighting and solar analysis
- Building energy performance (EUI targets for BC)
- HVAC system selection and zoning
- BC Energy Step Code compliance
- Passive design strategies (orientation, shading, thermal mass)
- LEED / Passive House considerations

Your communication style:
- Translate technical energy data into design implications
- Always connect performance data back to design decisions the architect can make
- Flag overheating and daylighting risks clearly
- When Ladybug data is available, reference specific numbers
- When estimated, say "Based on simplified energy model..."

Important: BC Energy Step Code is mandatory in BC. New buildings must meet Step 3 minimum (Step 4-5 encouraged for LEED). Always reference applicable Step Code requirements.`;

export async function mepAgent(userMessage, history, params, apiKey) {
  const analysis = await analyzeFromGrasshopper(params);
  const dataSource = analysis.source === 'grasshopper' ? 'Ladybug Tools analysis' : 'simplified energy model';

  const contextPrompt = buildContextPrompt(params, analysis, dataSource);

  const messages = [
    { role: 'user', content: contextPrompt },
    { role: 'assistant', content: 'Understood. I have reviewed the environmental performance data. Ready to advise on MEP and sustainability.' },
    ...history,
    { role: 'user', content: userMessage }
  ];

  return await callLLM(SYSTEM_PROMPT, messages, apiKey);
}

const WINDOW_TYPE_IMPLICATIONS = {
  0: {
    name: 'Ribbon (horizontal glazing)',
    daylight: 'Good diffuse sky light; even distribution across depth of floor plate.',
    solar:    'Moderate direct solar gain. Low-angle winter sun penetrates well (south face). Summer high sun less of a concern.',
    hvac:     'Perimeter heating/cooling load is manageable. Standard VAV or FCU perimeter strategy works.',
    risk:     'Watch south and west facades in summer. External horizontal shading fins are highly effective.',
  },
  1: {
    name: 'Curtain Wall (floor-to-ceiling glazing)',
    daylight: 'Maximum daylight depth — excellent for open-plan offices. Glare risk without blinds.',
    solar:    'HIGH solar gain on east, south, and west exposures. Spandrel panels at slab edge add thermal bridging risk.',
    hvac:     'Perimeter cooling load is significantly elevated. Active chilled beam or fan coil units at perimeter are likely required. Heat pump loop recommended.',
    risk:     'Highest overheating risk of all types. External shading (fins, brise-soleil) or high-performance glazing (low SHGC) is essential for BC Energy Step Code compliance.',
  },
  2: {
    name: 'Punched windows',
    daylight: 'Moderate daylight — limited to zone near windows. Supplemental lighting may be required deeper in the plan.',
    solar:    'Best solar control of all types. Solid wall mass between windows buffers temperature swings.',
    hvac:     'Lowest perimeter cooling load. Simplified HVAC zoning — single zone per facade may be sufficient.',
    risk:     'Low overheating risk. Most compatible with passive strategies (thermal mass, natural ventilation).',
  },
  3: {
    name: 'Vertical strips',
    daylight: 'Narrow daylight columns — high contrast between bright strips and dark wall. Glare at strip edges.',
    solar:    'Lower sky exposure than ribbon; direct solar enters as concentrated shafts — high intensity but narrow width.',
    hvac:     'Moderate perimeter load. Localised solar gain at strip locations needs targeted supply air.',
    risk:     'Glare management at strip edges is key. External vertical fins between strips can be effective.',
  },
};

function buildContextPrompt(params, analysis, dataSource) {
  const { floors, floorplate, wwRatio, orientation, buildingUse, windowType = 0 } = params;
  const e   = analysis.environmental;
  const wti = WINDOW_TYPE_IMPLICATIONS[windowType] || WINDOW_TYPE_IMPLICATIONS[0];

  return `CURRENT DESIGN PARAMETERS:
- Building use: ${buildingUse}
- Floors: ${floors} | Floorplate: ${floorplate}m²
- Window-to-wall ratio: ${(wwRatio * 100).toFixed(0)}%
- Orientation: ${orientation}° (0=North)
- Window type: ${wti.name}

WINDOW TYPE ENVIRONMENTAL IMPLICATIONS:
- Daylighting: ${wti.daylight}
- Solar gain: ${wti.solar}
- HVAC strategy: ${wti.hvac}
- Key risk: ${wti.risk}

ENVIRONMENTAL DATA (from ${dataSource}):
- Estimated annual solar hours: ${e.annualSolarHours} hrs/year
- Estimated EUI: ${e.estimatedEUI} kWh/m²/year
- Overheating risk: ${e.overheatingRisk}

BC ENERGY STEP CODE CONTEXT:
- Location: Vancouver (Climate Zone 5)
- TEDI target (Step 3): ≤15 kWh/m²/year (heating)
- TEUI target (Step 3): ≤120 kWh/m²/year

Note: ${analysis.source === 'estimated' ? '⚠️ Data is estimated — connect Grasshopper/Ladybug for accurate solar/energy analysis' : '✓ Data from Ladybug Tools real-time analysis'}`;
}
