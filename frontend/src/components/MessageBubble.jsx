import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MessageBubble({ role, content, pending, activeTool }) {
  const isUser = role === "user";

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="message-avatar">{isUser ? "U" : "AI"}</div>
      <div className="message-content">
        {activeTool && <div className="tool-indicator">Using {activeTool}…</div>}
        {content ? (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : pending ? (
          <span className="typing-dots">
            <span></span>
            <span></span>
            <span></span>
          </span>
        ) : null}
      </div>
    </div>
  );
}
