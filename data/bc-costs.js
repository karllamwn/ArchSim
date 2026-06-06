// data/bc-costs.js — BC 地区建筑造价参考单价
// 来源：Altus Group / Hanscomb 2024 BC Cost Guide（简化版）
// 单位：CAD per sq ft (建筑面积)

export const BCCosts = {

  // 建筑类型单价范围
  constructionCost: {
    office: {
      low: 350, mid: 425, high: 550,
      description: 'Class B/C Office — Vancouver Metro',
      unit: 'CAD/sqft GFA'
    },
    residential: {
      low: 280, mid: 350, high: 480,
      description: 'Multi-family Residential — Vancouver Metro',
      unit: 'CAD/sqft GFA'
    },
    mixed: {
      low: 320, mid: 400, high: 520,
      description: 'Mixed-Use — Vancouver Metro',
      unit: 'CAD/sqft GFA'
    },
  },

  // 软成本系数（占硬成本百分比）
  softCosts: {
    design: 0.08,        // 设计费
    permits: 0.02,       // 许可证
    contingency: 0.10,   // 预备金
    total: 0.20,         // 合计软成本
  },

  // 高度附加系数（超高层施工成本增加）
  heightPremium(floors) {
    if (floors <= 6) return 0;
    if (floors <= 12) return 0.05;
    if (floors <= 20) return 0.12;
    return 0.20;
  },

  // 地下停车（如有）
  parking: {
    aboveGrade: 25000,   // CAD/stall
    belowGrade: 65000,   // CAD/stall
  },

  // m² 转 sqft
  m2ToSqft: 10.7639,

  /**
   * 估算总造价
   * @param {Object} params - 设计参数
   * @returns {Object} - 造价明细
   */
  estimate(params) {
    const { floors, floorplate, buildingUse } = params;
    const totalGFA_m2 = floors * floorplate;
    const totalGFA_sqft = totalGFA_m2 * this.m2ToSqft;

    const costs = this.constructionCost[buildingUse] || this.constructionCost.office;
    const heightAdj = this.heightPremium(floors);

    const hardCostLow = totalGFA_sqft * costs.low * (1 + heightAdj);
    const hardCostMid = totalGFA_sqft * costs.mid * (1 + heightAdj);
    const hardCostHigh = totalGFA_sqft * costs.high * (1 + heightAdj);

    const totalLow = hardCostLow * (1 + this.softCosts.total);
    const totalMid = hardCostMid * (1 + this.softCosts.total);
    const totalHigh = hardCostHigh * (1 + this.softCosts.total);

    return {
      gfa_m2: totalGFA_m2,
      gfa_sqft: Math.round(totalGFA_sqft),
      unitRate: costs,
      heightPremium: `${(heightAdj * 100).toFixed(0)}%`,
      hardCost: {
        low: formatCAD(hardCostLow),
        mid: formatCAD(hardCostMid),
        high: formatCAD(hardCostHigh),
      },
      totalProjectCost: {
        low: formatCAD(totalLow),
        mid: formatCAD(totalMid),
        high: formatCAD(totalHigh),
      },
      costPerM2: {
        low: `$${Math.round(hardCostLow / totalGFA_m2)} CAD/m²`,
        mid: `$${Math.round(hardCostMid / totalGFA_m2)} CAD/m²`,
      },
      note: 'Budgetary estimate only. Based on Altus/Hanscomb 2024 BC Cost Guide. Excludes land, financing, GST.',
    };
  }
};

function formatCAD(amount) {
  if (amount >= 1e6) return `$${(amount / 1e6).toFixed(1)}M CAD`;
  return `$${Math.round(amount / 1000)}K CAD`;
}
