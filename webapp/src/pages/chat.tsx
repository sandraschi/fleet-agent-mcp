import { useState, useRef, useEffect } from "react";
import { Send, Trash2, Bot, User, RefreshCw, Terminal } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/api/settings")
      .then((r) => r.json())
      .then((s) => { if (s.model) setModel(s.model); })
      .catch(() => {});
    fetch("/api/models")
      .then((r) => r.json())
      .then((d) => setModels((d.models ?? []).map((m: any) => m.name)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setError(null);

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);

    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: text }],
          model: model || undefined,
        }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.c) {
              setMessages((prev) => {
                const last = [...prev];
                const idx = last.length - 1;
                if (last[idx]?.role === "assistant") {
                  last[idx] = { ...last[idx], content: last[idx].content + data.c };
                }
                return last;
              });
            }
            if (data.done) {
              setStreaming(false);
            }
            if (data.error) {
              setError(data.error);
              setStreaming(false);
            }
          } catch { /* skip parse errors */ }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
      setStreaming(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 shrink-0">
        <Bot className="w-6 h-6 text-fleet-400" />
        <h2 className="text-xl font-bold text-white">Chat</h2>
        <div className="flex-1" />
        <div className="flex items-center gap-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300 font-mono focus:border-fleet-500 outline-none"
          >
            <option value="">Default model</option>
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-white transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Bot className="w-12 h-12 mb-3 text-slate-700" />
            <p className="text-sm">Chat with Lumen — your fleet agent</p>
            <p className="text-xs text-slate-600 mt-1">
              Uses identity files (SOUL.md, NORTH_STAR.md) as system prompt
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="p-2 rounded-lg bg-slate-800 h-fit mt-1">
                <Bot className="w-4 h-4 text-fleet-400" />
              </div>
            )}
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-fleet-800 text-white rounded-br-sm"
                  : "bg-slate-800/80 text-slate-200 rounded-bl-sm"
              }`}
            >
              {msg.content || (i === messages.length - 1 && streaming ? (
                <span className="inline-flex gap-0.5">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </span>
              ) : "")}
            </div>
            {msg.role === "user" && (
              <div className="p-2 rounded-lg bg-fleet-900 h-fit mt-1">
                <User className="w-4 h-4 text-fleet-300" />
              </div>
            )}
          </div>
        ))}

        {error && (
          <div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/30 p-3 text-sm text-red-300">
            <Terminal className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 border border-slate-800 rounded-lg bg-slate-900/80 p-2 flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Lumen..."
          rows={1}
          className="flex-1 bg-transparent border-none outline-none text-sm text-slate-200 placeholder-slate-500 resize-none px-2 py-1.5"
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim() || streaming}
          className="px-3 py-2 bg-fleet-700 hover:bg-fleet-600 disabled:bg-slate-800 text-white rounded-lg transition-colors disabled:text-slate-500"
        >
          {streaming ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
    </div>
  );
}
