import { useEffect, useRef, useState } from "react";
import { api, streamChat } from "../api/client";
import Sidebar from "../components/Sidebar.jsx";
import AgentModal from "../components/AgentModal.jsx";
import MessageBubble from "../components/MessageBubble.jsx";
import "./Chat.css";

export default function Chat() {
  const [agents, setAgents] = useState([]);
  const [tools, setTools] = useState([]);
  const [activeAgentId, setActiveAgentId] = useState(null);

  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);

  const [modalAgent, setModalAgent] = useState(undefined); // undefined = closed, null = new, object = edit
  const [savingAgent, setSavingAgent] = useState(false);

  const [draft, setDraft] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [activeTool, setActiveTool] = useState(null);
  const [chatError, setChatError] = useState("");

  const messagesEndRef = useRef(null);
  const abortRef = useRef(null);

  // ---- initial load ----
  useEffect(() => {
    api.listAgents().then((list) => {
      setAgents(list);
      if (list.length > 0) setActiveAgentId(list[0].id);
      else setModalAgent(null); // force agent creation on first run
    });
    api.getTools().then(setTools);
  }, []);

  // ---- load conversations when active agent changes ----
  useEffect(() => {
    if (!activeAgentId) return;
    setActiveConversationId(null);
    setMessages([]);
    api.listConversations(activeAgentId).then(setConversations);
  }, [activeAgentId]);

  // ---- load messages when active conversation changes ----
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    api.getConversation(activeConversationId).then((conv) => {
      setMessages(conv.messages.map((m) => ({ role: m.role, content: m.content })));
    });
  }, [activeConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // ---- agent CRUD ----
  async function handleSaveAgent(form) {
    setSavingAgent(true);
    try {
      if (modalAgent && modalAgent.id) {
        const updated = await api.updateAgent(modalAgent.id, form);
        setAgents((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      } else {
        const created = await api.createAgent(form);
        setAgents((prev) => [created, ...prev]);
        setActiveAgentId(created.id);
      }
      setModalAgent(undefined);
    } finally {
      setSavingAgent(false);
    }
  }

  async function handleDeleteAgent(id) {
    await api.deleteAgent(id);
    setAgents((prev) => {
      const next = prev.filter((a) => a.id !== id);
      if (activeAgentId === id) setActiveAgentId(next[0]?.id || null);
      return next;
    });
  }

  // ---- conversation actions ----
  function handleNewChat() {
    setActiveConversationId(null);
    setMessages([]);
    setChatError("");
  }

  async function handleDeleteConversation(id) {
    await api.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
      setMessages([]);
    }
  }

  async function handleRenameConversation(id, title) {
    const updated = await api.renameConversation(id, title);
    setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
  }

  // ---- send message / stream ----
  async function handleSend() {
    const text = draft.trim();
    if (!text || isStreaming || !activeAgentId) return;

    setChatError("");
    setDraft("");

    let conversationId = activeConversationId;
    try {
      if (!conversationId) {
        const conv = await api.createConversation(activeAgentId, "New Conversation");
        conversationId = conv.id;
        setActiveConversationId(conv.id);
        setConversations((prev) => [conv, ...prev]);
      }
    } catch (err) {
      setChatError(err.message || "Couldn't start a new conversation.");
      setDraft(text);
      return;
    }

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsStreaming(true);
    setStreamingText("");
    setActiveTool(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        conversationId,
        text,
        (event) => {
          if (event.type === "token") {
            setStreamingText((prev) => prev + event.content);
          } else if (event.type === "tool_start") {
            setActiveTool(event.tool);
          } else if (event.type === "tool_end") {
            setActiveTool(null);
          } else if (event.type === "error") {
            setChatError(event.error);
          }
        },
        controller.signal
      );
    } catch (err) {
      if (err.name !== "AbortError") {
        setChatError(err.message || "The chat stream failed.");
      }
    } finally {
      setIsStreaming(false);
      setActiveTool(null);
      setStreamingText((finalText) => {
        if (finalText) {
          setMessages((prev) => [...prev, { role: "assistant", content: finalText }]);
        }
        return "";
      });
      // refresh sidebar title (backend auto-titles new conversations from first message)
      api.listConversations(activeAgentId).then(setConversations);
      abortRef.current = null;
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const activeAgent = agents.find((a) => a.id === activeAgentId);

  return (
    <div className="chat-layout">
      <Sidebar
        agents={agents}
        activeAgentId={activeAgentId}
        onSelectAgent={setActiveAgentId}
        onOpenAgentModal={(agent) => setModalAgent(agent || null)}
        onDeleteAgent={handleDeleteAgent}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={setActiveConversationId}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
      />

      <main className="chat-main">
        {!activeAgent ? (
          <div className="full-screen-center">Create an agent to get started.</div>
        ) : (
          <>
            <header className="chat-header">
              <div>
                <div className="chat-header-name">{activeAgent.name}</div>
                <div className="chat-header-model">{activeAgent.model}</div>
              </div>
            </header>

            <div className="message-list">
              {messages.length === 0 && !isStreaming && (
                <div className="chat-empty">
                  <div className="chat-empty-title">{activeAgent.name}</div>
                  <p>{activeAgent.description || "Start a conversation below."}</p>
                </div>
              )}
              {messages.map((m, i) => (
                <MessageBubble key={i} role={m.role} content={m.content} />
              ))}
              {isStreaming && (
                <MessageBubble role="assistant" content={streamingText} pending activeTool={activeTool} />
              )}
              <div ref={messagesEndRef} />
            </div>

            {chatError && <div className="chat-error-banner">{chatError}</div>}

            <div className="chat-input-bar">
              <textarea
                className="chat-input"
                placeholder={`Message ${activeAgent.name}…`}
                rows={1}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
              />
              <button className="chat-send-btn" onClick={handleSend} disabled={isStreaming || !draft.trim()}>
                ➤
              </button>
            </div>
          </>
        )}
      </main>

      {modalAgent !== undefined && (
        <AgentModal
          agent={modalAgent}
          tools={tools}
          onSave={handleSaveAgent}
          onClose={() => {
            // don't allow closing without an agent on first run
            if (agents.length > 0) setModalAgent(undefined);
          }}
          saving={savingAgent}
        />
      )}
    </div>
  );
}
