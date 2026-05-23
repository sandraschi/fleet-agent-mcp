import { useState, useEffect } from "react";
import { Brain, RefreshCw, AlertCircle } from "lucide-react";

interface Card {
  id: string;
  content: string;
  tags: string[];
  created_at: string;
}

export function Memory() {
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMemory = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/memory");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setCards(d.cards ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cannot reach backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMemory(); }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Brain className="w-6 h-6 text-fleet-400" />
        <h2 className="text-xl font-bold text-white">Memory</h2>
        <div className="flex-1" />
        <button onClick={fetchMemory} disabled={loading}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 border border-red-800 rounded-lg bg-red-950/50 p-3 text-sm text-red-300">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {cards.length === 0 && !loading && (
        <p className="text-sm text-slate-500">No memory cards yet. Fritz hasn't learned anything.</p>
      )}

      <div className="grid grid-cols-1 gap-3">
        {cards.map((card) => (
          <div key={card.id} className="border border-slate-800 rounded-lg bg-slate-900/50 p-4">
            <pre className="text-sm text-slate-300 whitespace-pre-wrap font-sans">{card.content}</pre>
            <div className="flex items-center gap-2 mt-2">
              {card.tags?.map((t) => (
                <span key={t} className="text-xs bg-fleet-900/50 text-fleet-400 px-2 py-0.5 rounded">{t}</span>
              ))}
              <span className="text-xs text-slate-600 ml-auto">{new Date(card.created_at).toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
