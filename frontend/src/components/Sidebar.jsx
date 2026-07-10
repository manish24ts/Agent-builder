import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function Sidebar({
  agents,
  activeAgentId,
  onSelectAgent,
  onOpenAgentModal,
  onDeleteAgent,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onRenameConversation,
}) {
  const { user, logout } = useAuth();
  const [agentMenuOpen, setAgentMenuOpen] = useState(false);
  const [renamingId, setRenamingId] = useState(null);
  const [renameValue, setRenameValue] = useState("");

  const activeAgent = agents.find((a) => a.id === activeAgentId);

  function startRename(conv) {
    setRenamingId(conv.id);
    setRenameValue(conv.title);
  }

  function commitRename(conv) {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== conv.title) {
      onRenameConversation(conv.id, trimmed);
    }
    setRenamingId(null);
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="auth-brand-mark">AB</div>
        <span>Agent Builder</span>
      </div>

      <button className="sidebar-newchat" onClick={onNewChat} disabled={!activeAgentId}>
        + New chat
      </button>

      <div className="sidebar-section-label">Agent</div>
      <div className="agent-switcher">
        <button className="agent-switcher-btn" onClick={() => setAgentMenuOpen((v) => !v)}>
          <span className="agent-dot" />
          <span className="agent-switcher-name">{activeAgent ? activeAgent.name : "Select an agent"}</span>
          <span className="chevron">▾</span>
        </button>

        {agentMenuOpen && (
          <div className="agent-menu">
            {agents.map((a) => (
              <div
                key={a.id}
                className={`agent-menu-item ${a.id === activeAgentId ? "active" : ""}`}
                onClick={() => {
                  onSelectAgent(a.id);
                  setAgentMenuOpen(false);
                }}
              >
                <span className="agent-menu-item-name">{a.name}</span>
                <button
                  className="icon-btn danger"
                  title="Delete agent"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete agent "${a.name}"? This deletes its conversations too.`)) {
                      onDeleteAgent(a.id);
                    }
                  }}
                >
                  ✕
                </button>
              </div>
            ))}
            <div
              className="agent-menu-item new"
              onClick={() => {
                setAgentMenuOpen(false);
                onOpenAgentModal(null);
              }}
            >
              + Create agent
            </div>
          </div>
        )}
      </div>

      {activeAgent && (
        <button className="sidebar-edit-agent" onClick={() => onOpenAgentModal(activeAgent)}>
          ⚙ Edit "{activeAgent.name}"
        </button>
      )}

      <div className="sidebar-section-label">Chats</div>
      <div className="conversation-list">
        {conversations.length === 0 && <div className="conversation-empty">No conversations yet.</div>}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conversation-item ${c.id === activeConversationId ? "active" : ""}`}
            onClick={() => onSelectConversation(c.id)}
          >
            {renamingId === c.id ? (
              <input
                className="conversation-rename-input"
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={() => commitRename(c)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename(c);
                  if (e.key === "Escape") setRenamingId(null);
                }}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span className="conversation-title">{c.title}</span>
            )}
            <div className="conversation-actions">
              <button
                className="icon-btn"
                title="Rename"
                onClick={(e) => {
                  e.stopPropagation();
                  startRename(c);
                }}
              >
                ✎
              </button>
              <button
                className="icon-btn danger"
                title="Delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (confirm("Delete this conversation?")) onDeleteConversation(c.id);
                }}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-user">
        <div className="sidebar-user-avatar">{(user?.name || user?.email || "?")[0].toUpperCase()}</div>
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">{user?.name || "Account"}</div>
          <div className="sidebar-user-email">{user?.email}</div>
        </div>
        <button className="icon-btn" title="Log out" onClick={logout}>
          ⏻
        </button>
      </div>
    </aside>
  );
}
