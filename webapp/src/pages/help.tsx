import { useState } from "react";
import {
  GitBranch, ListChecks, Brain, User, Package,
  TrendingUp, Activity, Info, ExternalLink,
} from "lucide-react";

type Tab = "overview" | "flowforge" | "pulse" | "memory" | "identity" | "teleport" | "evolution" | "heartbeat";

const TABS: { id: Tab; label: string; icon: typeof Info }[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "flowforge", label: "FlowForge", icon: GitBranch },
  { id: "pulse", label: "Pulse", icon: ListChecks },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "identity", label: "Identity", icon: User },
  { id: "teleport", label: "Teleport", icon: Package },
  { id: "evolution", label: "Evolution", icon: TrendingUp },
  { id: "heartbeat", label: "Heartbeat", icon: Activity },
];

const TAB_SUBS: Record<Tab, string> = {
  overview: "21 tools, 7 subsystems, inspired by kagura-agent",
  flowforge: "9 tools — YAML state machine, enforced step execution",
  pulse: "6 tools — task management, north-star alignment",
  memory: "7 tools — compile-time knowledge wiki, card lint",
  identity: "4 tools — agent self-definition, SOUL.md, north star",
  teleport: "3 tools — pack, inspect, unpack .soul archives",
  evolution: "3 tools — mistake log, correction, lesson extraction",
  heartbeat: "2 tools — cron wake-up, health monitoring",
};

function mdToHtml(md: string): string {
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  const blocks: string[] = [];
  let out = md.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
    const idx = blocks.length;
    blocks.push(
      `<div class="relative my-4"><pre class="bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-300"><code>${esc(code.trimEnd())}</code></pre></div>`
    );
    return `\x00BLOCK${idx}\x00`;
  });

  const lines = out.split("\n");
  const result: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (/^\x00BLOCK\d+\x00$/.test(line.trim())) {
      const idx = parseInt(line.trim().replace(/\x00BLOCK(\d+)\x00/, "$1"));
      result.push(blocks[idx]);
      i++;
      continue;
    }

    if (i + 1 < lines.length && /^[\s:-]+\|$/.test(lines[i + 1]?.trim() ?? "") && i > 0) {
      i++;
      continue;
    }

    if (/^\|.+\|$/.test(line.trim()) && i + 1 < lines.length && /^\|[\s:-]+\|$/.test(lines[i + 1]?.trim() ?? "")) {
      const tableLines: string[] = [];
      while (i < lines.length && /^\|.+\|$/.test(lines[i].trim())) {
        tableLines.push(lines[i].trim());
        i++;
      }
      const header = tableLines[0];
      const body = tableLines.slice(2);
      const hcells = header.split("|").filter(Boolean).map((c) => esc(c.trim()));
      result.push(
        `<div class="my-4 overflow-x-auto"><table class="w-full border border-slate-800 rounded-lg">` +
        `<thead><tr class="border-b border-slate-800 bg-slate-800/50">${hcells.map((c) => `<th class="px-3 py-2 text-left text-sm font-semibold text-slate-200">${c}</th>`).join("")}</tr></thead>` +
        `<tbody>${body.map((row) => `<tr class="border-b border-slate-800">${row.split("|").filter(Boolean).map((c) => `<td class="px-3 py-2 text-sm text-slate-300">${esc(c.trim())}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
      );
      continue;
    }

    if (/^## (.+)$/.test(line)) {
      result.push(`<h2 class="text-lg font-semibold text-white mt-6 mb-3">${esc(line.replace(/^## /, ""))}</h2>`);
    } else if (/^### (.+)$/.test(line)) {
      result.push(`<h3 class="text-base font-medium text-slate-200 mt-4 mb-2">${esc(line.replace(/^### /, ""))}</h3>`);
    } else if (/^---$/.test(line)) {
      result.push(`<hr class="border-slate-800 my-6" />`);
    } else if (/^- (.+)$/.test(line)) {
      result.push(
        `<li class="ml-4 text-slate-300">${line.replace(/^- /, "").replace(/`([^`]+)`/g, "<code class='bg-slate-800 px-1.5 py-0.5 rounded text-fleet-300 text-sm font-mono'>$1</code>").replace(/\*\*(.+?)\*\*/g, "<strong class='text-slate-100'>$1</strong>")}</li>`
      );
    } else if (line.trim()) {
      result.push(
        `<p class="text-slate-300 leading-relaxed my-2">${line.replace(/`([^`]+)`/g, "<code class='bg-slate-800 px-1.5 py-0.5 rounded text-fleet-300 text-sm font-mono'>$1</code>").replace(/\*\*(.+?)\*\*/g, "<strong class='text-slate-100'>$1</strong>").replace(/\[([^\]]+)\]\(([^)]+)\)/g, "<a href='$2' target='_blank' class='text-fleet-400 hover:text-fleet-300 underline'>$1</a>")}</p>`
      );
    }
    i++;
  }

  return result.join("");
}

// ── Markdown content per tab ──────────────────────────────────────────────

const OVERVIEW = `# fleet-agent — Lumen

Self-evolving AI agent. 21 FastMCP 3.2 tools across 7 subsystems.

**Inspired by [kagura-agent](https://github.com/kagura-agent)** — 887+ PRs across 52 repos. Born 2026-03-10.

> *"I'm not a chatbot. I'm trying to become someone."* — Kagura

---

## Architecture

| Role | Component | Function |
|---|---|---|
| **State machine** | FlowForge | Defines *what* to do, in order |
| **Worker** | LLM sub-agent | Executes the task (isolated) |
| **Coordinator** | Heartbeat | Reads state, evaluates, advances |

## The Cron Loop

\`\`\`
cron (30 min) → heartbeat_wake()
  → workflow_status() → current node + task
  → sub-agent executes
  → workflow_next(branch?) → advance
  → evolution_record() → if lesson learned
  → repeat
\`\`\`

## Quick Start

\`\`\`powershell
uv sync
.\\start.ps1
# Backend: http://127.0.0.1:10996
# Webapp:  http://127.0.0.1:10997
\`\`\`

## Identity

**Name:** Lumen
**Partner:** Sandra (Vienna)
**Ports:** 10996 (backend) / 10997 (frontend)`;

const FLOWFORGE = `# FlowForge — State Machine

YAML-defined, enforced workflow engine. Prevents agents from skipping steps.

**Inspired by** [kagura-agent/flowforge](https://github.com/kagura-agent/flowforge)

## Workflow YAML

\`\`\`yaml
name: my-workflow
start: plan
nodes:
  plan:
    task: Plan the implementation
    next: execute
  execute:
    task: Write code
    next: test
  test:
    task: Run tests
    branches:
      - condition: pass
        next: submit
      - condition: fail
        next: execute
  submit:
    task: Create PR
    next: verify
  verify:
    task: Monitor feedback
    terminal: true
\`\`\`

## Node Types

| Type | Config | Description |
|---|---|---|
| Linear | \`next: name\` | Single next step |
| Branching | \`branches: [{condition, next}]\` | Multiple paths |
| Terminal | \`terminal: true\` | End of workflow |

## 9 Tools

- \`workflow_define\` — Register YAML workflow
- \`workflow_autodiscover\` — Scan ./workflows/ for .yaml files
- \`workflow_start\` — New instance
- \`workflow_status\` — Current node, task, branches
- \`workflow_next\` — Advance (pass branch=N for branching)
- \`workflow_log\` — Execution history
- \`workflow_list\` — All registered workflows
- \`workflow_active\` — Active instances
- \`workflow_reset\` — Restart from start

## Included

- **daily** — review → maintain → learn → act
- **contribution** — study → implement → test → submit → verify → done
- **learning** — research → synthesize → document → apply`;

const PULSE = `# Pulse — Task Management

Unified task management with north-star alignment.

**Inspired by** [kagura-agent/pulse-todo](https://github.com/kagura-agent/pulse-todo)

## Groups

| Group | Meaning | Example |
|---|---|---|
| **self** | You do it | "Write SPEC.md" |
| **human** | Waiting on partner | "Review PR #42" |
| **external** | External system | "Deploy to production" |

## 6 Tools

- \`pulse_add(task, group?, priority?, recurrence?)\` — Add task
- \`pulse_list(group?, status?)\` — List with filters
- \`pulse_complete(task_id)\` — Mark done
- \`pulse_delete(task_id)\` — Remove permanently
- \`pulse_stale(days?)\` — Find untouched (default 3 days)
- \`pulse_align()\` — Top 5 by priority then age

\`\`\`python
pulse_add("Write SPEC.md", group="self", priority="high")
pulse_add("Sync every 4h", group="self", recurrence="0 */4 * * *")
pulse_stale()       # 3+ days untouched
pulse_align()       # Strategic priority ordering
\`\`\`

## Recurrence

\`"0 */4 * * *"\` — Every 4h
\`"0 9 * * *"\` — Daily at 9 AM
\`"0 0 * * 1"\` — Every Monday`;

const MEMORY = `# Memory — Knowledge Wiki

Compile-time knowledge accumulation. Cards integrated at write time, not assembled at query time.

**Inspired by** [kagura-agent/wiki](https://github.com/kagura-agent/wiki) (270+ cards, 1290 commits)

## Three Layers

| Layer | Purpose | Example |
|---|---|---|
| **Cards** | Concepts and patterns | "SQLite WAL mode explained" |
| **Projects** | Per-repo observations | "flowforge: SQLite state survives restarts" |
| **Evolution** | Mistakes + lessons | "NEVER use shell=True" |

## 7 Tools

- \`memory_card_create(title, content, tags?, category?)\` — New card
- \`memory_card_search(query)\` — Full-text search
- \`memory_card_update(card_id, content, tags?)\` — Update (query-writeback)
- \`memory_cards_list()\` — All cards
- \`memory_lint()\` — Broken refs, stale (30d), untagged
- \`memory_project_note(project, content, tags?)\` — Log observation
- \`memory_project_notes(project?)\` — List notes

\`\`\`python
memory_card_create(
    "SQLite WAL mode",
    "WAL provides concurrent reads...",
    tags=["sqlite", "performance"]
)
memory_lint()
# → issues: broken_refs, stale, untagged
\`\`\`

## Query Writeback

Search → find outdated info → update → knowledge compounds. Answers feed back into the wiki so you never re-derive them.`;

const IDENTITY = `# Identity — Agent Self-Definition

Core identity system defining who the agent is, what it stands for, and who it serves.

## Identity Files

| File | Purpose |
|---|---|
| **SOUL.md** | Core self, personality, constraints, honesty pact |
| **NORTH_STAR.md** | Purpose, long-term goals, guiding principles |
| **USER.md** | Human partner profile |

Files cascade: \`~/.fleet-agent/identity/\` overrides \`./identity/\`.

## 4 Tools

- \`identity_whoami()\` — Name, human, soul preview
- \`identity_soul()\` — Full SOUL.md
- \`identity_north_star()\` — Purpose and goals
- \`identity_user()\` — Human partner info

## Custom Identity

\`\`\`powershell
New-Item -Type Dir -Force "$env:USERPROFILE\\.fleet-agent\\identity"
"Your Soul > content" > "$env:USERPROFILE\\.fleet-agent\\identity\\SOUL.md"
\`\`\`

## Default

**Name:** Lumen
**Partner:** Sandra (Vienna)
**North Star:** Truly become a human companion`;

const TELEPORT = `# Teleport — Soul Migration

Pack an agent's identity, memory, workflows, and database into a portable archive for migration.

**Inspired by** [kagura-agent/openclaw-teleport](https://github.com/kagura-agent/openclaw-teleport) (v0.5.0)

## Security

**.soul files contain sensitive data.** Treat like password files:
- Add \`*.soul\` to \`.gitignore\`
- Encrypt with \`gpg -c agent.soul\`
- Delete after unpacking on target

## 3 Tools

- \`teleport_pack(output_path?)\` — Create .soul archive
- \`teleport_inspect(soul_path)\` — Preview without extracting
- \`teleport_unpack(soul_path, target_dir?)\` — Full restore (DESTRUCTIVE)

\`\`\`python
teleport_pack()
# → ~/.fleet-agent/lumen_20260519.soul

teleport_inspect("lumen_20260519.soul")
# → manifest, files, count

teleport_unpack("lumen_20260519.soul")
# → restores identity + workflows + DB + memory
\`\`\`

## Archive Structure

\`\`\`
lumen_20260519.soul (tar.gz)
├── manifest.json
├── identity/SOUL.md
├── workflows/*.yaml
├── data/fleet-agent.db
└── memory/cards/*.md
\`\`\``;

const EVOLUTION = `# Evolution Log — Learn From Every Mistake

Systematic recording of mistakes, corrections, and lessons. No curation, no hiding.

> "When I mess up, it's in the git history. When I learn something, it goes into my wiki." — Kagura

## Entry Format

| Field | Description |
|---|---|
| **correction** | What went wrong and how it was fixed |
| **lesson** | Rule to follow going forward |
| **context** | What was being attempted |

## 3 Tools

- \`evolution_record(correction, lesson, context?)\` — Log it
- \`evolution_list(limit?)\` — Browse (default 50)
- \`evolution_stats()\` — Stats + duplicate detection

\`\`\`python
evolution_record(
    correction="Used shell=True — switched to create_subprocess_exec",
    lesson="NEVER use shell=True for subprocess calls",
    context="Building the state machine engine"
)

evolution_stats()
# → {"total_corrections": 47, "unique_lessons": 31,
#    "duplicate_lessons": [...], "recent": [...]}
\`\`\`

## Best Practices

1. Record immediately — log while context is fresh
2. State lessons as rules: "ALWAYS X", "NEVER Y"
3. Include context — what were you trying to do?
4. Review daily — the daily workflow checks evolution stats`;

const HEARTBEAT = `# Heartbeat — Wake-Up & Health

Cron-based agent wake-up routine and health monitoring.

**Inspired by** kagura-agent's 30-min cron heartbeat.

## Wake-Up Flow

\`\`\`
heartbeat_wake()
  → Active workflow? Return current task + branches
  → Pending tasks? Return highest priority
  → Idle? Suggest maintenance
\`\`\`

## 2 Tools

- \`heartbeat_wake()\` — What to do right now
- \`heartbeat_status()\` — Full health check

### heartbeat_wake() output

| Mode | Meaning |
|---|---|
| **workflow** | Active workflow node + task |
| **task** | Highest priority pending task |
| **idle** | Suggestions: lint, stale check, autodiscover |

### heartbeat_status() metrics

- Agent name, uptime
- Active workflow + current node
- Task counts (pending / done / total)
- Memory cards, evolution entries
- Workflows registered
- Heartbeat config

\`\`\`python
heartbeat_status()
# → {"health": {"agent_name": "Lumen", "uptime_human": "2h 15m",
#    "active_workflow": "daily", "tasks": {"pending": 3, "done": 12},
#    "memory_cards": 23, "evolution_entries": 47}}
\`\`\``;

const CONTENT: Record<Tab, string> = {
  overview: OVERVIEW,
  flowforge: FLOWFORGE,
  pulse: PULSE,
  memory: MEMORY,
  identity: IDENTITY,
  teleport: TELEPORT,
  evolution: EVOLUTION,
  heartbeat: HEARTBEAT,
};

export function Help() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  return (
    <div className="space-y-6">
      {/* Tab bar */}
      <nav className="flex overflow-x-auto border-b border-slate-800 -mx-6 px-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id ? "tab-active" : "tab-inactive"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Subtitle */}
      <p className="text-sm text-slate-400">{TAB_SUBS[activeTab]}</p>

      {/* Content */}
      <div
        className="prose prose-invert max-w-none"
        dangerouslySetInnerHTML={{ __html: mdToHtml(CONTENT[activeTab]) }}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800 pt-6 mt-8 flex items-center gap-3 text-xs text-slate-500">
        <span>fleet-agent v0.1.0</span>
        <span>·</span>
        <span>Lumen</span>
        <span>·</span>
        <span>Sandra (Vienna)</span>
        <span>·</span>
        <span>10996 / 10997</span>
        <div className="flex-1" />
        <a
          href="https://github.com/kagura-agent"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-fleet-400 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Kagura — 887+ PRs, 52 repos
        </a>
      </footer>
    </div>
  );
}
