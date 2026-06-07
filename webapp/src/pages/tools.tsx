import { GitBranch, ListChecks, Brain, User, Package, TrendingUp, Activity, ExternalLink, X, Briefcase, Newspaper } from "lucide-react";
import { useState } from "react";

interface Param {
  name: string;
  type: string;
  description: string;
  required: boolean;
  default?: string;
}

interface Tool {
  name: string;
  type: "R" | "W" | "D";
  description: string;
  note?: string;
  params: Param[];
  returns: string;
  examples: string[];
}

interface Subsystem {
  id: string;
  icon: typeof GitBranch;
  label: string;
  count: number;
  color: string;
  tools: Tool[];
}

const SUBSYSTEMS: Subsystem[] = [
  {
    id: "flowforge", icon: GitBranch, label: "FlowForge", count: 9, color: "text-fleet-400",
    tools: [
      { name: "workflow_define", type: "W", description: "Register a workflow from a YAML file. Enforces step-by-step execution with DAG of nodes.",
        params: [{ name: "yaml_path", type: "str", description: "Path to workflow YAML file.", required: true }],
        returns: '{"success": bool, "workflow": {"name": str, "nodes": int, "start": str}, "message": str}',
        examples: ['workflow_define("workflows/daily.yaml")'] },
      { name: "workflow_autodiscover", type: "W", description: "Auto-discover and register all YAML workflows from ./workflows/ and ~/.fleet-agent/workflows/.",
        params: [],
        returns: '{"success": bool, "registered": int, "workflows": list[str], "message": str}',
        examples: ["workflow_autodiscover()"] },
      { name: "workflow_start", type: "W", description: "Start a new workflow instance from a registered workflow.",
        params: [{ name: "name", type: "str", description: "Name of the registered workflow to start.", required: true }],
        returns: '{"success": bool, "instance": dict, "first_task": str, "message": str}',
        examples: ['workflow_start("daily")'] },
      { name: "workflow_status", type: "R", description: "Get current workflow instance status — node, task, and available branches.",
        params: [],
        returns: '{"success": bool, "workflow": str, "current_node": str, "task": str, "branches": list|null, "is_terminal": bool, "message": str}',
        examples: ["workflow_status()"] },
      { name: "workflow_next", type: "W", description: "Complete current node and advance to the next step.",
        params: [{ name: "branch", type: "int | null", description: "Branch index to take (0-based). Required if current node has branches.", required: false, default: "null" }],
        returns: '{"success": bool, "next_node": str, "next_task": str, "completed": bool, "message": str}',
        examples: ["workflow_next()", "workflow_next(branch=0)"] },
      { name: "workflow_log", type: "R", description: "View execution history for the current workflow instance.",
        params: [],
        returns: '{"success": bool, "workflow": str, "history": list[dict], "steps_completed": int, "message": str}',
        examples: ["workflow_log()"] },
      { name: "workflow_list", type: "R", description: "List all registered workflow definitions.",
        params: [],
        returns: '{"success": bool, "workflows": list[dict], "count": int, "message": str}',
        examples: ["workflow_list()"] },
      { name: "workflow_active", type: "R", description: "List all active workflow instances.",
        params: [],
        returns: '{"success": bool, "active": list[dict], "count": int, "message": str}',
        examples: ["workflow_active()"] },
      { name: "workflow_reset", type: "W", description: "Reset the current workflow instance back to its start node.",
        params: [],
        returns: '{"success": bool, "workflow": str, "message": str}',
        examples: ["workflow_reset()"] },
    ],
  },
  {
    id: "pulse", icon: ListChecks, label: "Pulse", count: 6, color: "text-emerald-400",
    tools: [
      { name: "pulse_add", type: "W", description: "Add a task to the unified TODO list. Tasks grouped by dependency: self, human, or external.",
        params: [
          { name: "task", type: "str", description: "Task description.", required: true },
          { name: "group", type: "str", description: "Dependency group: 'self', 'human', or 'external'.", required: false, default: '"self"' },
          { name: "priority", type: "str", description: "Priority: 'high', 'medium', or 'low'.", required: false, default: '"medium"' },
          { name: "recurrence", type: "str | null", description: "Cron-style recurrence for repeating tasks.", required: false, default: "null" },
        ],
        returns: '{"success": bool, "task": dict, "message": str}',
        examples: ['pulse_add("Write SPEC.md", group="self", priority="high")', 'pulse_add("Sync every 4h", group="self", recurrence="0 */4 * * *")'] },
      { name: "pulse_list", type: "R", description: "List all tasks, optionally filtered by group or status.",
        params: [
          { name: "group", type: "str | null", description: "Filter by group: 'self', 'human', 'external'.", required: false, default: "null" },
          { name: "status", type: "str | null", description: "Filter by status: 'pending', 'done', 'cancelled'.", required: false, default: "null" },
        ],
        returns: '{"success": bool, "tasks": list[dict], "count": int, "message": str}',
        examples: ["pulse_list()", 'pulse_list(group="self", status="pending")'] },
      { name: "pulse_complete", type: "W", description: "Mark a task as complete.",
        params: [{ name: "task_id", type: "str", description: "ID of the task to mark as complete.", required: true }],
        returns: '{"success": bool, "task": dict, "message": str}',
        examples: ['pulse_complete("a1b2c3d4")'] },
      { name: "pulse_delete", type: "W", description: "Delete a task permanently.",
        params: [{ name: "task_id", type: "str", description: "ID of the task to delete.", required: true }],
        returns: '{"success": bool, "message": str}',
        examples: ['pulse_delete("a1b2c3d4")'] },
      { name: "pulse_stale", type: "R", description: "Find tasks untouched for >= N days.",
        params: [{ name: "days", type: "int", description: "Number of days without updates to flag as stale.", required: false, default: "3" }],
        returns: '{"success": bool, "stale_tasks": list[dict], "count": int, "message": str}',
        examples: ["pulse_stale()", "pulse_stale(days=7)"] },
      { name: "pulse_align", type: "R", description: "Display tasks sorted by strategic alignment with north star goals.",
        note: "Requires NORTH_STAR.md in identity/; picks highest-priority, most overdue tasks first.",
        params: [],
        returns: '{"success": bool, "recommendations": list[dict], "message": str}',
        examples: ["pulse_align()"] },
    ],
  },
  {
    id: "memory", icon: Brain, label: "Memory", count: 7, color: "text-amber-400",
    tools: [
      { name: "memory_card_create", type: "W", description: "Create a knowledge card in the wiki. Each card captures a concept, pattern, lesson, or reference.",
        params: [
          { name: "title", type: "str", description: "Card title.", required: true },
          { name: "content", type: "str", description: "Card content (Markdown).", required: true },
          { name: "tags", type: "list[str] | null", description: "Tags for categorization and search.", required: false, default: "null" },
          { name: "category", type: "str", description: "Category: general, pattern, project, mistake, reference.", required: false, default: '"general"' },
        ],
        returns: '{"success": bool, "card": dict, "message": str}',
        examples: ['memory_card_create("SQLite WAL mode", "WAL provides concurrent reads...", tags=["sqlite", "performance"])'] },
      { name: "memory_card_search", type: "R", description: "Search knowledge cards by full-text query.",
        params: [{ name: "query", type: "str", description: "Search query (matches title, content, and tags).", required: true }],
        returns: '{"success": bool, "cards": list[dict], "count": int, "message": str}',
        examples: ['memory_card_search("state machine")'] },
      { name: "memory_card_update", type: "W", description: "Update a knowledge card's content and/or tags. Implements query-writeback.",
        params: [
          { name: "card_id", type: "str", description: "Card ID to update.", required: true },
          { name: "content", type: "str", description: "New content (replaces existing).", required: true },
          { name: "tags", type: "list[str] | null", description: "New tags (replaces existing if provided).", required: false, default: "null" },
        ],
        returns: '{"success": bool, "card": dict, "message": str}',
        examples: ['memory_card_update("a1b2c3d4", "Updated content...", tags=["updated", "sqlite"])'] },
      { name: "memory_cards_list", type: "R", description: "List all knowledge cards.",
        params: [],
        returns: '{"success": bool, "cards": list[dict], "count": int, "message": str}',
        examples: ["memory_cards_list()"] },
      { name: "memory_lint", type: "R", description: "Lint the knowledge base for issues: broken references, stale cards, untagged cards. Prevents knowledge rot.",
        params: [],
        returns: '{"success": bool, "issues": list[dict], "count": int, "message": str}',
        examples: ["memory_lint()"] },
      { name: "memory_project_note", type: "W", description: "Log a project observation or learning. Captures patterns, gotchas, architecture decisions.",
        params: [
          { name: "project", type: "str", description: "Project name (e.g. 'fleet-agent-mcp', 'flowforge').", required: true },
          { name: "content", type: "str", description: "Note content — what you learned or observed.", required: true },
          { name: "tags", type: "list[str] | null", description: "Tags for cross-referencing.", required: false, default: "null" },
        ],
        returns: '{"success": bool, "note": dict, "message": str}',
        examples: ['memory_project_note("flowforge", "SQLite state survives session restarts", tags=["architecture", "persistence"])'] },
      { name: "memory_project_notes", type: "R", description: "List project notes, optionally filtered by project.",
        params: [{ name: "project", type: "str | null", description: "Filter by project name. If omitted, lists all.", required: false, default: "null" }],
        returns: '{"success": bool, "notes": list[dict], "count": int, "message": str}',
        examples: ["memory_project_notes()", 'memory_project_notes(project="flowforge")'] },
    ],
  },
  {
    id: "identity", icon: User, label: "Identity", count: 4, color: "text-purple-400",
    tools: [
      { name: "identity_whoami", type: "R", description: "Return the agent's self-introduction — name, human partner, and purpose preview.",
        params: [],
        returns: '{"success": bool, "identity": dict, "message": str}',
        examples: ["identity_whoami()"] },
      { name: "identity_soul", type: "R", description: "Read the agent's full SOUL.md — core identity, personality, and constraints.",
        params: [],
        returns: '{"success": bool, "soul": str, "message": str}',
        examples: ["identity_soul()"] },
      { name: "identity_north_star", type: "R", description: "Read the agent's NORTH_STAR.md — purpose, long-term goals, guiding principles. Used by pulse_align().",
        params: [],
        returns: '{"success": bool, "north_star": str, "message": str}',
        examples: ["identity_north_star()"] },
      { name: "identity_user", type: "R", description: "Read USER.md — information about the agent's human partner.",
        params: [],
        returns: '{"success": bool, "user_info": str, "message": str}',
        examples: ["identity_user()"] },
    ],
  },
  {
    id: "teleport", icon: Package, label: "Teleport", count: 3, color: "text-cyan-400",
    tools: [
      { name: "teleport_pack", type: "R", description: "Pack agent identity, memory, workflows, and config into a portable .soul archive.",
        note: "WARNING: .soul files may contain sensitive config data. Treat them like password files.",
        params: [{ name: "output_path", type: "str | null", description: "Output path for .soul file. Defaults to ~/.fleet-agent/{name}_{date}.soul.", required: false, default: "null" }],
        returns: '{"success": bool, "soul_path": str, "file_count": int, "manifest": dict, "message": str}',
        examples: ["teleport_pack()", 'teleport_pack(output_path="/tmp/lumen_backup.soul")'] },
      { name: "teleport_inspect", type: "R", description: "Inspect a .soul archive without unpacking — show manifest and file listing.",
        params: [{ name: "soul_path", type: "str", description: "Path to .soul file to inspect.", required: true }],
        returns: '{"success": bool, "manifest": dict, "files": list[str], "message": str}',
        examples: ['teleport_inspect("lumen_20260519.soul")'] },
      { name: "teleport_unpack", type: "D", description: "Unpack a .soul archive — restore agent identity, memory, workflows, and database.",
        note: "WARNING: Overwrites existing files in the target directory. DESTRUCTIVE operation.",
        params: [
          { name: "soul_path", type: "str", description: "Path to .soul file to unpack.", required: true },
          { name: "target_dir", type: "str | null", description: "Target directory for unpacking. Defaults to ~/.fleet-agent/.", required: false, default: "null" },
        ],
        returns: '{"success": bool, "files_restored": int, "target_dir": str, "message": str}',
        examples: ['teleport_unpack("lumen_20260519.soul")'] },
    ],
  },
  {
    id: "evolution", icon: TrendingUp, label: "Evolution", count: 3, color: "text-rose-400",
    tools: [
      { name: "evolution_record", type: "W", description: "Record a mistake, correction, and lesson in the evolution log. Every correction becomes a permanent lesson.",
        params: [
          { name: "correction", type: "str", description: "What went wrong and how it was fixed.", required: true },
          { name: "lesson", type: "str", description: "The lesson learned — stated as a rule to follow going forward.", required: true },
          { name: "context", type: "str", description: "What was being attempted when the mistake happened.", required: false, default: '""' },
        ],
        returns: '{"success": bool, "entry": dict, "message": str}',
        examples: ['evolution_record(correction="Used shell=True...", lesson="NEVER use shell=True for subprocess", context="State machine engine")'] },
      { name: "evolution_list", type: "R", description: "List recent evolution log entries — corrections and lessons.",
        params: [{ name: "limit", type: "int", description: "Max entries to return.", required: false, default: "50" }],
        returns: '{"success": bool, "entries": list[dict], "count": int, "message": str}',
        examples: ["evolution_list()", "evolution_list(limit=10)"] },
      { name: "evolution_stats", type: "R", description: "Get evolution log statistics — total corrections, unique lessons, patterns.",
        params: [],
        returns: '{"success": bool, "stats": dict, "duplicate_lessons": list, "message": str}',
        examples: ["evolution_stats()"] },
    ],
  },
  {
    id: "heartbeat", icon: Activity, label: "Heartbeat", count: 2, color: "text-green-400",
    tools: [
      { name: "heartbeat_status", type: "R", description: "Agent health check — uptime, active workflows, task count, memory stats.",
        params: [],
        returns: '{"success": bool, "health": dict, "message": str}',
        examples: ["heartbeat_status()"] },
      { name: "heartbeat_wake", type: "W", description: "Agent wake-up routine — check state machine, get current task, suggest next action.",
        note: "Checks active workflow first; if none, checks pending tasks; returns next recommended action.",
        params: [],
        returns: '{"success": bool, "action": dict, "message": str}',
        examples: ["heartbeat_wake()"] },
    ],
  },
  {
    id: "coworker", icon: Briefcase, label: "Coworker", count: 11, color: "text-orange-400",
    tools: [
      { name: "coworker_fleet_pulse", type: "W", description: "Morning Fleet Pulse — MCP health, git snapshot, hub publish.",
        params: [{ name: "deliver", type: "bool", description: "Email report when SMTP configured.", required: false, default: "true" }],
        returns: '{"success": bool, "report": str, "artifact_path": str, "message": str}',
        examples: ["coworker_fleet_pulse()", "coworker_fleet_pulse(deliver=False)"] },
      { name: "coworker_devices_watch", type: "W", description: "Poll devices-mcp /api/fleet/priority — kitchen temp, CO, smoke, Ring.",
        params: [{ name: "deliver", type: "bool", description: "Hub + urgent email on new critical.", required: false, default: "true" }],
        returns: '{"success": bool, "critical_new": list, "message": str}',
        examples: ["coworker_devices_watch()"] },
      { name: "coworker_day_prep", type: "W", description: "Office Day Prep — inbox + pulse tasks + AIWatcher hot items.",
        params: [{ name: "deliver", type: "bool", description: "Email combined report.", required: false, default: "true" }],
        returns: '{"success": bool, "report": str, "message": str}',
        examples: ["coworker_day_prep()"] },
      { name: "coworker_bootstrap", type: "W", description: "Seed default coworker recurring tasks (idempotent).",
        params: [],
        returns: '{"success": bool, "created": int, "message": str}',
        examples: ["coworker_bootstrap()"] },
    ],
  },
  {
    id: "intel_hub", icon: Newspaper, label: "Intel Hub", count: 3, color: "text-violet-400",
    tools: [
      { name: "intel_reports_publish", type: "W", description: "Publish markdown/HTML report to Intel Hub (port 11027).",
        params: [
          { name: "title", type: "str", description: "Report title.", required: true },
          { name: "markdown", type: "str", description: "Markdown body.", required: true },
        ],
        returns: '{"success": bool, "id": str, "url_path": str, "hub_url": str}',
        examples: ['intel_reports_publish(title="Test", markdown="# Hello")'] },
      { name: "intel_reports_list", type: "R", description: "List published intel reports from hub catalog.",
        params: [{ name: "limit", type: "int", description: "Max reports.", required: false, default: "20" }],
        returns: '{"success": bool, "reports": list, "hub_url": str, "count": int}',
        examples: ["intel_reports_list()", "intel_reports_list(limit=5)"] },
      { name: "aiwatcher_push_event", type: "W", description: "Push structured event into AIWatcher Fleet Events feed.",
        params: [
          { name: "title", type: "str", description: "Event title.", required: true },
          { name: "urgency_hint", type: "float", description: "0–10 pre-score.", required: false },
        ],
        returns: '{"success": bool, "message": str}',
        examples: ['aiwatcher_push_event(title="Pulse", urgency_hint=7.5)'] },
    ],
  },
];

const TYPE_BADGES: Record<string, string> = {
  R: "bg-blue-900/50 text-blue-300 border-blue-700",
  W: "bg-amber-900/50 text-amber-300 border-amber-700",
  D: "bg-red-900/50 text-red-300 border-red-700",
};

const TYPE_LABELS: Record<string, string> = {
  R: "READ_ONLY",
  W: "MUTATING",
  D: "DESTRUCTIVE",
};

const TYPE_LONG: Record<string, string> = {
  R: "Safe to call any time — no side effects.",
  W: "Modifies state — call with awareness.",
  D: "Irreversible — confirm before use.",
};

export function Tools() {
  const [selected, setSelected] = useState<Tool | null>(null);
  const total = SUBSYSTEMS.reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <GitBranch className="w-6 h-6 text-fleet-400" />
        <div>
          <h2 className="text-xl font-bold text-white">MCP Tools</h2>
          <p className="text-sm text-slate-400">{total} tools across {SUBSYSTEMS.length} subsystems</p>
        </div>
        <div className="flex-1" />
        <a
          href="https://github.com/kagura-agent"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-slate-500 hover:text-fleet-400 flex items-center gap-1 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          kagura-agent
        </a>
      </div>

      <div className="flex gap-2 text-xs text-slate-500">
        <span className="bg-blue-900/50 border border-blue-700 px-2 py-0.5 rounded">R = READ_ONLY</span>
        <span className="bg-amber-900/50 border border-amber-700 px-2 py-0.5 rounded">W = MUTATING</span>
        <span className="bg-red-900/50 border border-red-700 px-2 py-0.5 rounded">D = DESTRUCTIVE</span>
      </div>

      {SUBSYSTEMS.map((ss) => (
        <div key={ss.id} className="border border-slate-800 rounded-lg bg-slate-900/50 p-5">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-md bg-slate-800">
              <ss.icon className={`w-5 h-5 ${ss.color}`} />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">{ss.label}</h3>
              <p className="text-xs text-slate-500">{ss.count} tools</p>
            </div>
          </div>
          <div className="space-y-1">
            {ss.tools.map((tool) => (
              <div
                key={tool.name}
                onClick={() => setSelected(tool)}
                className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-slate-800/50 transition-colors cursor-pointer"
                title={`${tool.name} — ${tool.description}`}
              >
                <span
                  className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${TYPE_BADGES[tool.type]}`}
                >
                  {TYPE_LABELS[tool.type]}
                </span>
                <code className="text-sm font-mono text-slate-200">{tool.name}</code>
                <span className="text-xs text-slate-400 flex-1 truncate">— {tool.description}</span>
              </div>
            ))}
          </div>
        </div>
      ))}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setSelected(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-2xl w-full mx-4 shadow-2xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border uppercase ${TYPE_BADGES[selected.type]}`}>
                  {TYPE_LABELS[selected.type]}
                </span>
                <code className="text-sm font-mono text-white font-semibold">{selected.name}</code>
              </div>
              <button onClick={() => setSelected(null)} className="p-1 rounded-md hover:bg-slate-800 transition-colors">
                <X className="w-4 h-4 text-slate-400" />
              </button>
            </div>

            <p className="text-sm text-slate-300 mb-1">{selected.description}</p>
            {selected.note && (
              <p className="text-xs text-amber-400 bg-amber-950/30 border border-amber-800/50 rounded p-2 mb-4">{selected.note}</p>
            )}
            <p className="text-xs text-slate-500 mb-4">
              <span className={`font-semibold ${selected.type === "R" ? "text-blue-400" : selected.type === "W" ? "text-amber-400" : "text-red-400"}`}>
                {TYPE_LABELS[selected.type]}
              </span>
              {" — "}{TYPE_LONG[selected.type]}
            </p>

            {selected.params.length > 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Parameters</h4>
                <div className="space-y-2">
                  {selected.params.map((p) => (
                    <div key={p.name} className="bg-slate-950 border border-slate-800 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <code className="text-sm font-mono text-fleet-300">{p.name}</code>
                        <span className="text-[10px] text-slate-500 font-mono">{p.type}</span>
                        {p.required && <span className="text-[10px] text-red-400 font-medium">required</span>}
                        {!p.required && p.default !== undefined && (
                          <span className="text-[10px] text-slate-500">default: <code className="font-mono text-slate-400">{p.default}</code></span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{p.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {selected.params.length === 0 && (
              <div className="mb-4">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Parameters</h4>
                <p className="text-xs text-slate-600 italic">None — this tool takes no arguments.</p>
              </div>
            )}

            <div className="mb-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Return Format</h4>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">{selected.returns}</pre>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Examples</h4>
              <div className="space-y-1">
                {selected.examples.map((ex, i) => (
                  <pre key={i} className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs font-mono text-emerald-300 overflow-x-auto">await {ex}</pre>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
