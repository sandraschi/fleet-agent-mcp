import {
	Check,
	Eye,
	EyeOff,
	RefreshCw,
	Save,
	Settings2,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Settings {
	provider: string;
	base_url: string;
	model: string;
	api_key: string;
	timeout: number;
}

interface ModelInfo {
	name: string;
	size: number;
}

const PROVIDERS = [
	{ id: "ollama", label: "Ollama", defaultUrl: "http://127.0.0.1:11434" },
	{ id: "lmstudio", label: "LM Studio", defaultUrl: "http://127.0.0.1:1234" },
];

export function SettingsPage() {
	const [settings, setSettings] = useState<Settings | null>(null);
	const [models, setModels] = useState<ModelInfo[]>([]);
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [testing, setTesting] = useState(false);
	const [testResult, setTestResult] = useState<{
		ok: boolean;
		msg: string;
	} | null>(null);
	const [showKey, setShowKey] = useState(false);
	const [modelLoading, setModelLoading] = useState(false);
	const [providerOk, setProviderOk] = useState<boolean | null>(null);

	const fetchSettings = useCallback(async () => {
		try {
			const res = await fetch(API_BASE + "/api/settings");
			if (res.ok) setSettings(await res.json());
		} catch {
			/* ignore */
		}
		setLoading(false);
	}, []);

	const fetchModels = useCallback(async () => {
		setModelLoading(true);
		try {
			const res = await fetch(API_BASE + "/api/models");
			if (res.ok) {
				const data = await res.json();
				setModels(data.models ?? []);
				setProviderOk(data.models?.length > 0);
			} else {
				setProviderOk(false);
			}
		} catch {
			setProviderOk(false);
		}
		setModelLoading(false);
	}, []);

	useEffect(() => {
		fetchSettings();
	}, [fetchSettings]);

	useEffect(() => {
		if (settings) fetchModels();
	}, [settings, fetchModels]);

	const handleSave = async () => {
		if (!settings) return;
		setSaving(true);
		try {
			const res = await fetch(API_BASE + "/api/settings", {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(settings),
			});
			if (res.ok) setSettings(await res.json());
		} catch {
			/* ignore */
		}
		setSaving(false);
	};

	const handleTest = async () => {
		setTesting(true);
		setTestResult(null);
		try {
			const res = await fetch(API_BASE + "/api/models");
			if (res.ok) {
				const data = await res.json();
				if (data.models?.length) {
					setTestResult({
						ok: true,
						msg: `Connected — ${data.models.length} models found`,
					});
					setModels(data.models);
				} else {
					setTestResult({ ok: true, msg: "Connected — no models loaded" });
				}
			} else {
				setTestResult({ ok: false, msg: "Connection failed" });
			}
		} catch {
			setTestResult({ ok: false, msg: "Cannot reach provider" });
		}
		setTesting(false);
	};

	const selectProvider = (id: string) => {
		if (!settings) return;
		const prov = PROVIDERS.find((p) => p.id === id);
		setSettings({
			...settings,
			provider: id,
			base_url: prov?.defaultUrl ?? settings.base_url,
		});
		setTestResult(null);
	};

	if (loading) return <div className="text-slate-500 p-8">Loading...</div>;
	if (!settings)
		return <div className="text-red-400 p-8">Failed to load settings</div>;

	return (
		<div className="max-w-2xl space-y-6">
			<div className="flex items-center gap-3">
				<Settings2 className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Settings</h2>
			</div>

			{/* Provider selection */}
			<section className="border border-slate-800 rounded-lg bg-slate-900/50 p-5">
				<h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
					LLM Provider
				</h3>
				<div className="flex items-center gap-3 mb-4">
					{PROVIDERS.map((p) => (
						<button
							key={p.id}
							onClick={() => selectProvider(p.id)}
							className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
								settings.provider === p.id
									? "bg-fleet-900/30 border-fleet-600 text-fleet-300"
									: "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
							}`}
						>
							{p.label}
						</button>
					))}
					<span
						className={`text-xs font-mono ${
							providerOk === true
								? "text-emerald-400"
								: providerOk === false
									? "text-red-400"
									: "text-amber-400"
						}`}
					>
						{providerOk === true
							? `Connected (${models.length} models)`
							: providerOk === false
								? "Offline"
								: "No provider"}
					</span>
				</div>

				<div className="space-y-4">
					<div>
						<label className="text-xs text-slate-500 uppercase tracking-wider">
							Base URL
						</label>
						<input
							type="text"
							value={settings.base_url}
							onChange={(e) =>
								setSettings({ ...settings, base_url: e.target.value })
							}
							className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
						/>
					</div>

					<div className="flex gap-4">
						<div className="flex-1">
							<label className="text-xs text-slate-500 uppercase tracking-wider">
								Model
							</label>
							<div className="flex gap-2">
								<input
									type="text"
									value={settings.model}
									onChange={(e) =>
										setSettings({ ...settings, model: e.target.value })
									}
									placeholder={models[0]?.name ?? "e.g. gemma4:26b"}
									className="flex-1 mt-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
								/>
								<button
									onClick={fetchModels}
									disabled={modelLoading}
									className="mt-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-400 hover:text-white disabled:opacity-50"
									title="Refresh models"
								>
									<RefreshCw
										className={`w-4 h-4 ${modelLoading ? "animate-spin" : ""}`}
									/>
								</button>
							</div>
							{models.length > 0 && (
								<select
									value={settings.model}
									onChange={(e) =>
										setSettings({ ...settings, model: e.target.value })
									}
									className="w-full mt-2 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
								>
									<option value="">— select model —</option>
									{models.map((m) => (
										<option key={m.name} value={m.name}>
											{m.name} ({(m.size / 1e9).toFixed(1)} GB)
										</option>
									))}
								</select>
							)}
						</div>

						<div className="w-32">
							<label className="text-xs text-slate-500 uppercase tracking-wider">
								Timeout (s)
							</label>
							<input
								type="number"
								value={settings.timeout}
								min={5}
								max={300}
								onChange={(e) =>
									setSettings({
										...settings,
										timeout: Number.parseInt(e.target.value) || 60,
									})
								}
								className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
							/>
						</div>
					</div>

					<div>
						<label className="text-xs text-slate-500 uppercase tracking-wider">
							API Key (for OpenAI-compatible)
						</label>
						<div className="flex gap-2 mt-1">
							<input
								type={showKey ? "text" : "password"}
								value={settings.api_key}
								onChange={(e) =>
									setSettings({ ...settings, api_key: e.target.value })
								}
								className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-fleet-500 outline-none"
								placeholder="sk-..."
							/>
							<button
								onClick={() => setShowKey(!showKey)}
								className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 hover:text-white"
							>
								{showKey ? (
									<EyeOff className="w-4 h-4" />
								) : (
									<Eye className="w-4 h-4" />
								)}
							</button>
						</div>
					</div>
				</div>
			</section>

			{/* Actions */}
			<div className="flex gap-3 items-center">
				<button
					onClick={handleSave}
					disabled={saving}
					className="flex items-center gap-2 px-4 py-2 bg-fleet-700 hover:bg-fleet-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
				>
					<Save className="w-4 h-4" />
					{saving ? "Saving..." : "Save"}
				</button>
				<button
					onClick={handleTest}
					disabled={testing}
					className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
				>
					<RefreshCw className={`w-4 h-4 ${testing ? "animate-spin" : ""}`} />
					{testing ? "Testing..." : "Test Connection"}
				</button>

				{testResult && (
					<div
						className={`flex items-center gap-2 text-sm ${testResult.ok ? "text-emerald-400" : "text-red-400"}`}
					>
						{testResult.ok ? (
							<Check className="w-4 h-4" />
						) : (
							<X className="w-4 h-4" />
						)}
						{testResult.msg}
					</div>
				)}
			</div>

			{/* Model quick-pick */}
			{models.length > 0 && (
				<section className="border border-slate-800 rounded-lg bg-slate-900/50 p-5">
					<h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
						Available Models ({models.length})
					</h3>
					<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
						{models.map((m) => (
							<button
								key={m.name}
								onClick={() => setSettings({ ...settings, model: m.name })}
								className={`text-left px-3 py-2 rounded-lg text-sm border transition-colors ${
									settings.model === m.name
										? "bg-fleet-900/30 border-fleet-600 text-fleet-300"
										: "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-600"
								}`}
							>
								<span className="font-mono text-xs">{m.name}</span>
								<span className="text-[10px] text-slate-500 ml-2">
									({(m.size / 1e9).toFixed(1)} GB)
								</span>
							</button>
						))}
					</div>
				</section>
			)}
		</div>
	);
}
