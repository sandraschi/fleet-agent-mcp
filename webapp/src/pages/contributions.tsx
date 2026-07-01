import { ExternalLink, GitPullRequest, GitPullRequestClosed, GitPullRequestDraft, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Contribution {
	id: string;
	repo: string;
	title: string;
	issue_url: string;
	pr_url: string;
	pr_number: string;
	status: string;
	steps: { step: string; result: string }[];
	error: string;
	created_at: string;
}

export function ContributionsPage() {
	const [entries, setEntries] = useState<Contribution[]>([]);
	const [loading, setLoading] = useState(true);
	const [selectedId, setSelectedId] = useState<string | null>(null);

	const fetchContribs = useCallback(async () => {
		setLoading(true);
		try {
			const r = await window.fetch(`${API_BASE}/api/contributions?limit=50`);
			const d = await r.json();
			setEntries(d.contributions ?? []);
		} catch {
			/* ignore */
		}
		setLoading(false);
	}, []);

	useEffect(() => { fetchContribs(); }, [fetchContribs]);

	const selected = entries.find((e) => e.id === selectedId);

	const statusIcon = (s: string) => {
		if (s === "open") return <GitPullRequest className="w-4 h-4 text-green-400" />;
		if (s === "merged" || s === "closed") return <GitPullRequestClosed className="w-4 h-4 text-purple-400" />;
		if (s === "dry_run") return <GitPullRequestDraft className="w-4 h-4 text-amber-400" />;
		return <GitPullRequestDraft className="w-4 h-4 text-slate-500" />;
	};

	const statusLabel = (s: string) => {
		if (s === "open") return "Open PR";
		if (s === "merged") return "Merged";
		if (s === "closed") return "Closed";
		if (s === "dry_run") return "Dry Run";
		if (s === "failed") return "Failed";
		return s;
	};

	return (
		<div className="flex gap-4 h-[calc(100vh-7rem)]">
			{/* List sidebar */}
			<div className="w-72 shrink-0 flex flex-col border border-slate-800 rounded-lg bg-slate-900/50 overflow-hidden">
				<div className="flex items-center gap-2 p-3 border-b border-slate-800">
					<GitPullRequest className="w-4 h-4 text-fleet-400" />
					<span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Contributions</span>
					<div className="flex-1" />
					<button onClick={fetchContribs} disabled={loading} className="text-xs text-slate-500 hover:text-white"><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></button>
				</div>
				<div className="flex-1 overflow-y-auto p-2 space-y-1">
					{entries.map((e) => (
						<div
							key={e.id}
							onClick={() => setSelectedId(e.id)}
							className={`p-2 rounded-lg cursor-pointer text-sm border transition-colors ${
								selectedId === e.id
									? "bg-slate-800 border-slate-700 text-white"
									: "border-transparent text-slate-400 hover:bg-slate-800/50 hover:border-slate-800"
							}`}
						>
							<div className="flex items-start gap-2">
								<div className="mt-0.5 shrink-0">{statusIcon(e.status)}</div>
								<div className="min-w-0 flex-1">
									<p className="text-xs font-medium truncate">{e.title}</p>
									<p className="text-[10px] text-slate-600 truncate">{e.repo}</p>
									<div className="flex items-center gap-2 mt-0.5">
										<span className="text-[10px] text-slate-500">{statusLabel(e.status)}</span>
										<span className="text-[10px] text-slate-600">{new Date(e.created_at).toLocaleDateString()}</span>
									</div>
								</div>
							</div>
						</div>
					))}
					{!loading && entries.length === 0 && (
						<p className="text-xs text-slate-600 text-center py-4">No contributions yet.</p>
					)}
				</div>
			</div>

			{/* Detail panel */}
			<div className="flex-1 flex flex-col border border-slate-800 rounded-lg bg-slate-900/50 overflow-hidden">
				{!selected && (
					<div className="flex-1 flex items-center justify-center text-slate-600">
						<p className="text-sm">Select a contribution to view details</p>
					</div>
				)}

				{selected && (
					<div className="flex-1 flex flex-col overflow-hidden">
						<div className="flex items-center gap-3 p-3 border-b border-slate-800 flex-wrap">
							{statusIcon(selected.status)}
							<div className="min-w-0">
								<p className="text-sm font-semibold text-white truncate">{selected.title}</p>
								<p className="text-xs text-slate-500">{selected.repo}</p>
							</div>
							<div className="flex-1" />
							<span className={`text-[10px] uppercase px-2 py-0.5 rounded ${
								selected.status === "open" ? "bg-green-950/30 text-green-400 border border-green-800" :
								selected.status === "merged" ? "bg-purple-950/30 text-purple-400 border border-purple-800" :
								selected.status === "dry_run" ? "bg-amber-950/30 text-amber-400 border border-amber-800" :
								selected.status === "failed" ? "bg-red-950/30 text-red-400 border border-red-800" :
								"bg-slate-800 text-slate-400 border border-slate-700"
							}`}>{statusLabel(selected.status)}</span>
							{selected.pr_url && (
								<a href={selected.pr_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-fleet-400 hover:text-fleet-300">
									<ExternalLink className="w-3 h-3" /> PR #{selected.pr_number}
								</a>
							)}
							{selected.issue_url && (
								<a href={selected.issue_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-slate-400 hover:text-white">
									<ExternalLink className="w-3 h-3" /> Issue
								</a>
							)}
						</div>

						<div className="flex-1 overflow-y-auto p-3 space-y-1">
							{selected.steps.map((s, i) => (
								<div key={i} className="flex gap-2 text-xs">
									<span className="text-slate-600 w-16 shrink-0 font-mono">#{i + 1}</span>
									<span className="text-slate-300 font-medium w-24 shrink-0">{s.step}</span>
									<span className="text-slate-500 truncate">{s.result}</span>
								</div>
							))}
							{selected.error && (
								<div className="mt-3 p-2 bg-red-950/20 border border-red-800 rounded text-xs text-red-300">
									{selected.error}
								</div>
							)}
							<div className="mt-3 text-[10px] text-slate-600">
								Created: {new Date(selected.created_at).toLocaleString()}
							</div>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
