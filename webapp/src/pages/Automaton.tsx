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
	status?: string;
	tool_count?: number;
	providers?: { tasks_pending?: number; memory_cards?: number };
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
							{status.providers?.tasks_pending ?? "?"}
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
							{status.providers?.memory_cards ?? "?"}
						</p>
					</div>
				</div>
			)}

			<div className="rounded-2xl border border-white/10 bg-[#0f0f12]/80 p-5">
				<h2 className="text-lg font-semibold text-white mb-3">Schedule board</h2>
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
						{tasks
							.filter((t) => t.recurrence)
							.map((t) => (
								<tr key={t.id} className="border-t border-white/5">
									<td className="py-2 text-slate-200">{t.task}</td>
									<td className="py-2 font-mono text-amber-300 text-xs">{t.recurrence}</td>
									<td className="py-2 text-slate-400">{t.status}</td>
									<td className="py-2 text-slate-500 text-xs">
										{t.updated_at ? t.updated_at.slice(0, 19).replace("T", " ") : "-"}
									</td>
								</tr>
							))}
						{tasks.filter((t) => t.recurrence).length === 0 && (
							<tr>
								<td colSpan={4} className="py-4 text-slate-500">
									No recurring tasks.
								</td>
							</tr>
						)}
					</tbody>
				</table>
			</div>
		</div>
	);
}
