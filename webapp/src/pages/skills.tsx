import { API_BASE } from "@/lib/api";
import { AlertCircle, RefreshCw, Search, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

interface Skill {
	id: string;
	title?: string;
	content: string;
	tags: string[];
	category: string;
	updated_at?: string;
}

export function SkillsPage() {
	const [skills, setSkills] = useState<Skill[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [notice, setNotice] = useState<string | null>(null);
	const [query, setQuery] = useState("");

	const fetchSkills = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const r = await fetch(`${API_BASE}/api/skills`);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			setSkills(d.skills ?? []);
			if (d.message) setNotice(String(d.message));
		} catch (e) {
			setError(e instanceof Error ? e.message : "Cannot reach backend");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchSkills();
	}, [fetchSkills]);

	const filtered = useMemo(() => {
		const q = query.trim().toLowerCase();
		if (!q) return skills;
		return skills.filter(
			(s) =>
				(s.title ?? "").toLowerCase().includes(q) ||
				s.content.toLowerCase().includes(q) ||
				(s.tags ?? []).some((t) => t.toLowerCase().includes(q)),
		);
	}, [skills, query]);

	return (
		<div className="space-y-6" data-testid="skills-page">
			<div className="flex items-center gap-3">
				<Sparkles className="w-6 h-6 text-fleet-400" />
				<div>
					<h2 className="text-xl font-bold text-white">Skills</h2>
					<p className="text-sm text-slate-400" data-testid="skills-count">
						{skills.length} learned skill{skills.length === 1 ? "" : "s"}
						{notice ? ` â€” ${notice}` : ""}
					</p>
				</div>
				<div className="flex-1" />
				<div className="relative">
					<Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
					<input
						value={query}
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Filter skills..."
						data-testid="skills-search"
						className="w-48 bg-slate-950 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-fleet-500"
					/>
				</div>
				<button
					type="button"
					onClick={fetchSkills}
					disabled={loading}
					data-testid="skills-refresh"
					className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors"
				>
					<RefreshCw
						className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
					/>
					Refresh
				</button>
			</div>

			{loading && (
				<p className="text-sm text-slate-500 text-center py-8">
					Loading skill cards...
				</p>
			)}

			{error && (
				<div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
					<AlertCircle className="w-4 h-4 shrink-0" /> {error}
					<button
						type="button"
						onClick={fetchSkills}
						className="ml-auto text-sm underline hover:text-red-200"
					>
						Retry
					</button>
				</div>
			)}

			{!loading && !error && skills.length === 0 && (
				<div
					className="border border-slate-800 rounded-lg bg-slate-900/50 p-6 text-center"
					data-testid="skills-empty"
				>
					<p className="text-sm text-slate-300 mb-1">
						No skill cards learned yet.
					</p>
					<p className="text-sm text-slate-500">
						Import one with the{" "}
						<code className="font-mono text-fleet-300">
							import_external_skill
						</code>{" "}
						MCP tool, or promote a memory card by tagging it{" "}
						<code className="font-mono text-fleet-300">skill</code>.
					</p>
				</div>
			)}

			{!loading && !error && skills.length > 0 && filtered.length === 0 && (
				<p className="text-sm text-slate-500 text-center py-8">
					No skills match {`"${query.trim()}"`}.
				</p>
			)}

			<div className="grid grid-cols-1 gap-3" data-testid="skills-list">
				{filtered.map((s) => (
					<div
						key={s.id}
						className="border border-slate-800 rounded-lg bg-slate-900/50 p-4"
						data-testid={`skill-card-${s.id}`}
					>
						<h3 className="text-sm font-semibold text-white mb-1">
							{s.title || s.id}
						</h3>
						<p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
							{s.content.slice(0, 600)}
							{s.content.length > 600 && "..."}
						</p>
						<div className="flex items-center gap-2 mt-3 flex-wrap">
							{s.updated_at && (
								<span className="text-[10px] font-mono text-slate-600">
									{s.updated_at}
								</span>
							)}
							{(s.tags ?? []).map((t) => (
								<button
									type="button"
									key={t}
									onClick={() => setQuery(t)}
									className="text-sm bg-fleet-900/50 text-fleet-400 px-2 py-0.5 rounded hover:bg-fleet-800 transition-colors"
								>
									{t}
								</button>
							))}
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
