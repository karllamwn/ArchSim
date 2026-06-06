// core/history.js — 对话历史记录管理

export class ConversationHistory {
  constructor() {
    // 全局流水记录（所有 Agent 混合，按时间排序）
    this._history = [];
    // 按 Agent 分类（传递给 LLM 作为上下文）
    this._byAgent = {
      structural: [],
      mep: [],
      cost: [],
      code: [],
      orchestrator: [],
    };
  }

  /**
   * 添加一条对话记录
   * @param {string} agent - Agent 名称
   * @param {'user'|'agent'|'orchestrator'} role
   * @param {string} content
   * @returns {Object} 记录条目
   */
  add(agent, role, content) {
    const entry = {
      agent,
      role,
      content,
      timestamp: Date.now(),
    };
    this._history.push(entry);
    if (this._byAgent[agent]) {
      this._byAgent[agent].push({ role, content });
    }
    return entry;
  }

  /**
   * 获取特定 Agent 的对话历史（传入 LLM）
   * @param {string} agent
   * @returns {Array<{role, content}>}
   */
  getAgentHistory(agent) {
    return [...(this._byAgent[agent] || [])];
  }

  /**
   * 获取全部流水记录
   * @returns {Array}
   */
  getAll() {
    return [...this._history];
  }

  /**
   * 获取最近 N 条（用于综合报告摘要）
   * @param {number} n
   * @returns {Array}
   */
  getRecent(n = 10) {
    return this._history.slice(-n);
  }

  /**
   * 清空特定 Agent 的历史
   * @param {string} agent
   */
  clearAgent(agent) {
    if (this._byAgent[agent]) this._byAgent[agent] = [];
  }

  /**
   * 清空所有历史
   */
  clearAll() {
    this._history = [];
    Object.keys(this._byAgent).forEach(k => { this._byAgent[k] = []; });
  }

  /**
   * 返回对话总条数
   * @returns {number}
   */
  get length() {
    return this._history.length;
  }
}
