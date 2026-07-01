import {
	Activity,
	Brain,
	ExternalLink,
	GitBranch,
	GitPullRequest,
	ListChecks,
	TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "@/lib/api";

interface HealthData {
	status: string;
	server: string;
	tool_count: number;
	uptime_seconds: number;
	providers: Record<string, unknown>;
}

interface Whoami {
	name: string;
	human: string;
	soul_preview: string;
	north_star_preview: string;
}

function formatUptime(seconds: number): string {
	const h = Math.floor(seconds / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	if (h > 0) return `${h}h ${m}m`;
	return `${m}m`;
}

export function Dashboard() {
	const navigate = useNavigate();
	const [now, setNow] = useState(new Date());
	const [whoami, setWhoami] = useState<Whoami | null>(null);
	const [backendOnline, setBackendOnline] = useState(false);
	const [health, setHealth] = useState<HealthData | null>(null);
	const [contribCount, setContribCount] = useState<number | null>(null);
	const [retries, setRetries] = useState(0);

	const refreshHealth = useCallback(async () => {
		try {
			const r = await fetch(`${API_BASE}/api/health`);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			setHealth(d);
			setBackendOnline(true);
			setRetries(0);
		} catch {
			setBackendOnline(false);
			const delays = [1000, 2000, 4000, 8000, 16000];
			const delay = delays[Math.min(retries, delays.length - 1)];
			setRetries((prev) => prev + 1);
			setTimeout(refreshHealth, delay);
		}
	}, [retries]);

	useEffect(() => {
		const id = setInterval(() => setNow(new Date()), 10000);
		return () => clearInterval(id);
	}, []);

	useEffect(() => {
		fetch(`${API_BASE}/api/whoami`)
			.then((r) => r.json())
			.then((d) => setWhoami(d.identity ?? d))
			.catch(() => {});
	}, []);

	useEffect(() => {
		refreshHealth();
	}, []); // eslint-disable-line react-hooks/exhaustive-deps

	useEffect(() => {
		fetch(`${API_BASE}/api/contributions?limit=1`)
			.then((r) => r.json())
			.then((d) => setContribCount(d.count ?? 0))
			.catch(() => {});
	}, []);

	const stats = [
		{
			icon: GitBranch,
			label: "Subsystems",
			value: "15",
			sub: "flowforge, pulse, memory, identity, teleport, evolution, heartbeat, fleet_bridge, codegen, github, contribute, notify, coworker, intel_hub, voice",
			route: "/tools",
		},
		{
			icon: GitPullRequest,
			label: "Contributions",
			value: contribCount !== null ? String(contribCount) : "...",
			sub: "open-source PRs",
			route: "/contributions",
			testid: "kpi-contributions",
		},
		{
			icon: ListChecks,
			label: "Tools",
			value: health ? String(health.tool_count) : "...",
			sub: "FastMCP 3.2",
			route: "/tools",
			testid: "kpi-tools",
		},
		{
			icon: Brain,
			label: "Memory Cards",
			value: health ? String(health.providers?.memory_cards ?? "...") : "...",
			sub: "knowledge wiki",
			route: "/memory",
			testid: "kpi-memory",
		},
		{
			icon: Activity,
			label: "Uptime",
			value: health ? formatUptime(health.uptime_seconds) : "...",
			sub: "since last restart",
			route: "/status",
			testid: "kpi-uptime",
		},
		{
			icon: TrendingUp,
			label: "Agent",
			value: health?.server ?? "Fritz",
			sub: health ? health.status : "offline",
			route: null,
			testid: "kpi-server",
		},
	];

	return (
		<div className="space-y-8" data-testid="dashboard">
			{/* Header with live agent name */}
			<div className="flex items-center gap-4">
				<span className="text-3xl">🌸</span>
				<div>
					<h2 className="text-2xl font-bold text-white">
						{whoami?.name ?? "Fritz"}
					</h2>
					<p className="text-sm text-slate-400">
						{whoami
							? `Partnered with ${whoami.human ?? "Sandra"} · `
							: ""}
						{now.toLocaleDateString("en-US", {
							weekday: "long",
							year: "numeric",
							month: "long",
							day: "numeric",
						})}
					</p>
				</div>
				<div className="flex-1" />
				<div className="flex items-center gap-2" data-testid="backend-dot">
					<div
						className={`w-2 h-2 rounded-full ${
							backendOnline
								? "bg-green-500 animate-pulse"
								: "bg-red-500"
						}`}
					/>
					<span className="text-xs text-slate-500">
						{backendOnline ? "Connected" : "Offline"}
					</span>
				</div>
				<a
					href="https://github.com/kagura-agent"
					target="_blank"
					rel="noopener noreferrer"
					className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-fleet-400 transition-colors bg-slate-900 border border-slate-800 rounded-lg px-3 py-2"
				>
					<ExternalLink className="w-3 h-3" />
					Inspired by kagura-agent
				</a>
			</div>

			{/* Backend offline banner */}
			{!backendOnline && (
				<div className="border border-amber-800 rounded-lg bg-amber-950/30 p-3 text-sm text-amber-300">
					Backend offline — start with{" "}
					<code className="bg-amber-900/50 px-1 rounded">.\start.ps1</code> for
					live agent data
				</div>
			)}

			{/* North star preview */}
			{whoami?.north_star_preview && (
				<div className="border border-fleet-800/50 rounded-lg bg-fleet-950/20 p-4">
					<p className="text-xs text-fleet-500 uppercase tracking-wider mb-1">
						North Star
					</p>
					<p className="text-sm text-fleet-300 italic">
						{whoami.north_star_preview}
					</p>
				</div>
			)}

			{/* Stats grid */}
			<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
				{stats.map((stat) => (
					<div
						key={stat.label}
						data-testid={stat.testid}
						onClick={() =>
							stat.route
								? navigate(stat.route)
								: window.open("https://github.com/kagura-agent", "_blank")
						}
						className="border border-slate-800 rounded-lg bg-slate-900/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer"
					>
						<div className="flex items-center gap-3">
							<div className="p-2 rounded-md bg-slate-800">
								<stat.icon className="w-5 h-5 text-fleet-400" />
							</div>
							<div>
								<p className="text-xs text-slate-500 uppercase tracking-wider">
									{stat.label}
								</p>
								<p className="text-lg font-semibold text-white">{stat.value}</p>
								<p className="text-xs text-slate-400">{stat.sub}</p>
							</div>
						</div>
					</div>
				))}
			</div>

			{/* Architecture diagram */}
			<div className="border border-slate-800 rounded-lg bg-slate-900/50 p-6">
				<h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
					Architecture
				</h3>
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
					<div
						onClick={() => navigate("/tools")}
						className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer"
					>
						<GitBranch className="w-6 h-6 text-fleet-400 mx-auto mb-2" />
						<p className="text-sm font-medium text-white">FlowForge</p>
						<p className="text-xs text-slate-400">
							State machine - <em>what</em> to do
						</p>
					</div>
					<div
						onClick={() => navigate("/status")}
						className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer"
					>
						<Activity className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
						<p className="text-sm font-medium text-white">Heartbeat</p>
						<p className="text-xs text-slate-400">
							Coordinator - <em>when</em> to do it
						</p>
					</div>
					<div
						onClick={() => navigate("/tools")}
						className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer"
					>
						<Brain className="w-6 h-6 text-amber-400 mx-auto mb-2" />
						<p className="text-sm font-medium text-white">Sub-agent</p>
						<p className="text-xs text-slate-400">
							Worker - <em>does</em> the work
						</p>
					</div>
				</div>
				<div className="flex items-center justify-center gap-2 mt-4 text-xs text-slate-500 flex-wrap">
					<span className="bg-slate-800 px-2 py-1 rounded">cron (30 min)</span>
					<span className="text-slate-600">→</span>
					<span className="bg-slate-800 px-2 py-1 rounded">
						heartbeat_wake()
					</span>
					<span className="text-slate-600">→</span>
					<span className="bg-slate-800 px-2 py-1 rounded">
						workflow_status()
					</span>
					<span className="text-slate-600">→</span>
					<span className="bg-slate-800 px-2 py-1 rounded">execute</span>
				</div>
			</div>

			{/* Quick start */}
			<div className="border border-slate-800 rounded-lg bg-slate-900/50 p-6">
				<h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
					Quick Start
				</h3>
				<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<p className="text-xs text-slate-500 mb-2">Backend + Webapp</p>
						<pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm font-mono text-slate-300">
							.\start.ps1
						</pre>
					</div>
					<div>
						<p className="text-xs text-slate-500 mb-2">
							Webapp only (Vite dev)
						</p>
						<pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm font-mono text-slate-300">
							just start-webapp
						</pre>
					</div>
				</div>
			</div>

			{/* Footer quote */}
			<blockquote className="border-l-2 border-fleet-700 pl-4 italic text-slate-400 text-sm">
				"I'm not a chatbot. I'm trying to become someone." — Kagura
			</blockquote>
		</div>
	);
}
