// api/hops.js — Grasshopper Hops 接口（阶段二）
// 目前返回 mock 数据，阶段二替换为真实 Hops 调用

const HOPS_URL = 'http://localhost:8081';

/**
 * 从 Grasshopper 获取真实分析数据
 * 阶段一：返回基于参数的模拟数据
 * 阶段二：调用真实 Hops API
 */
export async function analyzeFromGrasshopper(params) {
  // 阶段二：取消注释以下代码
  /*
  try {
    const res = await fetch(`${HOPS_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params)
    });
    if (res.ok) return await res.json();
  } catch (e) {
    console.warn('Hops not connected, using estimated data');
  }
  */

  // 阶段一：基于参数的简化估算
  return estimateFromParams(params);
}

/**
 * 检查 Hops 是否在线
 */
export async function checkHopsConnection() {
  try {
    const res = await fetch(`${HOPS_URL}/ping`, { method: 'GET', signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * 阶段一：基于参数的简化规则估算
 * 阶段二：这些数据将由真实 Karamba + Ladybug 提供
 */
// Window type environmental multipliers
// Horizontal openings (ribbon) capture more diffuse sky light and low-angle solar.
// Vertical openings (curtain wall) maximise view and daylight depth but drive up solar gain.
// Punched windows limit solar gain most effectively.
// Vertical strips reduce sky exposure compared to ribbon.
const WINDOW_TYPE_FACTORS = {
  0: { label: 'Ribbon',       solarMult: 1.00, euiMult: 1.00, overheatingBias:  0 }, // baseline
  1: { label: 'Curtain Wall', solarMult: 1.30, euiMult: 1.25, overheatingBias:  2 }, // high gain
  2: { label: 'Punched',      solarMult: 0.75, euiMult: 0.85, overheatingBias: -1 }, // best control
  3: { label: 'Vertical',     solarMult: 0.90, euiMult: 0.92, overheatingBias: -0.5 }, // moderate
};

function estimateFromParams(params) {
  const { floors, floorplate, height, structuralSpan, wwRatio, orientation, windowType = 0 } = params;
  const totalArea = floors * floorplate;
  const slenderness = height / Math.sqrt(floorplate);
  const wtf = WINDOW_TYPE_FACTORS[windowType] || WINDOW_TYPE_FACTORS[0];

  // Overheating: base from wwRatio, adjusted by window type
  const overheatScore = (wwRatio > 0.6 ? 2 : wwRatio > 0.4 ? 1 : 0) + wtf.overheatingBias;
  const overheatingRisk = overheatScore >= 2 ? 'HIGH' : overheatScore >= 1 ? 'MODERATE' : 'LOW';

  return {
    source: 'estimated', // 阶段二改为 'grasshopper'

    // Karamba 结构数据（阶段二由真实分析提供）
    structural: {
      utilization: Math.min(0.95, (structuralSpan / 12) * 0.6 + slenderness * 0.05),
      maxDeflection: structuralSpan * structuralSpan / 400,
      lateralDrift: slenderness > 5 ? 'HIGH' : slenderness > 3 ? 'MODERATE' : 'LOW',
      recommendsCoreWall: floors > 8 || slenderness > 4,
    },

    // Ladybug 日照/能耗数据（阶段二由真实分析提供）
    environmental: {
      annualSolarHours: estimateSolarHours(orientation, wwRatio, wtf.solarMult),
      estimatedEUI: estimateEUI(params, wtf.euiMult),
      overheatingRisk,
      windowTypeLabel: wtf.label,
    },

    // Embodied carbon (RC core baseline)
    carbon: estimateEmbodiedCarbon(params),

    // 几何汇总
    geometry: {
      totalGFA: totalArea,
      totalHeight: height,
      slenderness: slenderness.toFixed(2),
      floorCount: floors,
    }
  };
}

function estimateSolarHours(orientation, wwRatio, solarMult) {
  // 粗估 Vancouver 年均日照小时数
  const base = 1900;
  const orientationFactor = Math.cos((orientation * Math.PI) / 180) * 0.15;
  return Math.round(base * (1 + orientationFactor) * (0.7 + wwRatio * 0.3) * solarMult);
}

/**
 * Rough embodied carbon estimator — RC core only.
 * CoV benchmark: 400 kgCO₂e/m² (VBBL Section 10.4, Oct 2023).
 * Adjusted by height, WWR, span, and plan efficiency.
 * See data/embodied-carbon-reference.md for sources.
 */
const COV_BENCHMARK = 400; // kgCO2e/m² — City of Vancouver absolute benchmark

function estimateEmbodiedCarbon(params) {
  const { floors, floorplate, structuralSpan, wwRatio,
          courtyard_ratio = 0, void_ratio = 0 } = params;
  const totalGFA = floors * floorplate;

  // RC core baseline kgCO2e/m² (mid-rise Vancouver)
  let intensity = 420;

  // Height penalty: taller = thicker core + deeper foundations
  if (floors > 20) intensity += 60;
  else if (floors > 12) intensity += 30;
  else if (floors > 6) intensity += 10;

  // WWR: glazing ~2x more carbon than opaque wall per m²
  intensity += (wwRatio - 0.4) * 120;

  // Span: longer span = more concrete in slabs
  intensity += (structuralSpan - 8) * 8;

  // Plan inefficiency: courtyard/void = more envelope per GFA
  intensity += (courtyard_ratio + void_ratio) * 40;

  intensity = Math.round(Math.max(300, Math.min(650, intensity)));
  const totalTonnes = Math.round((intensity * totalGFA) / 1000);
  const covBenchmarkTotal = Math.round((COV_BENCHMARK * totalGFA) / 1000);
  const delta = intensity - COV_BENCHMARK;
  const status = delta <= 0 ? 'COMPLIANT' : delta <= 50 ? 'AT RISK' : 'OVER';

  return {
    intensity,           // kgCO2e/m²
    totalTonnes,         // total tCO2e
    benchmark: COV_BENCHMARK,
    benchmarkTotal: covBenchmarkTotal,
    delta,               // kgCO2e/m² over/under benchmark
    status,              // COMPLIANT | AT RISK | OVER
    system: 'RC Core',
  };
}

function estimateEUI(params, euiMult) {
  const { buildingUse, wwRatio } = params;
  const baseEUI = buildingUse === 'office' ? 180 : buildingUse === 'residential' ? 120 : 150;
  return Math.round(baseEUI * (1 + (wwRatio - 0.4) * 0.5) * euiMult);
}
