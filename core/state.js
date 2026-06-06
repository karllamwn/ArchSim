// core/state.js — 全局状态管理

export const AppState = {
  apiKey: '',
  activeAgent: null,
  briefData: null,

  params: {
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
  },

  agentHistories: {
    structural: [],
    mep: [],
    cost: [],
    code: [],
    orchestrator: [],
  },

  // 全局对话流水（用于最终综合报告）
  conversations: [],

  // ── 方法 ──────────────────────────────────────────────

  setApiKey(key) {
    this.apiKey = key;
  },

  setActiveAgent(agent) {
    this.activeAgent = agent;
  },

  setBriefData(data) {
    this.briefData = data;
  },

  updateParam(key, value) {
    this.params[key] = value;
  },

  getParams() {
    return { ...this.params };
  },

  reset() {
    this.activeAgent = null;
    this.briefData = null;
    this.agentHistories = { structural: [], mep: [], cost: [], code: [], orchestrator: [] };
    this.conversations = [];
  },
};
