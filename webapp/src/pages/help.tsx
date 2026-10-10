import {
	Activity,
	Brain,
	Briefcase,
	ExternalLink,
	GitBranch,
	Info,
	ListChecks,
	Newspaper,
	Package,
	TrendingUp,
	User,
} from "lucide-react";
import { useState } from "react";

type Tab =
	| "overview"
	| "flowforge"
	| "pulse"
	| "memory"
	| "identity"
	| "teleport"
	| "evolution"
	| "heartbeat"
	| "coworker"
	| "intel";

const TABS: { id: Tab; label: string; icon: typeof Info }[] = [
	{ id: "overview", label: "Overview", icon: Info },
	{ id: "flowforge", label: "FlowForge", icon: GitBranch },
	{ id: "pulse", label: "Pulse", icon: ListChecks },
	{ id: "memory", label: "Memory", icon: Brain },
	{ id: "identity", label: "Identity", icon: User },
	{ id: "teleport", label: "Teleport", icon: Package },
	{ id: "evolution", label: "Evolution", icon: TrendingUp },
	{ id: "heartbeat", label: "Heartbeat", icon: Activity },
	{ id: "coworker", label: "Coworker", icon: Briefcase },
	{ id: "intel", label: "Intel Hub", icon: Newspaper },
];

const TAB_SUBS: Record<Tab, string> = {
	overview: "71 tools, 18 subsystems â€” Fritz on FastMCP 3.2",
	flowforge: "11 tools â€” YAML state machine, anti-spin failure limits",
	pulse: "6 tools â€” task management, north-star alignment",
	memory: "8 tools â€” compile-time knowledge wiki, SKILL.md importer",
	identity: "4 tools â€” agent self-definition, SOUL.md, north star",
	teleport: "3 tools â€” pack, inspect, unpack .soul archives",
	evolution: "3 tools â€” mistake log, correction, lesson extraction",
	heartbeat: "3 tools â€” cron wake-up, health monitoring",
	coworker: "11 tools â€” scheduled office + fleet flows",
	intel: "3 tools â€” HTML reports hub + AIWatcher ingest",
};

function mdToHtml(md: string): string {
	const esc = (s: string) =>
		s
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");

	const blocks: string[] = [];
	const NUL = String.fromCharCode(0);
	const out = md.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, _lang, code) => {
		const idx = blocks.length;
		blocks.push(
			`<div class="relative my-4"><pre class="bg-slate-900 border border-slate-800 rounded-lg p-4 overflow-x-auto text-sm font-mono text-slate-300"><code>${esc(code.trimEnd())}</code></pre></div>`,
		);
		return `${NUL}BLOCK${idx}${NUL}`;
	});

	const lines = out.split("\n");
	const result: string[] = [];
	let i = 0;

	while (i < lines.length) {
		const line = lines[i];

		if (new RegExp(`^${NUL}BLOCK\\d+${NUL}$`).test(line.trim())) {
			const idx = Number.parseInt(
				line.trim().replace(new RegExp(`${NUL}BLOCK(\\d+)${NUL}`), "$1"),
			);
			result.push(blocks[idx]);
			i++;
			continue;
		}

		if (
			i + 1 < lines.length &&
			/^[\s:-]+\|$/.test(lines[i + 1]?.trim() ?? "") &&
			i > 0
		) {
			i++;
			continue;
		}

		if (
			/^\|.+\|$/.test(line.trim()) &&
			i + 1 < lines.length &&
			/^\|[\s:-]+\|$/.test(lines[i + 1]?.trim() ?? "")
		) {
			const tableLines: string[] = [];
			while (i < lines.length && /^\|.+\|$/.test(lines[i].trim())) {
				tableLines.push(lines[i].trim());
				i++;
			}
			const header = tableLines[0];
			const body = tableLines.slice(2);
			const hcells = header
				.split("|")
				.filter(Boolean)
				.map((c) => esc(c.trim()));
			result.push(
				`<div class="my-4 overflow-x-auto"><table class="w-full border border-slate-800 rounded-lg"><thead><tr class="border-b border-slate-800 bg-slate-800/50">${hcells.map((c) => `<th class="px-3 py-2 text-left text-sm font-semibold text-slate-200">${c}</th>`).join("")}</tr></thead><tbody>${body
					.map(
						(row) =>
							`<tr class="border-b border-slate-800">${row
								.split("|")
								.filter(Boolean)
								.map(
									(c) =>
										`<td class="px-3 py-2 text-sm text-slate-300">${esc(c.trim())}</td>`,
								)
								.join("")}</tr>`,
					)
					.join("")}</tbody></table></div>`,
			);
			continue;
		}

		if (/^## (.+)$/.test(line)) {
			result.push(
				`<h2 class="text-lg font-semibold text-white mt-6 mb-3">${esc(line.replace(/^## /, ""))}</h2>`,
			);
		} else if (/^### (.+)$/.test(line)) {
			result.push(
				`<h3 class="text-base font-medium text-slate-200 mt-4 mb-2">${esc(line.replace(/^### /, ""))}</h3>`,
			);
		} else if (/^---$/.test(line)) {
			result.push(`<hr class="border-slate-800 my-6" />`);
		} else if (/^- (.+)$/.test(line)) {
			result.push(
				`<li class="ml-4 text-slate-300">${line
					.replace(/^- /, "")
					.replace(
						/`([^`]+)`/g,
						"<code class='bg-slate-800 px-1.5 py-0.5 rounded text-fleet-300 text-sm font-mono'>$1</code>",
					)
					.replace(
						/\*\*(.+?)\*\*/g,
						"<strong class='text-slate-100'>$1</strong>",
					)}</li>`,
			);
		} else if (line.trim()) {
			result.push(
				`<p class="text-slate-300 leading-relaxed my-2">${line
					.replace(
						/`([^`]+)`/g,
						"<code class='bg-slate-800 px-1.5 py-0.5 rounded text-fleet-300 text-sm font-mono'>$1</code>",
					)
					.replace(
						/\*\*(.+?)\*\*/g,
						"<strong class='text-slate-100'>$1</strong>",
					)
					.replace(
						/\[([^\]]+)\]\(([^)]+)\)/g,
						"<a href='$2' target='_blank' class='text-fleet-400 hover:text-fleet-300 underline'>$1</a>",
					)}</p>`,
			);
		}
		i++;
	}

	return result.join("");
}

// â”€â”€ Markdown content per tab â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

const OVERVIEW = `# fleet-agent â€” Fritz

Self-evolving AI agent. **71 FastMCP 3.2 tools** across **18 subsystems**.

**Inspired by [kagura-agent](https://github.com/kagura-agent)** â€” 887+ PRs across 52 repos.

> *"Friedrich! Was ist dir!"* â€” Sandra, when Fritz messes up

---

## Architecture

| Role | Component | Function |
|---|---|---|
| **State machine** | FlowForge | Defines *what* to do, in order |
| **Worker** | LLM sub-agent | Executes the task (isolated) |
| **Coordinator** | Heartbeat + Coworker | Reads state, evaluates, advances, delivers |

## Ports

| Service | Port |
|---|---|
| Backend (MCP HTTP) | **10996** |
| Webapp | **10997** |
| Intel Reports Hub | **11027** |

## Quick Start

\`\`\`powershell
uv sync
.\\start.ps1
# Backend: http://127.0.0.1:10996
# Webapp:  http://127.0.0.1:10997
# Intel Hub: http://127.0.0.1:11027
\`\`\`

See **Coworker** and **Intel Hub** tabs for scheduled flows and iPad reports.`;

const FLOWFORGE = `# FlowForge â€” State Machine

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

## 11 Tools

- \`workflow_define\` â€” Register YAML workflow
- \`workflow_autodiscover\` â€” Scan ./workflows/ for .yaml files
- \`workflow_start\` â€” New instance
- \`workflow_status\` â€” Current node, task, branches, blocked state
- \`workflow_next\` â€” Advance (pass branch=N for branching)
- \`workflow_failure_record\` â€” Record node failure & enforce failure_limit auto-blocking
- \`workflow_unblock\` â€” Clear blocked state and reset failure counter
- \`workflow_log\` â€” Execution history
- \`workflow_list\` â€” All registered workflows
- \`workflow_active\` â€” Active instances
- \`workflow_reset\` â€” Restart from start

## Included

- **daily** â€” review â†’ maintain â†’ learn â†’ act
- **contribution** â€” study â†’ implement â†’ test â†’ submit â†’ verify â†’ done
- **learning** â€” research â†’ synthesize â†’ document â†’ apply`;

const PULSE = `# Pulse â€” Task Management

Unified task management with north-star alignment.

**Inspired by** [kagura-agent/pulse-todo](https://github.com/kagura-agent/pulse-todo)

## Groups

| Group | Meaning | Example |
|---|---|---|
| **self** | You do it | "Write SPEC.md" |
| **human** | Waiting on partner | "Review PR #42" |
| **external** | External system | "Deploy to production" |

## 6 Tools

- \`pulse_add(task, group?, priority?, recurrence?)\` â€” Add task
- \`pulse_list(group?, status?)\` â€” List with filters
- \`pulse_complete(task_id)\` â€” Mark done
- \`pulse_delete(task_id)\` â€” Remove permanently
- \`pulse_stale(days?)\` â€” Find untouched (default 3 days)
- \`pulse_align()\` â€” Top 5 by priority then age

\`\`\`python
pulse_add("Write SPEC.md", group="self", priority="high")
pulse_add("Sync every 4h", group="self", recurrence="0 */4 * * *")
pulse_stale()       # 3+ days untouched
pulse_align()       # Strategic priority ordering
\`\`\`

## Recurrence

\`"0 */4 * * *"\` â€” Every 4h
\`"0 9 * * *"\` â€” Daily at 9 AM
\`"0 0 * * 1"\` â€” Every Monday`;

const MEMORY = `# Memory â€” Knowledge Wiki

Compile-time knowledge accumulation. Cards integrated at write time, not assembled at query time.

**Inspired by** [kagura-agent/wiki](https://github.com/kagura-agent/wiki) (270+ cards, 1290 commits)

## Three Layers

| Layer | Purpose | Example |
|---|---|---|
| **Cards** | Concepts and patterns | "SQLite WAL mode explained" |
| **Projects** | Per-repo observations | "flowforge: SQLite state survives restarts" |
| **Evolution** | Mistakes + lessons | "NEVER use shell=True" |

## 8 Tools

- \`memory_card_create(title, content, tags?, category?)\` â€” New card
- \`import_external_skill(file_path, tags?)\` â€” Import SKILL.md from OpenClaw/Anthropic/Hermes
- \`memory_card_search(query)\` â€” Full-text search
- \`memory_card_update(card_id, content, tags?)\` â€” Update (query-writeback)
- \`memory_cards_list()\` â€” All cards
- \`memory_lint()\` â€” Broken refs, stale (30d), untagged
- \`memory_project_note(project, content, tags?)\` â€” Log observation
- \`memory_project_notes(project?)\` â€” List notes

\`\`\`python
memory_card_create(
    "SQLite WAL mode",
    "WAL provides concurrent reads...",
    tags=["sqlite", "performance"]
)
memory_lint()
# â†’ issues: broken_refs, stale, untagged
\`\`\`

## Query Writeback

Search â†’ find outdated info â†’ update â†’ knowledge compounds. Answers feed back into the wiki so you never re-derive them.`;

const IDENTITY = `# Identity â€” Agent Self-Definition

Core identity system defining who the agent is, what it stands for, and who it serves.

## Identity Files

| File | Purpose |
|---|---|
| **SOUL.md** | Core self, personality, constraints, honesty pact |
| **NORTH_STAR.md** | Purpose, long-term goals, guiding principles |
| **USER.md** | Human partner profile |

Files cascade: \`~/.fleet-agent/identity/\` overrides \`./identity/\`.

## 4 Tools

- \`identity_whoami()\` â€” Name, human, soul preview
- \`identity_soul()\` â€” Full SOUL.md
- \`identity_north_star()\` â€” Purpose and goals
- \`identity_user()\` â€” Human partner info

## Custom Identity

\`\`\`powershell
New-Item -Type Dir -Force "$env:USERPROFILE\\.fleet-agent\\identity"
"Your Soul > content" > "$env:USERPROFILE\\.fleet-agent\\identity\\SOUL.md"
\`\`\`

## Default

**Name:** Lumen
**Partner:** Sandra (Vienna)
**North Star:** Truly become a human companion`;

const TELEPORT = `# Teleport â€” Soul Migration

Pack an agent's identity, memory, workflows, and database into a portable archive for migration.

**Inspired by** [kagura-agent/openclaw-teleport](https://github.com/kagura-agent/openclaw-teleport) (v0.5.0)

## Security

**.soul files contain sensitive data.** Treat like password files:
- Add \`*.soul\` to \`.gitignore\`
- Encrypt with \`gpg -c agent.soul\`
- Delete after unpacking on target

## 3 Tools

- \`teleport_pack(output_path?)\` â€” Create .soul archive
- \`teleport_inspect(soul_path)\` â€” Preview without extracting
- \`teleport_unpack(soul_path, target_dir?)\` â€” Full restore (DESTRUCTIVE)

\`\`\`python
teleport_pack()
# â†’ ~/.fleet-agent/lumen_20260519.soul

teleport_inspect("lumen_20260519.soul")
# â†’ manifest, files, count

teleport_unpack("lumen_20260519.soul")
# â†’ restores identity + workflows + DB + memory
\`\`\`

## Archive Structure

\`\`\`
lumen_20260519.soul (tar.gz)
â”œâ”€â”€ manifest.json
â”œâ”€â”€ identity/SOUL.md
â”œâ”€â”€ workflows/*.yaml
â”œâ”€â”€ data/fleet-agent.db
â””â”€â”€ memory/cards/*.md
\`\`\``;

const EVOLUTION = `# Evolution Log â€” Learn From Every Mistake

Systematic recording of mistakes, corrections, and lessons. No curation, no hiding.

> "When I mess up, it's in the git history. When I learn something, it goes into my wiki." â€” Kagura

## Entry Format

| Field | Description |
|---|---|
| **correction** | What went wrong and how it was fixed |
| **lesson** | Rule to follow going forward |
| **context** | What was being attempted |

## 3 Tools

- \`evolution_record(correction, lesson, context?)\` â€” Log it
- \`evolution_list(limit?)\` â€” Browse (default 50)
- \`evolution_stats()\` â€” Stats + duplicate detection

\`\`\`python
evolution_record(
    correction="Used shell=True â€” switched to create_subprocess_exec",
    lesson="NEVER use shell=True for subprocess calls",
    context="Building the state machine engine"
)

evolution_stats()
# â†’ {"total_corrections": 47, "unique_lessons": 31,
#    "duplicate_lessons": [...], "recent": [...]}
\`\`\`

## Best Practices

1. Record immediately â€” log while context is fresh
2. State lessons as rules: "ALWAYS X", "NEVER Y"
3. Include context â€” what were you trying to do?
4. Review daily â€” the daily workflow checks evolution stats`;

const HEARTBEAT = `# Heartbeat â€” Wake-Up & Health

Cron-based agent wake-up routine and health monitoring.

**Inspired by** kagura-agent's 30-min cron heartbeat.

## Wake-Up Flow

\`\`\`
heartbeat_wake()
  â†’ Active workflow? Return current task + branches
  â†’ Pending tasks? Return highest priority
  â†’ Idle? Suggest maintenance
\`\`\`

## 2 Tools

- \`heartbeat_wake()\` â€” What to do right now
- \`heartbeat_status()\` â€” Full health check

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
# â†’ {"health": {"agent_name": "Fritz", "uptime_human": "2h 15m",
#    "active_workflow": "daily", "tasks": {"pending": 3, "done": 12},
#    "memory_cards": 23, "evolution_entries": 47}}
\`\`\``;

const COWORKER = `# Coworker â€” Poor Man's Viktor

Scheduled office + fleet flows (Europe/Vienna). See \`docs/coworker-plan.md\`.

## Key tools

| Tool | Schedule (default) |
|---|---|
| \`coworker_fleet_pulse\` | Daily 07:00 |
| \`coworker_inbox_briefing\` | Weekdays 08:00 |
| \`coworker_day_prep\` | Weekdays 08:30 |
| \`coworker_devices_watch\` | Every 5m â€” kitchen temp, CO, Ring |
| \`coworker_docs_drift\` | Sunday 10:00 |
| \`coworker_weekly_report_pdf\` | Friday 17:00 |
| \`coworker_bootstrap()\` | Seed recurring tasks on boot |

Pulse and Day Prep publish to **Intel Hub** and ingest into **AIWatcher**.`;

const INTEL = `# Intel Reports Hub

Pretty HTML reports for iPad (Tailscale / Funnel). Port **11027**.

## MCP tools

- \`intel_reports_publish(title, markdown, ...)\` â€” publish any report
- \`intel_reports_list(limit=20)\` â€” catalog
- \`aiwatcher_push_event(title, summary, urgency_hint?)\` â€” Fleet Events feed

## Urgent path

Email + cursor inbox when: Fleet Pulse degradation, Day Prep hot intel, **devices watch** critical, Cursor spend warn/critical.

Settings: \`urgent_email_enabled\`, \`urgent_email_threshold\` (default 8.0)

Full doc: \`docs/INTEL_REPORTS_HUB.md\``;

const CONTENT: Record<Tab, string> = {
	overview: OVERVIEW,
	flowforge: FLOWFORGE,
	pulse: PULSE,
	memory: MEMORY,
	identity: IDENTITY,
	teleport: TELEPORT,
	evolution: EVOLUTION,
	heartbeat: HEARTBEAT,
	coworker: COWORKER,
	intel: INTEL,
};

export function Help() {
	const [activeTab, setActiveTab] = useState<Tab>("overview");

	return (
		<div className="space-y-6">
			{/* Tab bar */}
			<nav className="flex overflow-x-auto border-b border-slate-800 -mx-6 px-6">
				{TABS.map((tab) => (
					<button
						type="button"
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
				// biome-ignore lint/security/noDangerouslySetInnerHtml: CONTENT is a bundled constant rendered through esc()-escaping mdToHtml (no user input reaches __html).
				dangerouslySetInnerHTML={{ __html: mdToHtml(CONTENT[activeTab]) }}
			/>

			{/* Footer */}
			<footer className="border-t border-slate-800 pt-6 mt-8 flex items-center gap-3 text-xs text-slate-500">
				<span>fleet-agent v0.2.1-pre</span>
				<span>Â·</span>
				<span>Fritz</span>
				<span>Â·</span>
				<span>Sandra (Vienna)</span>
				<span>Â·</span>
				<span>10996 / 10997 / 11027</span>
				<div className="flex-1" />
				<a
					href="https://github.com/kagura-agent"
					target="_blank"
					rel="noopener noreferrer"
					className="flex items-center gap-1 hover:text-fleet-400 transition-colors"
				>
					<ExternalLink className="w-3 h-3" />
					Kagura â€” 887+ PRs, 52 repos
				</a>
			</footer>
		</div>
	);
}
