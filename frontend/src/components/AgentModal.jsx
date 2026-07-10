import { useEffect, useState } from "react";

const MODEL_SUGGESTIONS = [
  "llama-3.3-70b-versatile",
  "llama-3.1-8b-instant",
  "gemma2-9b-it",
  "mixtral-8x7b-32768",
];

const EMPTY_FORM = {
  name: "",
  description: "",
  system_prompt: "You are a helpful assistant.",
  model: "llama-3.3-70b-versatile",
  temperature: 0.7,
  tool_names: [],
};

export default function AgentModal({ agent, tools, onSave, onClose, saving }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [error, setError] = useState("");

  useEffect(() => {
    if (agent) {
      setForm({
        name: agent.name,
        description: agent.description || "",
        system_prompt: agent.system_prompt,
        model: agent.model,
        temperature: agent.temperature,
        tool_names: agent.tool_names || [],
      });
    } else {
      setForm(EMPTY_FORM);
    }
  }, [agent]);

  function toggleTool(name) {
    setForm((f) => ({
      ...f,
      tool_names: f.tool_names.includes(name)
        ? f.tool_names.filter((t) => t !== name)
        : [...f.tool_names, name],
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!form.name.trim()) {
      setError("Give your agent a name.");
      return;
    }
    try {
      await onSave(form);
    } catch (err) {
      setError(err.message || "Failed to save agent.");
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal agent-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{agent ? "Edit agent" : "Create agent"}</h2>
          <button className="icon-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="auth-error">{error}</div>}

          <div className="form-row">
            <label>Name</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Research Assistant"
              required
            />
          </div>

          <div className="form-row">
            <label>Description (optional)</label>
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="What is this agent for?"
            />
          </div>

          <div className="form-row">
            <label>System prompt</label>
            <textarea
              rows={5}
              value={form.system_prompt}
              onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
            />
          </div>

          <div className="form-row-split">
            <div className="form-row">
              <label>Model</label>
              <input
                list="model-suggestions"
                value={form.model}
                onChange={(e) => setForm({ ...form, model: e.target.value })}
              />
              <datalist id="model-suggestions">
                {MODEL_SUGGESTIONS.map((m) => (
                  <option value={m} key={m} />
                ))}
              </datalist>
            </div>

            <div className="form-row">
              <label>Temperature: {form.temperature}</label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={form.temperature}
                onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div className="form-row">
            <label>Tools</label>
            <div className="tool-grid">
              {tools.map((t) => (
                <label
                  key={t.name}
                  className={`tool-card ${form.tool_names.includes(t.name) ? "selected" : ""} ${
                    !t.available ? "unavailable" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={form.tool_names.includes(t.name)}
                    disabled={!t.available}
                    onChange={() => toggleTool(t.name)}
                  />
                  <div>
                    <div className="tool-card-name">
                      {t.name}
                      {!t.available && <span className="tool-badge">needs key</span>}
                    </div>
                    <div className="tool-card-desc">{t.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving…" : agent ? "Save changes" : "Create agent"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
