import {
	AlertCircle,
	Calendar,
	Check,
	ChevronDown,
	ChevronRight,
	Clock,
	ListChecks,
	Play,
	RefreshCw,
	Trash2,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Task {
	id: string;
	task: string;
	group_name?: string;
	priority: string;
	status: string;
	recurrence?: string;
	created_at: string;
	description?: string;
	metadata?: Record<string, unknown>;
	script_id?: string;
	script_name?: string;
}

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DOW_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DOW_SHORT = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];
const DOM = Array.from({ length: 31 }, (_, i) => i + 1);

interface ParsedSchedule {
	type: string;
	label: string;
	detail: string;
	raw: string;
}

function parseRecurrence(rec: string | undefined): ParsedSchedule | null {
	if (!rec) return null;
	const r = rec.trim();

	const wd = r.match(/^wd:(\d{1,2}):(\d{2})$/i);
	if (wd) {
		const h = parseInt(wd[1]);
		const m = parseInt(wd[2]);
		return { type: "weekdays", label: "Mon-Fri", detail: `Weekdays at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	const named = r.match(/^(mon|tue|wed|thu|fri|sat|sun):(\d{1,2}):(\d{2})$/i);
	if (named) {
		const idx = DOW_SHORT.indexOf(named[1].toLowerCase());
		const h = parseInt(named[2]);
		const m = parseInt(named[3]);
		return { type: "weekly", label: DOW_LABELS[idx], detail: `Every ${DOW_FULL[idx]} at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	const dom = r.match(/^d(\d{1,2}):(\d{1,2}):(\d{2})$/i);
	if (dom) {
		const day = parseInt(dom[1]);
		const h = parseInt(dom[2]);
		const m = parseInt(dom[3]);
		return { type: "monthly", label: `Day ${day}`, detail: `${getOrdinal(day)} of month at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	const daily = r.match(/^(\d{1,2}):(\d{2})$/);
	if (daily) {
		const h = parseInt(daily[1]);
		const m = parseInt(daily[2]);
		return { type: "daily", label: "Daily", detail: `Every day at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	const cronDaily = r.match(/^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$/);
	if (cronDaily) {
		const h = parseInt(cronDaily[2]);
		const m = parseInt(cronDaily[1]);
		return { type: "daily", label: "Daily", detail: `Every day at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	const cronMonth = r.match(/^(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+\*\s+\*$/);
	if (cronMonth) {
		const day = parseInt(cronMonth[3]);
		const h = parseInt(cronMonth[2]);
		const m = parseInt(cronMonth[1]);
		return { type: "monthly", label: `Day ${day}`, detail: `${getOrdinal(day)} of month at ${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`, raw: r };
	}

	if (r.endsWith("h") && r.slice(0, -1).match(/^\d+$/)) {
		const n = parseInt(r.slice(0, -1));
		return { type: "interval", label: `Every ${n}h`, detail: `Every ${n} hour${n > 1 ? "s" : ""}`, raw: r };
	}

	if (r.endsWith("m") && r.slice(0, -1).match(/^\d+$/)) {
		const n = parseInt(r.slice(0, -1));
		return { type: "interval", label: `Every ${n}m`, detail: `Every ${n} minute${n > 1 ? "s" : ""}`, raw: r };
	}

	if (r.match(/^\d+$/)) {
		const s = parseInt(r);
		if (s < 3600) return { type: "interval", label: `Every ${s}s`, detail: `Every ${s} seconds`, raw: r };
		const h = Math.floor(s / 3600);
		const m = Math.floor((s % 3600) / 60);
		return { type: "interval", label: `Every ${h}h ${m}m`, detail: `Every ${h} hour${h > 1 ? "s" : ""} ${m} minute${m > 1 || m === 0 ? "s" : ""}`, raw: r };
	}

	return { type: "custom", label: r, detail: `Custom: ${r}`, raw: r };
}

function getOrdinal(n: number): string {
	if (n === 1 || n === 21 || n === 31) return `${n}st`;
	if (n === 2 || n === 22) return `${n}nd`;
	if (n === 3 || n === 23) return `${n}rd`;
	return `${n}th`;
}

function buildRecurrence(type: string, hour: number, minute: number, daysOfWeek: number[], dayOfMonth: number, intervalValue: number, intervalUnit: string, customRaw: string): string {
	if (type === "daily") return `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`;
	if (type === "weekdays") return `wd:${hour}:${minute.toString().padStart(2, "0")}`;
	if (type === "weekly" && daysOfWeek.length > 0) {
		if (daysOfWeek.length === 5 && daysOfWeek.every((d) => d >= 0 && d <= 4)) return `wd:${hour}:${minute.toString().padStart(2, "0")}`;
		const day = DOW_SHORT[daysOfWeek[0]];
		return `${day}:${hour}:${minute.toString().padStart(2, "0")}`;
	}
	if (type === "monthly") return `d${dayOfMonth}:${hour}:${minute.toString().padStart(2, "0")}`;
	if (type === "interval") return intervalUnit === "hours" ? `${intervalValue}h` : `${intervalValue}m`;
	return customRaw;
}

interface ScheduleBuilderProps {
	recurrence: string;
	onChange: (rec: string) => void;
}

function ScheduleBuilder({ recurrence, onChange }: ScheduleBuilderProps) {
	const parsed = parseRecurrence(recurrence);
	const defaultType = parsed?.type || "none";
	const [type, setType] = useState(defaultType);
	const [hour, setHour] = useState(8);
	const [minute, setMinute] = useState(0);
	const [daysOfWeek, setDaysOfWeek] = useState<number[]>([0]);
	const [dayOfMonth, setDayOfMonth] = useState(1);
	const [intervalValue, setIntervalValue] = useState(30);
	const [intervalUnit, setIntervalUnit] = useState("minutes");
	const [customRaw, setCustomRaw] = useState(recurrence || "");

	const preview = useMemo(() => {
		const parsedPreview = parseRecurrence(recurrence);
		return parsedPreview ? `${parsedPreview.label} — ${parsedPreview.detail}` : "";
	}, [recurrence]);

	const selectType = (t: string) => {
		setType(t);
		if (t !== "custom") {
			const rec = buildRecurrence(t, hour, minute, daysOfWeek, dayOfMonth, intervalValue, intervalUnit, "");
			onChange(rec);
		}
	};

	const updateField = () => {
		if (type !== "custom") {
			const rec = buildRecurrence(type, hour, minute, daysOfWeek, dayOfMonth, intervalValue, intervalUnit, "");
			onChange(rec);
		}
	};

	const toggleDay = (idx: number) => {
		setDaysOfWeek((prev) => {
			const next = prev.includes(idx) ? prev.filter((d) => d !== idx) : [...prev, idx].sort();
			return next;
		});
		setTimeout(updateField, 0);
	};

	useEffect(() => { updateField(); }, [hour, minute]); // eslint-disable-line react-hooks/exhaustive-deps
	useEffect(() => { if (type === "weekly") updateField(); }, [daysOfWeek]); // eslint-disable-line react-hooks/exhaustive-deps
	useEffect(() => { if (type === "monthly") updateField(); }, [dayOfMonth]); // eslint-disable-line react-hooks/exhaustive-deps
	useEffect(() => { if (type === "interval") updateField(); }, [intervalValue, intervalUnit]); // eslint-disable-line react-hooks/exhaustive-deps

	const scheduleTypes = [
		{ id: "none", label: "No schedule" },
		{ id: "daily", label: "Daily" },
		{ id: "weekdays", label: "Weekdays" },
		{ id: "weekly", label: "Weekly" },
		{ id: "monthly", label: "Monthly" },
		{ id: "interval", label: "Interval" },
		{ id: "custom", label: "Custom" },
	];

	return (
		<div className="space-y-3">
			<div className="flex gap-1.5 flex-wrap">
				{scheduleTypes.map((st) => (
					<button
						key={st.id}
						type="button"
						onClick={() => selectType(st.id)}
						className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
							type === st.id
								? "bg-fleet-900/30 border-fleet-600 text-fleet-300"
								: "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
						}`}
					>
						{st.label}
					</button>
				))}
			</div>

			{type !== "none" && type !== "custom" && (
				<div className="flex gap-3 items-end">
					{(type === "daily" || type === "weekdays" || type === "weekly" || type === "monthly") && (
						<>
							<div>
								<label className="text-[10px] text-slate-500 uppercase tracking-wider">Hour</label>
								<select
									value={hour}
									onChange={(e) => { setHour(parseInt(e.target.value)); }}
									className="w-20 mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
								>
									{HOURS.map((h) => (
										<option key={h} value={h}>{h.toString().padStart(2, "0")}</option>
									))}
								</select>
							</div>
							<div>
								<label className="text-[10px] text-slate-500 uppercase tracking-wider">Minute</label>
								<select
									value={minute}
									onChange={(e) => { setMinute(parseInt(e.target.value)); }}
									className="w-20 mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
								>
									{MINUTES.map((m) => (
										<option key={m} value={m}>{m.toString().padStart(2, "0")}</option>
									))}
								</select>
							</div>
						</>
					)}

					{type === "interval" && (
						<>
							<div>
								<label className="text-[10px] text-slate-500 uppercase tracking-wider">Every</label>
								<input
									type="number"
									min={1}
									value={intervalValue}
									onChange={(e) => setIntervalValue(Math.max(1, parseInt(e.target.value) || 1))}
									className="w-20 mt-1 bg-zinc-800 border-zinc-600 rounded-lg px-2 py-1.5 text-xs text-zinc-100"
								/>
							</div>
							<div>
								<label className="text-[10px] text-slate-500 uppercase tracking-wider">Unit</label>
								<select
									value={intervalUnit}
									onChange={(e) => setIntervalUnit(e.target.value)}
									className="w-24 mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
								>
									<option value="minutes">Minutes</option>
									<option value="hours">Hours</option>
								</select>
							</div>
						</>
					)}

					{type === "monthly" && (
						<div>
							<label className="text-[10px] text-slate-500 uppercase tracking-wider">Day of month</label>
							<select
								value={dayOfMonth}
								onChange={(e) => setDayOfMonth(parseInt(e.target.value))}
								className="w-20 mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
							>
								{DOM.map((d) => (
									<option key={d} value={d}>{getOrdinal(d)}</option>
								))}
							</select>
						</div>
					)}
				</div>
			)}

			{type === "weekly" && (
				<div className="flex gap-1.5">
					{DOW_LABELS.map((label, i) => (
						<button
							key={i}
							type="button"
							onClick={() => toggleDay(i)}
							className={`w-9 h-9 rounded-lg text-xs font-medium border transition-colors ${
								daysOfWeek.includes(i)
									? "bg-fleet-900/40 border-fleet-600 text-fleet-300"
									: "bg-slate-800 border-slate-700 text-slate-500 hover:border-slate-600"
							}`}
						>
							{label[0]}
						</button>
					))}
				</div>
			)}

			{type === "custom" && (
				<input
					value={customRaw}
					onChange={(e) => { setCustomRaw(e.target.value); onChange(e.target.value); }}
					placeholder="e.g. 07:00, wd:08:00, mon:14:30, d1:09:00, 30m, 2h"
					className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono outline-none focus:border-fleet-500"
				/>
			)}

			{recurrence && (
				<div className="flex items-center gap-2 text-xs text-slate-500 bg-slate-950/50 rounded-lg px-3 py-2">
					<Calendar className="w-3.5 h-3.5 text-fleet-400" />
					<span className="font-mono text-fleet-400">{recurrence}</span>
					<span className="text-slate-600">—</span>
					<span>{preview}</span>
				</div>
			)}
		</div>
	);
}


export function Tasks() {
	const [tasks, setTasks] = useState<Task[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [showForm, setShowForm] = useState(false);
	const [expandedId, setExpandedId] = useState<string | null>(null);

	const [formTask, setFormTask] = useState("");
	const [formDesc, setFormDesc] = useState("");
	const [formPriority, setFormPriority] = useState("medium");
	const [formGroup, setFormGroup] = useState("self");
	const [formRecurrence, setFormRecurrence] = useState("");
	const [formScriptId, setFormScriptId] = useState("");
	const [scripts, setScripts] = useState<{ id: string; name: string }[]>([]);
	const [saving, setSaving] = useState(false);
	const [runResultId, setRunResultId] = useState<string | null>(null);
	const [runResult, setRunResult] = useState<{ success: boolean; exit_code?: number; message?: string; stdout?: string; stderr?: string } | null>(null);

	const fetchTasks = useCallback(async () => {
		try {
			const r = await fetch(`${API_BASE}/api/tasks`);
			const d = await r.json();
			setTasks(d.tasks ?? []);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Failed to load tasks");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => { fetchTasks(); }, [fetchTasks]);

	useEffect(() => {
		fetch(`${API_BASE}/api/scripts`)
			.then((r) => r.json())
			.then((d) => setScripts((d.scripts ?? []).map((s: { id: string; name: string }) => ({ id: s.id, name: s.name }))))
			.catch(() => {});
	}, []);

	const completeTask = async (id: string) => {
		await fetch(`${API_BASE}/api/tasks/complete`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ task_id: id }),
		});
		fetchTasks();
	};

	const deleteTask = async (id: string) => {
		await fetch(`${API_BASE}/api/tasks/delete`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ task_id: id }),
		});
		fetchTasks();
	};

	const createTask = async () => {
		if (!formTask.trim() || saving) return;
		setSaving(true);
		try {
			await fetch(`${API_BASE}/api/tasks`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				task: formTask.trim(),
				description: formDesc.trim() || undefined,
				priority: formPriority,
				group: formGroup,
				recurrence: formRecurrence || undefined,
				script_id: formScriptId || undefined,
			}),
			});
			setFormTask("");
			setFormDesc("");
			setFormRecurrence("");
			setFormScriptId("");
			setShowForm(false);
			fetchTasks();
		} catch {
			setError("Failed to create task");
		}
		setSaving(false);
	};

	const toggleExpand = (id: string) => setExpandedId(expandedId === id ? null : id);

	const runScript = async (task: Task) => {
		const scriptId = task.metadata?.script_id as string | undefined;
		if (!scriptId) return;
		setRunResultId(task.id);
		setRunResult(null);
		try {
			const r = await fetch(`${API_BASE}/api/scripts/${scriptId}/run`, { method: "POST", headers: { "Content-Type": "application/json" } });
			const d = await r.json();
			setRunResult({ success: d.success, exit_code: d.exit_code, message: d.message, stdout: d.stdout, stderr: d.stderr });
		} catch {
			setRunResult({ success: false, message: "Run failed" });
		}
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
				<button
					onClick={() => setShowForm(!showForm)}
					className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5"
				>
					{showForm ? "Cancel" : "New Task"}
				</button>
				<button
					onClick={fetchTasks}
					disabled={loading}
					className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5"
				>
					<RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
				</button>
			</div>

			{error && (
				<div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
					<AlertCircle className="w-4 h-4 shrink-0" /> {error}
				</div>
			)}

			{/* New Task Form */}
			{showForm && (
				<div className="border border-slate-800 rounded-lg bg-slate-900/50 p-4 space-y-3">
					<h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">New Task</h3>
					<input
						value={formTask}
						onChange={(e) => setFormTask(e.target.value)}
						placeholder="Task title"
						className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
						autoFocus
					/>
					<textarea
						value={formDesc}
						onChange={(e) => setFormDesc(e.target.value)}
						placeholder="Description (optional)"
						rows={2}
						className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none resize-none"
					/>
					<div className="flex gap-3">
						<div className="flex-1">
							<label className="text-[10px] text-slate-500 uppercase tracking-wider">Priority</label>
							<select
								value={formPriority}
								onChange={(e) => setFormPriority(e.target.value)}
								className="w-full mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
							>
								<option value="high">High</option>
								<option value="medium">Medium</option>
								<option value="low">Low</option>
							</select>
						</div>
						<div className="flex-1">
							<label className="text-[10px] text-slate-500 uppercase tracking-wider">Group</label>
							<select
								value={formGroup}
								onChange={(e) => setFormGroup(e.target.value)}
								className="w-full mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
							>
								<option value="self">Self</option>
								<option value="human">Human</option>
								<option value="external">External</option>
							</select>
						</div>
					</div>

					{/* Script selector */}
					{scripts.length > 0 && (
						<div className="flex items-center gap-3">
							<Zap className="w-3.5 h-3.5 text-fleet-400" />
							<select
								value={formScriptId}
								onChange={(e) => setFormScriptId(e.target.value)}
								className="flex-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs"
							>
								<option value="">No script</option>
								{scripts.map((s) => (
									<option key={s.id} value={s.id}>{s.name}</option>
								))}
							</select>
						</div>
					)}

					{/* Schedule builder */}
					<div className="border border-slate-800 rounded-lg bg-slate-950/30 p-3">
						<div className="flex items-center gap-2 mb-2">
							<Clock className="w-3.5 h-3.5 text-fleet-400" />
							<span className="text-[10px] text-slate-500 uppercase tracking-wider">Schedule</span>
						</div>
						<ScheduleBuilder recurrence={formRecurrence} onChange={setFormRecurrence} />
					</div>

					<div className="flex justify-end gap-2 pt-1">
						<button onClick={() => setShowForm(false)} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded-lg">Cancel</button>
						<button onClick={createTask} disabled={!formTask.trim() || saving} className="px-3 py-1.5 text-xs text-white bg-fleet-700 hover:bg-fleet-600 disabled:opacity-50 rounded-lg">
							{saving ? "Creating..." : "Create Task"}
						</button>
					</div>
				</div>
			)}

			{/* Task list */}
			{tasks.length === 0 && !loading && <p className="text-sm text-slate-500 text-center py-8">No tasks. Create one above.</p>}
			<div className="grid grid-cols-1 gap-2">
				{tasks.map((t) => {
					const desc = t.description || (t.metadata?.description as string | undefined);
					const schedule = parseRecurrence(t.recurrence);
					const isExpanded = expandedId === t.id;
					return (
						<div key={t.id} className="border border-slate-800 rounded-lg bg-slate-900/50 hover:border-slate-700 transition-colors">
							<div className="flex items-center gap-3 px-4 py-3">
								<button onClick={() => completeTask(t.id)} className="shrink-0 w-6 h-6 rounded border border-slate-700 flex items-center justify-center hover:border-green-500 hover:text-green-400 text-slate-600" title="Mark complete">
									<Check className="w-3.5 h-3.5" />
								</button>
								<button onClick={() => toggleExpand(t.id)} className="shrink-0 text-slate-600 hover:text-slate-300">
									{isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
								</button>
								<div className="flex-1 min-w-0">
									<p className="text-sm text-slate-200 truncate cursor-pointer" onClick={() => toggleExpand(t.id)}>{t.task}</p>
									<div className="flex items-center gap-2 mt-0.5 flex-wrap">
										<span className={`text-[10px] uppercase ${prioColor(t.priority)}`}>{t.priority}</span>
										<span className={`text-[10px] ${groupColor(t.group_name)}`}>{t.group_name}</span>
										{schedule && (
											<span className="text-[10px] text-fleet-500 flex items-center gap-1">
												<Calendar className="w-3 h-3" />
												{schedule.label}
											</span>
										)}
										{t.recurrence && (
											<span className="text-[10px] font-mono text-slate-600">{t.recurrence}</span>
										)}
									</div>
								</div>
								<button onClick={() => deleteTask(t.id)} className="shrink-0 text-slate-600 hover:text-red-400" title="Delete task">
									<Trash2 className="w-3.5 h-3.5" />
								</button>
							</div>

							{isExpanded && (
								<div className="border-t border-slate-800 px-4 py-3 space-y-2">
									{desc ? (
										<p className="text-sm text-slate-400 whitespace-pre-wrap">{desc}</p>
									) : (
										<p className="text-sm text-slate-600 italic">No description</p>
									)}

									{/* Run Script button */}
									{t.metadata?.script_id as string && (
										<div>
											{runResultId === t.id ? (
												<div className="text-xs space-y-1">
													<div className={`flex items-center gap-2 ${runResult?.success ? "text-emerald-400" : "text-red-400"}`}>
														<span>Exit: {runResult?.exit_code ?? "?"}</span>
														<span className="text-slate-600">|</span>
														<span className="text-slate-400 truncate">{runResult?.message || ""}</span>
													</div>
													{runResult?.stdout && <pre className="text-emerald-300 bg-slate-950 rounded p-2 max-h-32 overflow-auto">{runResult.stdout}</pre>}
													{runResult?.stderr && <pre className="text-red-300 bg-slate-950 rounded p-2 max-h-32 overflow-auto">{runResult.stderr}</pre>}
												</div>
											) : (
												<button
													onClick={() => runScript(t)}
													className="flex items-center gap-1 text-xs text-fleet-400 hover:text-fleet-300 border border-fleet-800 rounded px-2 py-1"
												>
													<Play className="w-3 h-3" /> Run Script
												</button>
											)}
										</div>
									)}

									<div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-slate-600">
										<span>Created: {t.created_at ? new Date(t.created_at).toLocaleString() : "unknown"}</span>
										<span>Status: {t.status}</span>
										{schedule && (
											<span className="flex items-center gap-1">
												<Calendar className="w-3 h-3" /> Schedule: {schedule.detail}
											</span>
										)}
									</div>
								</div>
							)}
						</div>
					);
				})}
			</div>
		</div>
	);
}
