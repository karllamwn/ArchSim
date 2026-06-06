// api/gemini.js — Gemini API 封装（支持未来切换 Claude）

const GEMINI_MODEL = 'gemini-3-flash-preview';

/**
 * 调用 LLM（目前用 Gemini，接口预留切换）
 * @param {string} systemPrompt - Agent 的系统提示
 * @param {Array} messages - 对话历史 [{role, content}]
 * @param {string} apiKey
 * @returns {Promise<string>} - Agent 回应文字
 */
export async function callLLM(systemPrompt, messages, apiKey) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${apiKey}`;

  const contents = messages.map(m => ({
    role: m.role === 'user' ? 'user' : 'model',
    parts: [{ text: m.content }]
  }));

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemPrompt }] },
      contents,
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 4096,
        thinkingConfig: { thinkingBudget: 0 }
      }
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `API error ${res.status}`);
  }

  const data = await res.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || 'No response';
}

/**
 * 调用 LLM 并要求返回 JSON
 * @param {string} systemPrompt
 * @param {string} userPrompt
 * @param {string} apiKey
 * @returns {Promise<Object>}
 */
export async function callLLMforJSON(systemPrompt, userPrompt, apiKey) {
  const text = await callLLM(
    systemPrompt + '\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation.',
    [{ role: 'user', content: userPrompt }],
    apiKey
  );

  // 清理可能的 markdown 包装
  const clean = text.replace(/```json|```/g, '').trim();
  try {
    return JSON.parse(clean);
  } catch {
    console.warn('JSON parse failed, raw:', text);
    return null;
  }
}
