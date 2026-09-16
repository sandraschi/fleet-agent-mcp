import { useEffect, useMemo, useState } from "react";
import { Network } from "lucide-react";
import { API_BASE } from "@/lib/api";

interface Task {
	id: string;
	task: string;
	status: string;
	recurrence?: string;
	updated_at?: string;
}

interface Workflow {
	name: string;
	description?: string;
	registered_at?: string;
}

interface Status {
	success?: boolean;
	health?: {
		tasks?: { pending?: number; done?: number; total?: number };
		memory_cards?: number;
	};
}

function esc(label: string): string {
	return label.replace(/"/g, "'").replace(/\n/g, " ").slice(0, 60);
}

export default function Automaton() {
	const [tasks, setTasks] = useState<Task[]>([]);
	const [workflows, setWorkflows] = useState<Workflow[]>([]);
	const [status, setStatus] = useState<Status | null>(null);
	const [svg, setSvg] = useState("");
	const [err, setErr] = useState<string | null>(null);

	useEffect(() => {
		Promise.all([
			fetch(`${API_BASE}/api/tasks`).then((r) => r.json()),
			fetch(`${API_BASE}/api/workflows`).then((r) => r.json()),
			fetch(`${API_BASE}/api/status`).then((r) => r.json()),
		])
			.then(([t, w, s]) => {
				setTasks(Array.isArray(t) ? t : t.tasks ?? []);
				setWorkflows(Array.isArray(w) ? w : w.workflows ?? []);
				setStatus(s);
			})
			.catch((e) => setErr(e instanceof Error ? e.message : String(e)));
	}, []);

	const diagram = useMemo(() => {
		const recurring = tasks.filter((t) => t.recurrence);
		const lines: string[] = [
			"flowchart TD",
			'  HB["Heartbeat scheduler (60s)"] --> CRON["Recurring task engine"]',
		];
		recurring.forEach((t, i) => {
			const id = `T${i}`;
			const rec = esc(t.recurrence ?? "");
			lines.push(`  CRON --> ${id}["${esc(t.task)} [${rec}]"]`);
		});
		workflows.forEach((w, i) => {
			const id = `W${i}`;
			lines.push(`  CRON -.-> ${id}["workflow: ${esc(w.name)}"]`);
		});
		lines.push('  SCR["Agent scripts"]');
		if (tasks.length) lines.push("  CRON --> SCR");
		lines.push("  SCR --> OUT[\"Actions: tasks, reports, email, voice\"]");
		lines.push("  OUT --> HB");
		return lines.join("\n");
	}, [tasks, workflows]);

	useEffect(() => {
		if (!diagram) return;
		let cancelled = false;
		(async () => {
			try {
				const mermaid = (await import("mermaid")).default;
				mermaid.initialize({
					startOnLoad: false,
					theme: "dark",
					securityLevel: "loose",
					themeVariables: {
						primaryColor: "#18181b",
						primaryTextColor: "#e4e4e7",
						primaryBorderColor: "#f59e0b",
						lineColor: "#52525b",
						secondaryColor: "#27272a",
						tertiaryColor: "#0f0f12",
					},
				});
				const { svg: rendered } = await mermaid.render("automaton-graph", diagram);
				if (!cancelled) setSvg(rendered);
			} catch (e) {
				if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
			}
		})();
		return () => {
			cancelled = true;
		};
	}, [diagram]);

	return (
		<div className="space-y-6 py-4 max-w-5xl">
			<div className="flex items-center gap-4">
				<Network className="text-amber-400 w-8 h-8" />
				<div>
					<h1 className="text-2xl font-bold text-white">Fleet Automaton</h1>
					<p className="text-slate-400 text-sm">
						Heartbeat scheduler, recurring tasks, workflows and scripts - the machinery
						behind Fritz.
					</p>
				</div>
			</div>

			{err && <p className="text-amber-300 text-sm">Error: {err}</p>}

			<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4 overflow-x-auto">
				{svg ? (
					<div dangerouslySetInnerHTML={{ __html: svg }} />
				) : (
					<p className="text-slate-500 text-sm py-8 text-center">Rendering automaton diagram...</p>
				)}
			</div>

			{status && (
				<div className="grid grid-cols-2 md:grid-cols-4 gap-3">
					<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4">
						<p className="text-slate-500 text-xs">Pending tasks</p>
						<p className="text-2xl font-semibold text-white">
							{status.health?.tasks?.pending ?? "?"}
						</p>
					</div>
					<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4">
						<p className="text-slate-500 text-xs">Recurring</p>
						<p className="text-2xl font-semibold text-white">
							{tasks.filter((t) => t.recurrence).length}
						</p>
					</div>
					<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4">
						<p className="text-slate-500 text-xs">Workflows</p>
						<p className="text-2xl font-semibold text-white">{workflows.length}</p>
					</div>
					<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-4">
						<p className="text-slate-500 text-xs">Memory cards</p>
						<p className="text-2xl font-semibold text-white">
							{status.health?.memory_cards ?? "?"}
						</p>
					</div>
				</div>
			)}

			<ScheduleBoard tasks={tasks} />
		</div>
	);
}

const PAGE_SIZE = 15;

function ScheduleBoard({ tasks }: { tasks: Task[] }) {
	const [search, setSearch] = useState("");
	const [statusFilter, setStatusFilter] = useState("all");
	const [sortBy, setSortBy] = useState("task");
	const [page, setPage] = useState(0);

	const recurring = useMemo(() => tasks.filter((t) => t.recurrence), [tasks]);

	const filtered = useMemo(() => {
		let result = recurring;
		if (statusFilter !== "all") result = result.filter((t) => t.status === statusFilter);
		if (search.trim()) {
			const q = search.trim().toLowerCase();
			result = result.filter((t) => t.task.toLowerCase().includes(q));
		}
		const sorted = [...result];
		if (sortBy === "task") sorted.sort((a, b) => a.task.localeCompare(b.task));
		else if (sortBy === "status") sorted.sort((a, b) => a.status.localeCompare(b.status));
		else if (sortBy === "updated") sorted.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
		return sorted;
	}, [recurring, search, statusFilter, sortBy]);

	useEffect(() => { setPage(0); }, [search, statusFilter, sortBy]);

	const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
	const pageItems = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

	return (
		<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
			<div className="flex items-center justify-between mb-3 flex-wrap gap-2">
				<h2 className="text-lg font-semibold text-white">Schedule board</h2>
				<span className="text-xs text-slate-500">{filtered.length} of {recurring.length} recurring</span>
			</div>

			<div className="flex items-center gap-2 flex-wrap mb-3">
				<input
					value={search}
					onChange={(e) => setSearch(e.target.value)}
					placeholder="Search..."
					className="bg-black/40 border border-white/10 rounded-lg px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-amber-500 w-40"
				/>
				<select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="bg-black/40 border border-white/10 text-slate-200 rounded-lg px-2 py-1.5 text-xs">
					<option value="all">All statuses</option>
					<option value="pending">Pending</option>
					<option value="done">Done</option>
					<option value="failed">Failed</option>
				</select>
				<select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="bg-black/40 border border-white/10 text-slate-200 rounded-lg px-2 py-1.5 text-xs">
					<option value="task">Sort: A-Z</option>
					<option value="status">Sort: status</option>
					<option value="updated">Sort: last updated</option>
				</select>
			</div>

			<table className="w-full text-sm">
				<thead>
					<tr className="text-left text-slate-500 text-xs">
						<th className="pb-2">Task</th>
						<th className="pb-2">Recurrence</th>
						<th className="pb-2">Status</th>
						<th className="pb-2">Last updated</th>
					</tr>
				</thead>
				<tbody>
					{pageItems.map((t) => (
						<tr key={t.id} className="border-t border-white/5">
							<td className="py-2 text-slate-200">{t.task}</td>
							<td className="py-2 font-mono text-amber-300 text-xs">{t.recurrence}</td>
							<td className="py-2 text-slate-400">{t.status}</td>
							<td className="py-2 text-slate-500 text-xs">
								{t.updated_at ? t.updated_at.slice(0, 19).replace("T", " ") : "-"}
							</td>
						</tr>
					))}
					{filtered.length === 0 && (
						<tr>
							<td colSpan={4} className="py-4 text-slate-500">
								No recurring tasks match.
							</td>
						</tr>
					)}
				</tbody>
			</table>

			{pageCount > 1 && (
				<div className="flex items-center justify-end gap-2 mt-3 text-xs text-slate-400">
					<button
						onClick={() => setPage((p) => Math.max(0, p - 1))}
						disabled={page === 0}
						className="px-2 py-1 rounded bg-black/40 border border-white/10 disabled:opacity-30"
					>
						Prev
					</button>
					<span>Page {page + 1} / {pageCount}</span>
					<button
						onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
						disabled={page >= pageCount - 1}
						className="px-2 py-1 rounded bg-black/40 border border-white/10 disabled:opacity-30"
					>
						Next
					</button>
				</div>
			)}
		</div>
	);
}
