import { Activity, GitBranch, Brain, ListChecks, TrendingUp, ExternalLink } from "lucide-react";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const STATS = [
  { icon: GitBranch, label: "Workflows", value: "3", sub: "daily, contribution, learning", route: "/tools" },
  { icon: ListChecks, label: "Tools", value: "21", sub: "7 subsystems", route: "/tools" },
  { icon: Brain, label: "Subsystems", value: "7", sub: "flowforge, pulse, memory, identity, teleport, evolution, heartbeat", route: "/tools" },
  { icon: Activity, label: "Ports", value: "10996/10997", sub: "backend / frontend", route: "/status" },
  { icon: TrendingUp, label: "Inspiration", value: "kagura-agent", sub: "887+ PRs, 52 repos", route: null },
];

interface Whoami {
  name: string;
  human: string;
  soul_preview: string;
  north_star_preview: string;
}

export function Dashboard() {
  const navigate = useNavigate();
  const [now, setNow] = useState(new Date());
  const [whoami, setWhoami] = useState<Whoami | null>(null);
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch("/api/whoami")
      .then((r) => r.json())
      .then((d) => { setWhoami(d.identity ?? d); setBackendOnline(true); })
      .catch(() => setBackendOnline(false));
  }, []);

  return (
    <div className="space-y-8">
      {/* Header with live agent name */}
      <div className="flex items-center gap-4">
        <span className="text-3xl">🌸</span>
        <div>
          <h2 className="text-2xl font-bold text-white">
            {whoami?.name ?? "Lumen"}
          </h2>
          <p className="text-sm text-slate-400">
            {backendOnline ? `Partnered with ${whoami?.human ?? "Sandra"} · ` : ""}
            {now.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </p>
        </div>
        <div className="flex-1" />
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
          Backend offline — start with <code className="bg-amber-900/50 px-1 rounded">.\start.ps1</code> for live agent data
        </div>
      )}

      {/* North star preview */}
      {whoami?.north_star_preview && (
        <div className="border border-fleet-800/50 rounded-lg bg-fleet-950/20 p-4">
          <p className="text-xs text-fleet-500 uppercase tracking-wider mb-1">North Star</p>
          <p className="text-sm text-fleet-300 italic">{whoami.north_star_preview}</p>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            onClick={() => stat.route ? navigate(stat.route) : window.open("https://github.com/kagura-agent", "_blank")}
            className="border border-slate-800 rounded-lg bg-slate-900/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-slate-800">
                <stat.icon className="w-5 h-5 text-fleet-400" />
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider">{stat.label}</p>
                <p className="text-lg font-semibold text-white">{stat.value}</p>
                <p className="text-xs text-slate-400">{stat.sub}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Architecture diagram */}
      <div className="border border-slate-800 rounded-lg bg-slate-900/50 p-6">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Architecture</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
          <div onClick={() => navigate("/tools")} className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer">
            <GitBranch className="w-6 h-6 text-fleet-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-white">FlowForge</p>
            <p className="text-xs text-slate-400">State machine - <em>what</em> to do</p>
          </div>
          <div onClick={() => navigate("/status")} className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer">
            <Activity className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-white">Heartbeat</p>
            <p className="text-xs text-slate-400">Coordinator - <em>when</em> to do it</p>
          </div>
          <div onClick={() => navigate("/tools")} className="border border-slate-700 rounded-lg bg-slate-800/50 p-4 hover:border-fleet-600 transition-colors cursor-pointer">
            <Brain className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-white">Sub-agent</p>
            <p className="text-xs text-slate-400">Worker - <em>does</em> the work</p>
          </div>
        </div>
        <div className="flex items-center justify-center gap-2 mt-4 text-xs text-slate-500 flex-wrap">
          <span className="bg-slate-800 px-2 py-1 rounded">cron (30 min)</span>
          <span className="text-slate-600">→</span>
          <span className="bg-slate-800 px-2 py-1 rounded">heartbeat_wake()</span>
          <span className="text-slate-600">→</span>
          <span className="bg-slate-800 px-2 py-1 rounded">workflow_status()</span>
          <span className="text-slate-600">→</span>
          <span className="bg-slate-800 px-2 py-1 rounded">execute</span>
        </div>
      </div>

      {/* Quick start */}
      <div className="border border-slate-800 rounded-lg bg-slate-900/50 p-6">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Quick Start</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-slate-500 mb-2">Backend + Webapp</p>
            <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm font-mono text-slate-300">.\start.ps1</pre>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-2">Webapp only (Vite dev)</p>
            <pre className="bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm font-mono text-slate-300">just start-webapp</pre>
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
