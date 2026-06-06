// data/bcbc-rules.js — BCBC 关键规则库（简化版）
// 来源：BC Building Code 2024，仅包含最常用规则
// 阶段三：替换为完整 RAG 知识库

export const BCBC = {

  // 建筑分类
  occupancy: {
    office: { class: 'D', description: 'Business and Personal Services' },
    residential: { class: 'C', description: 'Residential Occupancy' },
    retail: { class: 'E', description: 'Mercantile Occupancy' },
    mixed: { class: 'mixed', description: 'Mixed Occupancy — requires separation' },
  },

  // Part 3 vs Part 9 判定
  getApplicablePart(floors, totalArea) {
    if (floors > 3 || totalArea > 600) return 3;
    return 9;
  },

  // 防火分区面积限制 (m²)
  fireCompartment: {
    D: { sprinklered: 'unlimited', nonSprinklered: 3600 },
    C: { sprinklered: 'unlimited', nonSprinklered: 1500 },
    E: { sprinklered: 'unlimited', nonSprinklered: 2400 },
  },

  // 出口要求
  exits: {
    getMinExits(floors, occupantLoad) {
      if (occupantLoad > 60) return 2;
      if (floors > 1) return 2;
      return 1;
    },
    maxTravelDistance: { sprinklered: 45, nonSprinklered: 25 }, // metres
  },

  // 无障碍要求
  accessibility: {
    requiredFor: ['office', 'retail', 'mixed'],
    elevatorRequired: (floors) => floors > 3,
  },

  // 节能要求（BCBC Part 10 / ASHRAE 90.1）
  energy: {
    maxWWR: 0.60, // 最大窗墙比
    minWWR: 0.10,
    insulationZone: 'Zone 5', // Vancouver
  },

  // 高度限制（需查分区，这里用通用规则）
  height: {
    woodFrameMax: 6, // 楼层（Part 3 木结构）
    concreteUnlimited: true,
  },

  /**
   * 对当前设计参数做合规检查
   * @param {Object} params - 设计参数
   * @returns {Array} - 合规问题列表
   */
  check(params) {
    const issues = [];
    const { floors, floorplate, wwRatio, buildingUse } = params;
    const totalArea = floors * floorplate;
    const part = this.getApplicablePart(floors, totalArea);

    if (part === 3) {
      issues.push({ level: 'info', rule: 'Part 3', message: `Building requires Part 3 compliance (${floors} storeys, ${totalArea}m² GFA)` });
    }

    if (wwRatio > this.energy.maxWWR) {
      issues.push({ level: 'warning', rule: 'BCBC 10.2', message: `Window-to-wall ratio ${(wwRatio * 100).toFixed(0)}% exceeds maximum 60%` });
    }

    if (floors > 3 && !this.accessibility.elevatorRequired(floors)) {
      issues.push({ level: 'info', rule: 'BCBC 3.8', message: 'Accessible elevator required for buildings over 3 storeys' });
    }

    const occ = this.occupancy[buildingUse];
    if (occ) {
      issues.push({ level: 'info', rule: 'Occupancy', message: `Classified as Group ${occ.class} — ${occ.description}` });
    }

    return issues;
  }
};
