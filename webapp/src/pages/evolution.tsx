import { AlertCircle, RefreshCw, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface EvoEntry {
	id: string;
	correction: string;
	lesson: string;
	context: string;
	created_at: string;
}

export function Evolution() {
	const [entries, setEntries] = useState<EvoEntry[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const fetchEvolution = async () => {
		setLoading(true);
		try {
			const r = await fetch(API_BASE + "/api/evolution");
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			setEntries(d.entries ?? []);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Cannot reach backend");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		fetchEvolution();
	}, []);

	return (
		<div className="space-y-6">
			<div className="flex items-center gap-3">
				<TrendingUp className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Evolution Log</h2>
				<div className="flex-1" />
				<button
					onClick={fetchEvolution}
					disabled={loading}
					className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors"
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
					{error}
				</div>
			)}

			{entries.length === 0 && !loading && (
				<p className="text-sm text-slate-500">
					No evolution entries yet. Fritz hasn't made any corrections.
				</p>
			)}

			<div className="grid grid-cols-1 gap-3">
				{entries.map((e) => (
					<div
						key={e.id}
						className="border border-slate-800 rounded-lg bg-slate-900/50 p-4"
					>
						<div className="flex items-start gap-3">
							<span className="shrink-0 mt-0.5 w-2 h-2 rounded-full bg-amber-500" />
							<div className="min-w-0">
								<p className="text-sm font-medium text-amber-300">
									{e.correction}
								</p>
								<p className="text-sm text-slate-300 mt-1">
									<span className="text-fleet-400">Lesson:</span> {e.lesson}
								</p>
								{e.context && (
									<p className="text-xs text-slate-500 mt-1">
										Context: {e.context}
									</p>
								)}
								<p className="text-xs text-slate-600 mt-1">
									{new Date(e.created_at).toLocaleString()}
								</p>
							</div>
						</div>
					</div>
				))}
			</div>
		</div>
	);
}
