import {
	Activity,
	AlertTriangle,
	Info,
	RefreshCw,
	Terminal,
	Trash2,
	XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

interface LogEntry {
	id: string;
	level: string;
	message: string;
	source: string;
	timestamp: string;
}

const LEVEL_COLORS: Record<string, string> = {
	info: "text-blue-400",
	warn: "text-amber-400",
	error: "text-red-400",
	debug: "text-slate-500",
};

const LEVEL_BG: Record<string, string> = {
	info: "bg-blue-950/20 border-blue-900/30",
	warn: "bg-amber-950/20 border-amber-900/30",
	error: "bg-red-950/20 border-red-900/30",
	debug: "bg-slate-950/50 border-slate-800/30",
};

export function LoggerPage() {
	const [logs, setLogs] = useState<LogEntry[]>([]);
	const [loading, setLoading] = useState(true);
	const [autoScroll, setAutoScroll] = useState(true);
	const [filter, setFilter] = useState<string>("all");
	const bottomRef = useRef<HTMLDivElement>(null);
	const esRef = useRef<EventSource | null>(null);

	const fetchLogs = useCallback(async () => {
		try {
			const res = await fetch(API_BASE + "/api/logs?limit=200");
			if (res.ok) {
				const data = await res.json();
				setLogs(data.logs ?? []);
			}
		} catch {
			/* ignore */
		}
		setLoading(false);
	}, []);

	useEffect(() => {
		fetchLogs();

		// Connect to SSE stream for live logs
		const es = new EventSource("/api/logs/stream");
		esRef.current = es;

		es.onmessage = (event) => {
			try {
				const entry: LogEntry = JSON.parse(event.data);
				setLogs((prev) => [...prev.slice(-499), entry]);
			} catch {
				/* ignore */
			}
		};

		return () => {
			es.close();
		};
	}, [fetchLogs]);

	useEffect(() => {
		if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [logs, autoScroll]);

	const filtered =
		filter === "all" ? logs : logs.filter((l) => l.level === filter);

	const levelIcon = (level: string) => {
		switch (level) {
			case "error":
				return <XCircle className="w-3.5 h-3.5" />;
			case "warn":
				return <AlertTriangle className="w-3.5 h-3.5" />;
			case "debug":
				return <Terminal className="w-3.5 h-3.5" />;
			default:
				return <Info className="w-3.5 h-3.5" />;
		}
	};

	return (
		<div className="flex flex-col h-[calc(100vh-7rem)]">
			{/* Header */}
			<div className="flex items-center gap-3 mb-4 shrink-0">
				<Activity className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Logger</h2>
				<div className="flex-1" />
				<div className="flex items-center gap-2">
					{/* Level filter */}
					<div className="flex bg-slate-900 border border-slate-800 rounded-lg overflow-hidden text-xs">
						{["all", "info", "warn", "error", "debug"].map((lvl) => (
							<button
								key={lvl}
								onClick={() => setFilter(lvl)}
								className={`px-2.5 py-1.5 font-medium transition-colors ${
									filter === lvl
										? "bg-slate-700 text-white"
										: "text-slate-500 hover:text-slate-300"
								}`}
							>
								{lvl === "all"
									? "All"
									: lvl.charAt(0).toUpperCase() + lvl.slice(1)}
							</button>
						))}
					</div>

					<button
						onClick={() => setAutoScroll(!autoScroll)}
						className={`px-2.5 py-1.5 text-xs rounded-lg border transition-colors ${
							autoScroll
								? "bg-fleet-900/30 border-fleet-700 text-fleet-300"
								: "bg-slate-900 border-slate-800 text-slate-500 hover:text-slate-300"
						}`}
					>
						Auto-scroll
					</button>

					<button
						onClick={fetchLogs}
						className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-400 hover:text-white transition-colors"
					>
						<RefreshCw className="w-3.5 h-3.5" />
						Refresh
					</button>

					<button
						onClick={() => setLogs([])}
						className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-400 hover:text-white transition-colors"
					>
						<Trash2 className="w-3.5 h-3.5" />
						Clear
					</button>
				</div>
			</div>

			{/* Log count */}
			<p className="text-xs text-slate-500 mb-2 shrink-0">
				{filtered.length} entries{filter !== "all" ? ` (level: ${filter})` : ""}
				{esRef.current ? " · Live" : ""}
			</p>

			{/* Log list */}
			<div className="flex-1 overflow-y-auto space-y-0.5 font-mono text-xs">
				{loading && (
					<div className="flex items-center justify-center py-8 text-slate-500">
						<RefreshCw className="w-4 h-4 animate-spin mr-2" />
						Loading logs...
					</div>
				)}

				{!loading && filtered.length === 0 && (
					<div className="flex items-center justify-center py-8 text-slate-500">
						{logs.length === 0
							? "No log entries yet"
							: "No entries match filter"}
					</div>
				)}

				{filtered.map((entry) => (
					<div
						key={entry.id}
						className={`flex items-start gap-2 px-3 py-1.5 rounded border ${LEVEL_BG[entry.level] ?? "border-slate-800/30"} hover:bg-slate-800/30 transition-colors`}
					>
						<span
							className={`shrink-0 mt-0.5 ${LEVEL_COLORS[entry.level] ?? "text-slate-400"}`}
						>
							{levelIcon(entry.level)}
						</span>
						<span className="text-slate-600 shrink-0 w-20">
							{entry.timestamp ? entry.timestamp.slice(11, 23) : "--:--:--"}
						</span>
						<span
							className={`shrink-0 uppercase text-[10px] font-bold w-10 ${LEVEL_COLORS[entry.level] ?? ""}`}
						>
							{entry.level}
						</span>
						<span className="text-slate-500 shrink-0 w-16 text-[10px]">
							{entry.source}
						</span>
						<span className="text-slate-300 break-words flex-1">
							{entry.message}
						</span>
					</div>
				))}
				<div ref={bottomRef} />
			</div>
		</div>
	);
}
