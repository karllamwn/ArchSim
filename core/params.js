// core/params.js — 设计参数处理

export const DEFAULT_PARAMS = {
  floors: 10,
  floorplate: 800,
  height: 36,
  structuralSpan: 9,
  wwRatio: 0.4,
  orientation: 0,
  buildingUse: 'office',
  ghConnected: false,
  karamba: null,
  ladybug: null,
};

// 参数 key → UI input ID 映射
export const PARAM_INPUT_MAP = {
  floors:        'p_floors',
  floorplate:    'p_fp',
  height:        'p_h',
  structuralSpan:'p_span',
  wwRatio:       'p_wwr',
  orientation:   'p_ori',
  buildingUse:   'p_use',
};

/**
 * 将参数同步到 UI 输入控件
 * @param {Object} params
 */
export function syncParamsToUI(params) {
  for (const [key, id] of Object.entries(PARAM_INPUT_MAP)) {
    const el = document.getElementById(id);
    if (el && params[key] !== undefined) el.value = params[key];
  }
}

/**
 * 校验设计参数，返回错误信息列表
 * @param {Object} params
 * @returns {string[]}
 */
export function validateParams(params) {
  const errors = [];
  if (params.floors < 1 || params.floors > 100)
    errors.push('楼层数必须在 1–100 之间');
  if (params.floorplate < 50 || params.floorplate > 10000)
    errors.push('楼板面积必须在 50–10,000m² 之间');
  if (params.wwRatio < 0.05 || params.wwRatio > 0.95)
    errors.push('窗墙比必须在 0.05–0.95 之间');
  if (params.structuralSpan < 3 || params.structuralSpan > 30)
    errors.push('结构跨度必须在 3–30m 之间');
  return errors;
}

/**
 * 计算派生参数（不直接输入、由基础参数推算）
 * @param {Object} params
 * @returns {Object}
 */
export function getDerivedParams(params) {
  const totalGFA = params.floors * params.floorplate;
  return {
    totalGFA,
    gfa_sqft:    Math.round(totalGFA * 10.7639),
    slenderness: (params.height / Math.sqrt(params.floorplate)).toFixed(2),
    floorHeight: (params.height / params.floors).toFixed(2),
  };
}
