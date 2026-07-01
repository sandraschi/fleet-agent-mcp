import { Activity, AlertCircle, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface HealthData {
	health: {
		agent_name: string;
		uptime_seconds: number;
		uptime_human: string;
		active_workflow: string | null;
		current_node: string | null;
		tasks: { pending: number; done: number; total: number };
		memory_cards: number;
		evolution_entries: number;
		workflows_registered: number;
		heartbeat_interval_minutes: number;
	};
}

export function Status() {
	const [health, setHealth] = useState<HealthData["health"] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	const fetchStatus = async () => {
		setLoading(true);
		setError(null);
		try {
			const res = await fetch(API_BASE + "/api/status");
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const data: HealthData = await res.json();
			setHealth(data.health ?? data);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Cannot reach backend");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchStatus();
	}, []);

	return (
		<div className="space-y-6">
			<div className="flex items-center gap-3">
				<Activity className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Agent Status</h2>
				<div className="flex-1" />
				<button
					onClick={fetchStatus}
					disabled={loading}
					className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors disabled:opacity-50"
				>
					<RefreshCw
						className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
					/>
					Refresh
				</button>
			</div>

			{error && (
				<div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
					<AlertCircle className="w-4 h-4 shrink-0" />
					{error} — start the backend first (
					<code className="text-red-200 bg-red-900/50 px-1 rounded">
						.\start.ps1
					</code>
					)
				</div>
			)}

			{loading && !health && (
				<div className="flex items-center justify-center py-12 text-slate-500">
					<Activity className="w-5 h-5 animate-pulse mr-2" />
					Loading...
				</div>
			)}

			{health && (
				<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
					<StatCard label="Agent Name" value={health.agent_name} />
					<StatCard label="Uptime" value={health.uptime_human} />
					<StatCard
						label="Active Workflow"
						value={health.active_workflow ?? "none"}
					/>
					<StatCard label="Current Node" value={health.current_node ?? "—"} />
					<StatCard
						label="Pending Tasks"
						value={String(health.tasks.pending)}
						sub={`${health.tasks.done} done, ${health.tasks.total} total`}
					/>
					<StatCard label="Memory Cards" value={String(health.memory_cards)} />
					<StatCard
						label="Evolution Entries"
						value={String(health.evolution_entries)}
					/>
					<StatCard
						label="Registered Workflows"
						value={String(health.workflows_registered)}
					/>
				</div>
			)}

			{!health && !loading && !error && (
				<p className="text-sm text-slate-500">
					Could not reach backend at /api/status. Start the server first.
				</p>
			)}
		</div>
	);
}

function StatCard({
	label,
	value,
	sub,
}: { label: string; value: string; sub?: string }) {
	return (
		<div className="border border-slate-800 rounded-lg bg-slate-900/50 p-4">
			<p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
				{label}
			</p>
			<p className="text-lg font-semibold text-white">{value}</p>
			{sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
		</div>
	);
}
