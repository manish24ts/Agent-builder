const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getToken() {
  return localStorage.getItem("token");
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/login";
    throw new Error("Session expired. Please sign in again.");
  }

  if (!res.ok) {
    let detail = "Request failed.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // ---- auth ----
  register: (email, password, name) =>
    request("/auth/register", { method: "POST", body: { email, password, name }, auth: false }),
  login: (email, password) =>
    request("/auth/login", { method: "POST", body: { email, password }, auth: false }),
  loginWithGoogle: (id_token) =>
    request("/auth/google", { method: "POST", body: { id_token }, auth: false }),
  me: () => request("/auth/me"),

  // ---- agents ----
  listAgents: () => request("/agents"),
  getTools: () => request("/agents/tools"),
  createAgent: (payload) => request("/agents", { method: "POST", body: payload }),
  updateAgent: (id, payload) => request(`/agents/${id}`, { method: "PUT", body: payload }),
  deleteAgent: (id) => request(`/agents/${id}`, { method: "DELETE" }),

  // ---- conversations ----
  listConversations: (agentId) =>
    request(agentId ? `/conversations?agent_id=${agentId}` : "/conversations"),
  createConversation: (agentId, title) =>
    request("/conversations", { method: "POST", body: { agent_id: agentId, title } }),
  getConversation: (id) => request(`/conversations/${id}`),
  renameConversation: (id, title) => request(`/conversations/${id}`, { method: "PATCH", body: { title } }),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: "DELETE" }),
};

/**
 * Streams a chat response via SSE-over-fetch (POST, so EventSource can't be used).
 * Calls onEvent(parsedJson) for every "data: {...}" line received.
 */
export async function streamChat(conversationId, message, onEvent, signal) {
  const token = getToken();
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ conversation_id: conversationId, message }),
    signal,
  });

  if (!res.ok || !res.body) {
    let detail = "Chat request failed.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop(); // keep the last (possibly incomplete) chunk

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const jsonStr = trimmed.slice(5).trim();
      if (!jsonStr) continue;
      try {
        onEvent(JSON.parse(jsonStr));
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}

export { API_URL };
