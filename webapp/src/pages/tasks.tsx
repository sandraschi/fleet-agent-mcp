import { useState, useEffect } from "react";
import { ListChecks, Plus, Check, Trash2, RefreshCw, AlertCircle } from "lucide-react";

interface Task {
  id: string;
  task: string;
  group_name?: string;
  priority: string;
  status: string;
  recurrence?: string;
  created_at: string;
}

export function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newTask, setNewTask] = useState("");
  const [newPriority, setNewPriority] = useState("medium");
  const [newGroup, setNewGroup] = useState("self");
  const [showForm, setShowForm] = useState(false);

  const fetchTasks = async (status?: string) => {
    setLoading(true);
    try {
      const q = status ? `?status=${status}` : "";
      const r = await fetch(`/api/tasks${q}`);
      const d = await r.json();
      setTasks(d.tasks ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTasks(); }, []);

  const addTask = async () => {
    if (!newTask.trim()) return;
    try {
      await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: newTask, priority: newPriority, group: newGroup }),
      });
      setNewTask("");
      setShowForm(false);
      fetchTasks();
    } catch {}
  };

  const completeTask = async (id: string) => {
    await fetch("/api/tasks/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: id }),
    });
    fetchTasks();
  };

  const deleteTask = async (id: string) => {
    await fetch("/api/tasks/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_id: id }),
    });
    fetchTasks();
  };

  const prioColor = (p: string) =>
    p === "high" ? "text-red-400" : p === "medium" ? "text-amber-400" : "text-slate-400";
  const groupColor = (g?: string) =>
    g === "human" ? "text-blue-400" : g === "external" ? "text-purple-400" : "text-green-400";

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ListChecks className="w-6 h-6 text-fleet-400" />
        <h2 className="text-xl font-bold text-white">Tasks</h2>
        <div className="flex-1" />
        <button onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors">
          <Plus className="w-3.5 h-3.5" /> Add Task
        </button>
        <button onClick={() => fetchTasks()} disabled={loading}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {showForm && (
        <div className="border border-slate-800 rounded-lg bg-slate-900/50 p-4 space-y-3">
          <textarea value={newTask} onChange={(e) => setNewTask(e.target.value)}
            placeholder="What should Fritz do?"
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-slate-200 placeholder:text-slate-600 resize-none h-20"
          />
          <div className="flex gap-3">
            <select value={newPriority} onChange={(e) => setNewPriority(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-400">
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select value={newGroup} onChange={(e) => setNewGroup(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-400">
              <option value="self">Self (Fritz)</option>
              <option value="human">Human (Sandra)</option>
              <option value="external">External</option>
            </select>
            <button onClick={addTask}
              className="px-3 py-1 text-xs bg-fleet-800 text-fleet-200 rounded-lg hover:bg-fleet-700 transition-colors">
              Save
            </button>
          </div>
        </div>
      )}

      {tasks.length === 0 && !loading && (
        <p className="text-sm text-slate-500">No tasks. Add one to tell Fritz what to do.</p>
      )}

      <div className="grid grid-cols-1 gap-2">
        {tasks.map((t) => (
          <div key={t.id}
            className="flex items-center gap-3 border border-slate-800 rounded-lg bg-slate-900/50 px-4 py-3 hover:border-slate-700 transition-colors">
            <button onClick={() => completeTask(t.id)}
              className="shrink-0 w-6 h-6 rounded border border-slate-700 flex items-center justify-center hover:border-green-500 hover:text-green-400 transition-colors text-slate-600">
              <Check className="w-3.5 h-3.5" />
            </button>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200 truncate">{t.task}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`text-[10px] uppercase ${prioColor(t.priority)}`}>{t.priority}</span>
                <span className={`text-[10px] ${groupColor(t.group_name)}`}>{t.group_name}</span>
                {t.recurrence && <span className="text-[10px] text-slate-600">{t.recurrence}</span>}
              </div>
            </div>
            <button onClick={() => deleteTask(t.id)}
              className="shrink-0 text-slate-600 hover:text-red-400 transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
