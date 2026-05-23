import { useState, useEffect, useRef } from "react";
import { ListChecks, Check, Trash2, RefreshCw, AlertCircle, Send, Bot, User } from "lucide-react";

interface Task {
  id: string; task: string; group_name?: string; priority: string;
  status: string; recurrence?: string; created_at: string;
}
interface ChatMsg { role: "user" | "assistant"; content: string; }

export function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatting, setChatting] = useState(false);
  const chatEnd = useRef<HTMLDivElement>(null);

  const fetchTasks = async () => {
    try { const r = await fetch("/api/tasks"); const d = await r.json(); setTasks(d.tasks ?? []); }
    catch (e) { setError(e instanceof Error ? e.message : null); }
    finally { setLoading(false); }
  };
  useEffect(() => { fetchTasks(); }, []);

  const completeTask = async (id: string) => {
    await fetch("/api/tasks/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task_id: id }) });
    fetchTasks();
  };
  const deleteTask = async (id: string) => {
    await fetch("/api/tasks/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task_id: id }) });
    fetchTasks();
  };
  const actualSave = async (task: string, priority: string, group: string, recurrence?: string) => {
    await fetch("/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ task, priority, group, recurrence }) });
    setChat([]); setChatting(false); fetchTasks();
  };

  const sendToFritz = async () => {
    const text = chatInput.trim();
    if (!text || chatting) return;
    setChatInput("");
    const userMsg: ChatMsg = { role: "user", content: text };
    const newChat = [...chat, userMsg, { role: "assistant", content: "" }];
    setChat(newChat);
    setChatting(true);

    try {
      const history = chat.map(m => `${m.role}: ${m.content}`).join("\n");
      const sysPrompt = `You are Fritz, Sandra's AI agent. You are helping her create a task.

Current conversation:
${history}

User just said: "${text}"

Your job: figure out what task Sandra wants. If it's clear, output JSON:
{"action":"save","task":"...","priority":"high|medium|low","group":"self|human|external","recurrence":"... or null"}

If it's unclear and you need to ask something, output:
{"action":"ask","text":"your clarifying question here"}

If the task is impossible (square the circle, perpetual motion, etc.), output:
{"action":"refuse","text":"humorous refusal"}

Output ONLY the JSON, no other text.`;

      const r = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [{ role: "user", content: sysPrompt }], model: "" }),
      });
      const reader = r.body?.getReader();
      let full = "";
      if (reader) {
        const dec = new TextDecoder();
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = dec.decode(value, { stream: true });
          for (const line of chunk.split("\n").filter(l => l.startsWith("data: "))) {
            try {
              const d = JSON.parse(line.slice(6));
              if (d.c) full += d.c;
            } catch {}
          }
        }
      }

      // Parse the LLM response
      const jsonMatch = full.match(/\{.*\}/s);
      if (jsonMatch) {
        const resp = JSON.parse(jsonMatch[0]);
        if (resp.action === "save") {
          setChat(c => { const nc = [...c]; nc[nc.length - 1] = { role: "assistant", content: `✅ Saved: "${resp.task}" (${resp.priority}, ${resp.group})${resp.recurrence ? `, repeats: ${resp.recurrence}` : ""}` }; return nc; });
          await actualSave(resp.task, resp.priority, resp.group, resp.recurrence || undefined);
        } else if (resp.action === "ask") {
          setChat(c => { const nc = [...c]; nc[nc.length - 1] = { role: "assistant", content: resp.text }; return nc; });
        } else if (resp.action === "refuse") {
          setChat(c => { const nc = [...c]; nc[nc.length - 1] = { role: "assistant", content: `🤨 ${resp.text}` }; return nc; });
        }
      } else {
        setChat(c => { const nc = [...c]; nc[nc.length - 1] = { role: "assistant", content: full.slice(0, 500) }; return nc; });
      }
    } catch (e) {
      setChat(c => { const nc = [...c]; nc[nc.length - 1] = { role: "assistant", content: `Error: ${e}` }; return nc; });
    }
    setChatting(false);
  };

  const prioColor = (p: string) => p === "high" ? "text-red-400" : p === "medium" ? "text-amber-400" : "text-slate-400";
  const groupColor = (g?: string) => g === "human" ? "text-blue-400" : g === "external" ? "text-purple-400" : "text-green-400";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ListChecks className="w-6 h-6 text-fleet-400" />
        <h2 className="text-xl font-bold text-white">Tasks</h2>
        <div className="flex-1" />
        <button onClick={() => setChatting(!chatting ? true : null as any)} disabled={chatting}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5"
        ><Send className="w-3.5 h-3.5" /> New Task</button>
        <button onClick={fetchTasks} disabled={loading}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5"
        ><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh</button>
      </div>

      {error && <div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300"><AlertCircle className="w-4 h-4 shrink-0" />{error}</div>}

      {/* Chat-based task creation */}
      {chatting !== false && (
        <div className="border border-slate-800 rounded-lg bg-slate-900/50">
          <div className="h-64 overflow-y-auto p-3 space-y-2">
            {chat.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-8">Tell me what you want done. I'll ask questions if I need more info.</p>
            )}
            {chat.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : ""}`}>
                <div className={`p-2 rounded-lg max-w-[80%] text-sm ${m.role === "user" ? "bg-fleet-800 text-fleet-200" : "bg-slate-800 text-slate-300"}`}>
                  {m.content}
                </div>
              </div>
            ))}
            <div ref={chatEnd} />
          </div>
          <div className="flex gap-2 border-t border-slate-800 p-2">
            <input value={chatInput} onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendToFritz()}
              placeholder="e.g. Get arxiv papers at 9am, or speak a sonnet at 11..."
              className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600" />
            <button onClick={sendToFritz} disabled={chatting || !chatInput.trim()}
              className="px-3 py-2 bg-fleet-800 text-fleet-200 rounded-lg hover:bg-fleet-700 disabled:opacity-40"><Send className="w-4 h-4" /></button>
          </div>
        </div>
      )}

      {/* Task list */}
      {tasks.length === 0 && !loading && <p className="text-sm text-slate-500">No tasks.</p>}
      <div className="grid grid-cols-1 gap-2">
        {tasks.map(t => (
          <div key={t.id} className="flex items-center gap-3 border border-slate-800 rounded-lg bg-slate-900/50 px-4 py-3 hover:border-slate-700 transition-colors">
            <button onClick={() => completeTask(t.id)} className="shrink-0 w-6 h-6 rounded border border-slate-700 flex items-center justify-center hover:border-green-500 hover:text-green-400 text-slate-600"><Check className="w-3.5 h-3.5" /></button>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200 truncate">{t.task}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`text-[10px] uppercase ${prioColor(t.priority)}`}>{t.priority}</span>
                <span className={`text-[10px] ${groupColor(t.group_name)}`}>{t.group_name}</span>
                {t.recurrence && <span className="text-[10px] text-slate-600">{t.recurrence}</span>}
              </div>
            </div>
            <button onClick={() => deleteTask(t.id)} className="shrink-0 text-slate-600 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
