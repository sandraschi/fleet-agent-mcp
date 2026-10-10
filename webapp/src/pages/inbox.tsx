import { API_BASE } from "@/lib/api";
import { AlertCircle, Inbox as InboxIcon, RefreshCw, Send } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface InboxMessage {
	id?: string;
	subject?: string;
	from_entity?: string;
	to_entity?: string;
	created_at?: string;
	body?: string;
}

export function InboxPage() {
	const [messages, setMessages] = useState<InboxMessage[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [hubError, setHubError] = useState<string | null>(null);
	const [entity, setEntity] = useState("fritz");

	const fetchInbox = useCallback(async (forEntity: string) => {
		setLoading(true);
		setError(null);
		setHubError(null);
		try {
			const r = await fetch(
				`${API_BASE}/api/inbox?entity=${encodeURIComponent(forEntity)}`,
			);
			if (!r.ok) throw new Error(`HTTP ${r.status}`);
			const d = await r.json();
			setMessages(d.messages ?? []);
			if (d.error) setHubError(String(d.error));
		} catch (e) {
			setError(e instanceof Error ? e.message : "Cannot reach backend");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchInbox("fritz");
	}, [fetchInbox]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		const trimmed = entity.trim() || "fritz";
		setEntity(trimmed);
		fetchInbox(trimmed);
	};

	return (
		<div className="space-y-6" data-testid="inbox-page">
			<div className="flex items-center gap-3">
				<InboxIcon className="w-6 h-6 text-fleet-400" />
				<div>
					<h2 className="text-xl font-bold text-white">Inbox</h2>
					<p className="text-sm text-slate-400" data-testid="inbox-count">
						{messages.length} unread message{messages.length === 1 ? "" : "s"}{" "}
						for <span className="font-mono text-fleet-300">{entity}</span>
					</p>
				</div>
				<div className="flex-1" />
				<form onSubmit={handleSubmit} className="flex gap-2">
					<input
						value={entity}
						onChange={(e) => setEntity(e.target.value)}
						placeholder="entity (fritz)"
						data-testid="inbox-entity-input"
						className="w-36 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-fleet-500"
					/>
					<button
						type="submit"
						className="p-1.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white"
						title="Poll inbox for this entity"
					>
						<Send className="w-3.5 h-3.5" />
					</button>
				</form>
				<button
					type="button"
					onClick={() => fetchInbox(entity.trim() || "fritz")}
					disabled={loading}
					data-testid="inbox-refresh"
					className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors"
				>
					<RefreshCw
						className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
					/>
					Refresh
				</button>
			</div>

			{loading && (
				<p
					className="text-sm text-slate-500 text-center py-8"
					data-testid="inbox-loading"
				>
					Polling hub inbox...
				</p>
			)}

			{error && (
				<div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
					<AlertCircle className="w-4 h-4 shrink-0" /> {error}
					<button
						type="button"
						onClick={() => fetchInbox(entity.trim() || "fritz")}
						className="ml-auto text-sm underline hover:text-red-200"
					>
						Retry
					</button>
				</div>
			)}

			{!loading && !error && hubError && (
				<div className="flex items-center gap-2 border border-amber-800 rounded-lg bg-amber-950/30 p-3 text-sm text-amber-300">
					<AlertCircle className="w-4 h-4 shrink-0" />
					Hub unreachable ({hubError}) â€” showing last poll result (may be
					empty).
				</div>
			)}

			{!loading && !error && messages.length === 0 && (
				<p
					className="text-sm text-slate-500 text-center py-8"
					data-testid="inbox-empty"
				>
					No unread messages for {entity.trim() || "fritz"}. New hub mentions
					will appear here.
				</p>
			)}

			<div className="grid grid-cols-1 gap-3" data-testid="inbox-list">
				{messages.map((m, i) => (
					<div
						key={m.id ?? `${m.created_at ?? "msg"}-${i}`}
						className="border border-slate-800 rounded-lg bg-slate-900/50 p-4"
					>
						<h3 className="text-sm font-semibold text-white mb-1">
							{m.subject || "(no subject)"}
						</h3>
						<p className="text-[10px] font-mono text-slate-500 mb-2">
							{m.from_entity ?? "?"} â†’ {m.to_entity ?? "?"}
							{m.created_at ? ` Â· ${m.created_at}` : ""}
						</p>
						{m.body && (
							<p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
								{m.body.slice(0, 800)}
								{m.body.length > 800 && "..."}
							</p>
						)}
					</div>
				))}
			</div>
		</div>
	);
}
