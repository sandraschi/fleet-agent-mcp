import { AlertCircle, Brain, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Card {
	id: string;
	title?: string;
	content: string;
	tags: string[];
	category: string;
	created_at: string;
}

function extractTitle(content: string, fallback: string): string {
	const m = content.match(/^# (.+)$/m);
	return m ? m[1].trim() : fallback;
}

function stripMarkdown(text: string): string {
	return text
		.replace(/^#{1,6}\s+/gm, "")
		.replace(/\|.*\|/g, "")
		.replace(/\*{1,3}/g, "")
		.replace(/`{1,3}/g, "")
		.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
		.replace(/\n{3,}/g, "\n\n")
		.trim();
}

export function Memory() {
	const [cards, setCards] = useState<Card[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [search, setSearch] = useState("");

	const fetchMemory = useCallback(async (query?: string) => {
		setLoading(true);
		setError(null);
		try {
			const url = query
				? `${API_BASE}/api/memory/search?q=${encodeURIComponent(query)}`
				: `${API_BASE}/api/memory`;
			const r = await fetch(url);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			setCards(d.cards ?? []);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Cannot reach backend");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => { fetchMemory(); }, [fetchMemory]);

	const handleSearch = (e: React.FormEvent) => {
		e.preventDefault();
		fetchMemory(search.trim() || undefined);
	};

	return (
		<div className="space-y-6">
			<div className="flex items-center gap-3">
				<Brain className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Memory</h2>
				<div className="flex-1" />

				{/* Search */}
				<form onSubmit={handleSearch} className="flex gap-2">
					<input
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						placeholder="Search cards..."
						className="w-48 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 outline-none focus:border-fleet-500"
					/>
					<button type="submit" className="p-1.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white">
						<Search className="w-3.5 h-3.5" />
					</button>
				</form>

				<button
					onClick={() => fetchMemory()}
					disabled={loading}
					className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors"
				>
					<RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
				</button>
			</div>

			{error && (
				<div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
					<AlertCircle className="w-4 h-4 shrink-0" /> {error}
				</div>
			)}

			{cards.length === 0 && !loading && (
				<p className="text-sm text-slate-500 text-center py-8">
					No memory cards found. Create one via the chat or MCP tools.
				</p>
			)}

			<div className="grid grid-cols-1 gap-3">
				{cards.map((card) => (
					<div key={card.id} className="border border-slate-800 rounded-lg bg-slate-900/50 p-4">
						<h3 className="text-sm font-semibold text-white mb-1">
							{card.title || extractTitle(card.content, card.id)}
						</h3>
						<p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
							{stripMarkdown(card.content).slice(0, 500)}
							{card.content.length > 500 && "..."}
						</p>
						<div className="flex items-center gap-2 mt-3">
							{card.category && (
								<span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">{card.category}</span>
							)}
							{(card.tags || []).map((t) => (
								<button
									key={t}
									onClick={() => { setSearch(t); fetchMemory(t); }}
									className="text-xs bg-fleet-900/50 text-fleet-400 px-2 py-0.5 rounded hover:bg-fleet-800 transition-colors"
								>
									{t}
								</button>
							))}
							<span className="text-xs text-slate-600 ml-auto">
								{new Date(card.created_at).toLocaleDateString()}
							</span>
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
