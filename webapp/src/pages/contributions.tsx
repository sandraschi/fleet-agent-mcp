import { ChevronDown, ChevronRight, ExternalLink, GitPullRequest, GitPullRequestClosed, GitPullRequestDraft, RefreshCw, Search, Sparkles } from "lucide-react";
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

interface IssueAnalysis {
	tractability: string;
	confidence: number;
	reasoning: string;
	likely_duplicate_effort: boolean;
	recommendation: string;
	why_skip: string | null;
	llm_provider: string;
}

interface ExistingIssueFinding {
	number: number;
	title: string;
	url: string;
	age_signal: { age_days: number; comment_count: number; maintainer_engaged: boolean; quadrant: string };
	analysis: IssueAnalysis;
}

interface SelfFoundFinding {
	tool: string;
	file: string;
	line: number;
	code: string;
	message: string;
}

interface AnalyzeReport {
	success: boolean;
	repo: string;
	instrumentation: { instrumented_tools: string[]; fully_instrumented: boolean };
	existing_issues: ExistingIssueFinding[];
	self_found: SelfFoundFinding[];
	message: string;
}

interface Candidate {
	owner: string;
	repo: string;
	description: string;
	stars: number;
	pushed_at: string;
	report: AnalyzeReport;
}

const recColor = (rec: string) =>
	rec === "attempt" ? "text-emerald-400" : rec === "issue_only" ? "text-amber-400" : "text-slate-500";

function FindingsReport({ report, onAct }: { report: AnalyzeReport; onAct: (summary: string, action: "issue" | "pr", issueNumber?: string) => void }) {
	if (!report.success) return <p className="text-xs text-red-400">{report.message}</p>;
	return (
		<div className="space-y-2 text-xs">
			<p className="text-slate-500">
				{report.message} {!report.instrumentation.fully_instrumented && <span className="text-amber-400">(not lint-instrumented)</span>}
			</p>
			{report.existing_issues.map((f) => (
				<div key={f.number} className="border border-slate-800 rounded p-2 bg-slate-950/40">
					<div className="flex items-center gap-2">
						<a href={f.url} target="_blank" rel="noopener noreferrer" className="text-slate-200 hover:text-fleet-400 truncate">#{f.number} {f.title}</a>
						<span className={`ml-auto uppercase text-[10px] ${recColor(f.analysis.recommendation)}`}>{f.analysis.recommendation}</span>
					</div>
					<p className="text-slate-500 mt-1">{f.analysis.tractability} · {(f.analysis.confidence * 100).toFixed(0)}% conf · {f.age_signal.quadrant}</p>
					<p className="text-slate-600 mt-1">{f.analysis.reasoning}</p>
					{f.analysis.recommendation === "attempt" && (
						<div className="flex gap-2 mt-1.5">
							<button onClick={() => onAct(f.title, "issue", String(f.number))} className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300">File issue</button>
							<button onClick={() => onAct(f.title, "pr", String(f.number))} className="px-2 py-0.5 rounded bg-fleet-900/40 hover:bg-fleet-900/70 text-fleet-300 border border-fleet-800">Attempt PR (own repos only)</button>
						</div>
					)}
				</div>
			))}
			{report.self_found.map((f, i) => (
				<div key={i} className="border border-amber-900/40 rounded p-2 bg-amber-950/10">
					<p className="text-amber-300">{f.tool}/{f.code}: {f.message}</p>
					<p className="text-slate-600">{f.file}:{f.line}</p>
					<div className="flex gap-2 mt-1.5">
						<button onClick={() => onAct(`${f.code}: ${f.message} (${f.file}:${f.line})`, "issue")} className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300">File friendly issue</button>
					</div>
				</div>
			))}
			{report.existing_issues.length === 0 && report.self_found.length === 0 && (
				<p className="text-slate-600">Nothing found worth flagging.</p>
			)}
		</div>
	);
}

function FindWorkPanel({ onActed }: { onActed: () => void }) {
	const [open, setOpen] = useState(false);
	const [mode, setMode] = useState<"target" | "crawler">("target");
	const [repoUrl, setRepoUrl] = useState("");
	const [busy, setBusy] = useState(false);
	const [targetReport, setTargetReport] = useState<AnalyzeReport | null>(null);

	const [language, setLanguage] = useState("");
	const [minStars, setMinStars] = useState(5);
	const [maxStars, setMaxStars] = useState(5000);
	const [activeDays, setActiveDays] = useState(90);
	const [topic, setTopic] = useState("");
	const [repoLimit, setRepoLimit] = useState(3);
	const [candidates, setCandidates] = useState<Candidate[]>([]);

	const [actMessage, setActMessage] = useState<string | null>(null);

	const runTarget = async () => {
		if (!repoUrl.trim() || busy) return;
		setBusy(true);
		setTargetReport(null);
		try {
			const r = await fetch(`${API_BASE}/api/repo-analysis`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ repo_url: repoUrl.trim(), max_issues: 5 }),
			});
			setTargetReport(await r.json());
		} catch {
			setTargetReport({ success: false, repo: repoUrl, instrumentation: { instrumented_tools: [], fully_instrumented: false }, existing_issues: [], self_found: [], message: "Request failed" });
		}
		setBusy(false);
	};

	const runCrawler = async () => {
		if (busy) return;
		setBusy(true);
		setCandidates([]);
		try {
			const r = await fetch(`${API_BASE}/api/repo-analysis/discover`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					language, min_stars: minStars, max_stars: maxStars,
					active_days: activeDays, topic, repo_limit: repoLimit,
				}),
			});
			const d = await r.json();
			setCandidates(d.reports ?? []);
		} catch {
			setCandidates([]);
		}
		setBusy(false);
	};

	const act = async (targetRepoUrl: string, summary: string, action: "issue" | "pr", issueNumber?: string) => {
		setActMessage(null);
		try {
			const r = await fetch(`${API_BASE}/api/repo-analysis/act`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ repo_url: targetRepoUrl, action, summary, issue_number: issueNumber ?? "" }),
			});
			const d = await r.json();
			setActMessage(d.message || (d.success ? "Done." : "Failed."));
			if (d.success) onActed();
		} catch {
			setActMessage("Request failed");
		}
	};

	return (
		<div className="border border-slate-800 rounded-lg bg-slate-900/50 mb-4">
			<button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2 p-3 text-left">
				{open ? <ChevronDown className="w-4 h-4 text-slate-500" /> : <ChevronRight className="w-4 h-4 text-slate-500" />}
				<Sparkles className="w-4 h-4 text-fleet-400" />
				<span className="text-sm font-semibold text-white">Find Work</span>
				<span className="text-xs text-slate-500 ml-2">analyze a repo, or crawl for candidates</span>
			</button>
			{open && (
				<div className="border-t border-slate-800 p-3 space-y-3">
					<div className="flex gap-1.5">
						<button onClick={() => setMode("target")} className={`px-2.5 py-1 rounded text-xs border ${mode === "target" ? "bg-fleet-900/30 border-fleet-600 text-fleet-300" : "bg-slate-800 border-slate-700 text-slate-400"}`}>Target a repo</button>
						<button onClick={() => setMode("crawler")} className={`px-2.5 py-1 rounded text-xs border ${mode === "crawler" ? "bg-fleet-900/30 border-fleet-600 text-fleet-300" : "bg-slate-800 border-slate-700 text-slate-400"}`}>Auto crawler</button>
					</div>

					{mode === "target" && (
						<div className="space-y-2">
							<div className="flex gap-2">
								<input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repo" className="flex-1 bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-fleet-500" />
								<button onClick={runTarget} disabled={busy || !repoUrl.trim()} className="flex items-center gap-1 px-3 py-1.5 bg-fleet-700 hover:bg-fleet-600 disabled:opacity-50 text-white rounded text-xs"><Search className="w-3 h-3" /> Analyze</button>
							</div>
							{busy && <p className="text-xs text-slate-500">Cloning + analyzing (LLM analysis of open issues + a lint scan if the repo isn't instrumented)...</p>}
							{targetReport && <FindingsReport report={targetReport} onAct={(summary, action, issueNumber) => act(repoUrl.trim(), summary, action, issueNumber)} />}
						</div>
					)}

					{mode === "crawler" && (
						<div className="space-y-2">
							<div className="flex gap-2 flex-wrap items-end">
								<div><label className="text-[10px] text-slate-500 uppercase">Language</label><input value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="Python" className="block mt-1 w-24 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<div><label className="text-[10px] text-slate-500 uppercase">Min stars</label><input type="number" value={minStars} onChange={(e) => setMinStars(Number(e.target.value))} className="block mt-1 w-20 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<div><label className="text-[10px] text-slate-500 uppercase">Max stars</label><input type="number" value={maxStars} onChange={(e) => setMaxStars(Number(e.target.value))} className="block mt-1 w-24 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<div><label className="text-[10px] text-slate-500 uppercase">Active (days)</label><input type="number" value={activeDays} onChange={(e) => setActiveDays(Number(e.target.value))} className="block mt-1 w-20 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<div><label className="text-[10px] text-slate-500 uppercase">Topic</label><input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="ai-agent" className="block mt-1 w-28 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<div><label className="text-[10px] text-slate-500 uppercase"># repos</label><input type="number" value={repoLimit} onChange={(e) => setRepoLimit(Number(e.target.value))} className="block mt-1 w-16 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100" /></div>
								<button onClick={runCrawler} disabled={busy} className="flex items-center gap-1 px-3 py-1.5 bg-fleet-700 hover:bg-fleet-600 disabled:opacity-50 text-white rounded text-xs"><Search className="w-3 h-3" /> Crawl</button>
							</div>
							{busy && <p className="text-xs text-slate-500">Searching GitHub, then analyzing each candidate - this can take a minute...</p>}
							{candidates.map((c) => (
								<div key={`${c.owner}/${c.repo}`} className="border border-slate-800 rounded p-2">
									<p className="text-slate-200 text-xs font-medium">{c.owner}/{c.repo} <span className="text-slate-600">({c.stars}★)</span></p>
									<p className="text-slate-500 text-xs mb-1.5">{c.description}</p>
									<FindingsReport report={c.report} onAct={(summary, action, issueNumber) => act(`https://github.com/${c.owner}/${c.repo}`, summary, action, issueNumber)} />
								</div>
							))}
						</div>
					)}

					{actMessage && <p className="text-xs text-fleet-300 bg-fleet-950/30 border border-fleet-800 rounded px-2 py-1.5">{actMessage}</p>}
				</div>
			)}
		</div>
	);
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
		<div className="flex flex-col h-[calc(100vh-7rem)]">
			<FindWorkPanel onActed={fetchContribs} />
			<div className="flex gap-4 flex-1 min-h-0">
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
		</div>
	);
}
