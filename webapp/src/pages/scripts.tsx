import {
	AlertCircle,
	Code,
	Play,
	RefreshCw,
	Save,
	Trash2,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Script {
	id: string;
	name: string;
	description: string;
	language: string;
	content: string;
	created_at: string;
	updated_at: string;
}

interface RunResult {
	stdout: string;
	stderr: string;
	result: unknown;
	exit_code: number;
	success: boolean;
}

const KNOWN_SERVERS = [
	"fleet-agent", "git-github", "docs", "memory", "aiwatcher",
	"arxiv", "plex", "email", "discord", "robofang",
	"browser", "cursor", "speech", "opencode", "devices",
];

export function ScriptsPage() {
	const [scripts, setScripts] = useState<Script[]>([]);
	const [loading, setLoading] = useState(true);
	const [_error, setError] = useState<string | null>(null);
	const [selectedId, setSelectedId] = useState<string | null>(null);
	const [editing, setEditing] = useState(false);

	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [language, setLanguage] = useState("python");
	const [content, setContent] = useState("");

	// MCP Call fields
	const [selectedServer, setSelectedServer] = useState("");
	const [serverTools, setServerTools] = useState<{ name: string; description: string; parameters?: Record<string, unknown> }[]>([]);
	const [selectedTool, setSelectedTool] = useState("");
	const [toolParams, setToolParams] = useState<{ key: string; value: string; required?: boolean; type?: string; description?: string }[]>([{ key: "", value: "" }]);
	const [llmAnalyze, setLlmAnalyze] = useState("");
	const [loadingTools, _setLoadingTools] = useState(false);

	// Run/debug
	const [runResult, setRunResult] = useState<RunResult | null>(null);
	const [running, setRunning] = useState(false);

	// AI Generate
	const [showGeneratePrompt, setShowGeneratePrompt] = useState(false);
	const [generatePrompt, setGeneratePrompt] = useState("");
	const [generating, setGenerating] = useState(false);

	const fetchScripts = useCallback(async () => {
		try {
			const r = await fetch(`${API_BASE}/api/scripts`);
			const d = await r.json();
			setScripts(d.scripts ?? []);
		} catch {
			setError("Failed to load scripts");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => { fetchScripts(); }, [fetchScripts]);

	const selectedScript = scripts.find((s) => s.id === selectedId);

	const handleSelect = (s: Script) => {
		setSelectedId(s.id);
		setEditing(false);
		setRunResult(null);
	};

	const handleEdit = (s: Script) => {
		setSelectedId(s.id);
		setName(s.name);
		setDescription(s.description);
		setLanguage(s.language);
		setContent(s.content);
		if (s.language === "mcp_call") {
			try {
				const spec = JSON.parse(s.content);
				setSelectedServer(spec.server || "");
				setSelectedTool(spec.tool || "");
				const params = spec.params || {};
				setToolParams(Object.entries(params).map(([k, v]) => ({ key: k, value: String(v) })));
				if (toolParams.length === 0) setToolParams([{ key: "", value: "" }]);
				setLlmAnalyze(spec.llm_analyze || "");
			} catch {
				setSelectedServer("");
				setSelectedTool("");
				setToolParams([{ key: "", value: "" }]);
			}
		}
		setEditing(true);
	};

	const handleNew = () => {
		setSelectedId(null);
		setName("");
		setDescription("");
		setLanguage("python");
		setContent("");
		setSelectedServer("");
		setSelectedTool("");
		setToolParams([{ key: "", value: "" }]);
		setLlmAnalyze("");
		setRunResult(null);
		setEditing(true);
	};

	const saveScript = async () => {
		let finalContent = content;
		if (language === "mcp_call") {
			const params: Record<string, string> = {};
			for (const p of toolParams) {
				if (p.key.trim()) params[p.key.trim()] = p.value;
			}
			const spec: Record<string, unknown> = { server: selectedServer, tool: selectedTool, params };
			if (llmAnalyze.trim()) spec.llm_analyze = llmAnalyze.trim();
			finalContent = JSON.stringify(spec, null, 2);
		}

		const body: Record<string, string> = {
			name, description, language,
			content: finalContent,
		};

		try {
			let r: Response;
			if (selectedId) {
				r = await fetch(`${API_BASE}/api/scripts/${selectedId}`, {
					method: "PUT",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				});
			} else {
				r = await fetch(`${API_BASE}/api/scripts`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify(body),
				});
			}
			if (r.ok) {
				setEditing(false);
				fetchScripts();
			}
		} catch {
			setError("Failed to save script");
		}
	};

	const handleGenerate = async () => {
		if (!generatePrompt.trim() || generating) return;
		setGenerating(true);
		setShowGeneratePrompt(false);
		try {
			const r = await fetch(`${API_BASE}/api/scripts/generate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ prompt: generatePrompt }),
			});
			const d = await r.json();
			if (d.success) {
				setName(d.name || "Generated Script");
				setDescription(d.description || "");
				setLanguage(d.language || "python");
				setContent(d.content || "");
				if (d.language === "mcp_call") {
					try {
						const spec = JSON.parse(d.content);
						setSelectedServer(spec.server || "");
						setSelectedTool(spec.tool || "");
						const params = spec.params || {};
						const entries = Object.entries(params);
						setToolParams(entries.length > 0 ? entries.map(([k, v]) => ({ key: k, value: String(v) })) : [{ key: "", value: "" }]);
						setLlmAnalyze(spec.llm_analyze || "");
					} catch {
						/* JSON parse failed — keep raw content */
					}
				}
			} else {
				setError(d.message || "Generation failed");
			}
		} catch {
			setError("Failed to generate script");
		}
		setGenerating(false);
	};

	const deleteScript = async (id: string) => {
		try {
			await fetch(`${API_BASE}/api/scripts/${id}`, { method: "DELETE" });
			if (selectedId === id) { setSelectedId(null); setEditing(false); }
			fetchScripts();
		} catch {
			setError("Failed to delete script");
		}
	};

	const runScript = async () => {
		if (!selectedId) return;
		setRunning(true);
		setRunResult(null);
		try {
			const r = await fetch(`${API_BASE}/api/scripts/${selectedId}/run`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
			});
			const d = await r.json();
			setRunResult({
				stdout: d.stdout || "",
				stderr: d.stderr || "",
				result: d.result,
				exit_code: d.exit_code ?? -1,
				success: d.success,
			});
		} catch {
			setRunResult({ stdout: "", stderr: "Run failed", result: null, exit_code: -1, success: false });
		}
		setRunning(false);
	};

	const fetchServerTools = async (server: string) => {
		if (!server) return;
		_setLoadingTools(true);
		setSelectedTool("");
		setToolParams([{ key: "", value: "" }]);
		try {
			const r = await fetch(`${API_BASE}/api/fleet/list-tools`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ server }),
			});
			const d = await r.json();
			setServerTools(d.tools || []);
		} catch {
			setServerTools([]);
		}
		_setLoadingTools(false);
	};

	const handleServerChange = (s: string) => {
		setSelectedServer(s);
		setSelectedTool("");
		setToolParams([{ key: "", value: "" }]);
		fetchServerTools(s);
	};

	const handleToolChange = (toolName: string) => {
		setSelectedTool(toolName);
		const tool = serverTools.find((t) => t.name === toolName);
		if (tool?.parameters) {
			const schema = tool.parameters as Record<string, unknown>;
			const props = (schema.properties as Record<string, unknown>) || {};
			const required = (schema.required as string[]) || [];
			const entries = Object.entries(props).map(([k, v]) => {
				const meta = v as Record<string, unknown>;
				return {
					key: k,
					value: meta.default !== undefined ? String(meta.default) : "",
					required: required.includes(k),
					type: String(meta.type || "string"),
					description: String(meta.description || ""),
				};
			});
			setToolParams(entries.length > 0 ? entries : [{ key: "", value: "" }]);
		} else {
			setToolParams([{ key: "", value: "" }]);
		}
	};

	const updateParam = (idx: number, key: string, value: string) => {
		const next = [...toolParams];
		next[idx] = { key, value };
		setToolParams(next);
	};

	const addParam = () => setToolParams([...toolParams, { key: "", value: "" }]);
	const removeParam = (idx: number) => {
		if (toolParams.length <= 1) return;
		setToolParams(toolParams.filter((_, i) => i !== idx));
	};

	const langColor = (l: string) =>
		l === "python" ? "text-blue-400" :
		l === "shell" ? "text-green-400" :
		l === "powershell" ? "text-purple-400" :
		l === "mcp_call" ? "text-amber-400" : "text-slate-400";

	return (
		<div className="flex gap-4 h-[calc(100vh-7rem)]">
			{/* Script list sidebar */}
			<div className="w-64 shrink-0 flex flex-col border border-slate-800 rounded-lg bg-slate-900/50 overflow-hidden">
				<div className="flex items-center gap-2 p-3 border-b border-slate-800">
					<Code className="w-4 h-4 text-fleet-400" />
					<span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Scripts</span>
					<div className="flex-1" />
					<button onClick={handleNew} className="text-xs text-fleet-400 hover:text-fleet-300 bg-fleet-900/30 border border-fleet-800 rounded px-2 py-0.5">+ New</button>
					<button onClick={fetchScripts} disabled={loading} className="text-xs text-slate-500 hover:text-white"><RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /></button>
				</div>
				<div className="flex-1 overflow-y-auto p-2 space-y-1">
					{scripts.map((s) => (
						<div
							key={s.id}
							onClick={() => handleSelect(s)}
							className={`p-2 rounded-lg cursor-pointer text-sm border transition-colors ${
								selectedId === s.id
									? "bg-slate-800 border-slate-700 text-white"
									: "border-transparent text-slate-400 hover:bg-slate-800/50 hover:border-slate-800"
							}`}
						>
							<p className="truncate font-medium">{s.name}</p>
							<div className="flex items-center gap-2 mt-0.5">
								<span className={`text-[10px] uppercase ${langColor(s.language)}`}>{s.language}</span>
								{s.description && <span className="text-[10px] text-slate-600 truncate">{s.description}</span>}
							</div>
						</div>
					))}
					{!loading && scripts.length === 0 && (
						<p className="text-xs text-slate-600 text-center py-4">No scripts. Create one.</p>
					)}
				</div>
			</div>

			{/* Editor / Detail panel */}
			<div className="flex-1 flex flex-col border border-slate-800 rounded-lg bg-slate-900/50 overflow-hidden">
				{!selectedId && !editing && (
					<div className="flex-1 flex items-center justify-center text-slate-600">
						<p className="text-sm">Select a script or create a new one</p>
					</div>
				)}

				{editing && (
					<div className="flex-1 flex flex-col overflow-hidden">
						<div className="flex items-center gap-3 p-3 border-b border-slate-800 flex-wrap">
							<input
								value={name}
								onChange={(e) => setName(e.target.value)}
								placeholder="Script name"
								className="bg-transparent border-b border-slate-700 px-2 py-1 text-sm text-slate-200 focus:border-fleet-500 outline-none min-w-[200px]"
								autoFocus
							/>
							<select
								value={language}
								onChange={(e) => setLanguage(e.target.value)}
								className="bg-zinc-800 text-zinc-100 border-zinc-600 rounded px-2 py-1 text-xs"
							>
								<option value="python">Python</option>
								<option value="shell">Shell</option>
								<option value="powershell">PowerShell</option>
								<option value="mcp_call">MCP Call</option>
							</select>
							<input
								value={description}
								onChange={(e) => setDescription(e.target.value)}
								placeholder="Description (optional)"
								className="flex-1 bg-transparent border-b border-slate-700 px-2 py-1 text-xs text-slate-400 focus:border-slate-500 outline-none min-w-[150px]"
							/>
							<div className="flex gap-1">
								<button onClick={saveScript} className="flex items-center gap-1 px-3 py-1.5 bg-fleet-700 hover:bg-fleet-600 text-white rounded text-xs"><Save className="w-3 h-3" /> Save</button>
								<button onClick={() => setShowGeneratePrompt(!showGeneratePrompt)} className="flex items-center gap-1 px-3 py-1.5 bg-amber-700 hover:bg-amber-600 text-white rounded text-xs"><Zap className="w-3 h-3" /> AI</button>
								<button onClick={() => setEditing(false)} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs">Cancel</button>
							</div>
						</div>

						{/* AI Generate prompt */}
						{showGeneratePrompt && (
							<div className="border-b border-slate-800 p-3 bg-slate-950/50">
								<p className="text-[10px] text-amber-500 uppercase tracking-wider mb-2 flex items-center gap-1">
									<Zap className="w-3 h-3" /> Generate with AI — describe what you want
								</p>

								{/* Prompt idea pills */}
								<div className="flex flex-wrap gap-1.5 mb-2">
									{[
										"Check all fleet servers health and summarize",
										"List pending high-priority tasks and suggest which to do first",
										"Search memory cards for anything about FastMCP 3.2",
										"Get latest arXiv papers on RLHF and summarize them",
										"Sync Plex RAG index then search for Nolan films",
										"Check git status and uncommitted changes on all fleet repos",
										"Pull latest from all fleet repos and report stale branches",
										"Every 2h, check cursor spend and alert if over $20",
										"Daily 7am: fleet pulse, inbox briefing, then write intel report",
										"Check devices-mcp for CO/smoke alerts and email if critical",
										"Search GitHub for open PRs needing review across the fleet",
										"Friday 5pm: generate weekly report PDF and email it",
									].map((idea) => (
										<button
											key={idea}
											type="button"
											onClick={() => setGeneratePrompt(idea)}
											className={`px-2 py-1 rounded text-[10px] border transition-colors ${
												generatePrompt === idea
													? "bg-amber-900/30 border-amber-700 text-amber-300"
													: "bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600"
											}`}
										>
											{idea.length > 45 ? idea.slice(0, 42) + "..." : idea}
										</button>
									))}
								</div>

								<div className="flex gap-2">
									<input
										value={generatePrompt}
										onChange={(e) => setGeneratePrompt(e.target.value)}
										onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
										placeholder="Or type your own prompt..."
										className="flex-1 bg-slate-900 border border-slate-700 rounded px-3 py-2 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-amber-600"
										autoFocus
									/>
									<button
										onClick={handleGenerate}
										disabled={generating || !generatePrompt.trim()}
										className="px-3 py-2 bg-amber-700 hover:bg-amber-600 disabled:bg-slate-800 text-white rounded text-xs disabled:opacity-50 flex items-center gap-1"
									>
										{generating ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
										Generate
									</button>
								</div>
							</div>
						)}

						<div className="flex-1 overflow-auto p-3">
							{language === "mcp_call" ? (
								<div className="space-y-3">
									<div className="flex gap-3">
										<div className="flex-1">
											<label className="text-[10px] text-slate-500 uppercase tracking-wider">Server</label>
											<select
												value={selectedServer}
												onChange={(e) => handleServerChange(e.target.value)}
												className="w-full mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded px-2 py-1.5 text-xs"
											>
												<option value="">-- Select server --</option>
												{KNOWN_SERVERS.map((s) => <option key={s} value={s}>{s}</option>)}
											</select>
										</div>
										<div className="flex-1">
											<label className="text-[10px] text-slate-500 uppercase tracking-wider">Tool {loadingTools && <span className="text-amber-400">(loading...)</span>}</label>
											<select
												value={selectedTool}
												onChange={(e) => handleToolChange(e.target.value)}
												disabled={serverTools.length === 0}
												className="w-full mt-1 bg-zinc-800 text-zinc-100 border-zinc-600 rounded px-2 py-1.5 text-xs disabled:opacity-50"
											>
												<option value="">-- Select tool --</option>
												{serverTools.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
											</select>
										</div>
									</div>

									{selectedTool && (
										<div>
											<label className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Parameters</label>
											{toolParams.length > 0 && (
												<div className="border border-slate-800 rounded-lg bg-slate-950/30 divide-y divide-slate-800">
													{toolParams.map((p, i) => (
														<div key={i} className="px-3 py-2 space-y-1">
															<div className="flex items-center gap-2">
																<span className="text-xs font-mono text-slate-200 min-w-[100px]">
																	{p.required && <span className="text-red-400 mr-0.5">*</span>}
																	{p.key || <span className="text-slate-600 italic">key</span>}
																</span>
																{p.type && (
																	<span className="text-[10px] font-mono text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">
																		{p.type}
																	</span>
																)}
																<div className="flex-1" />
																<button
																	onClick={() => removeParam(i)}
																	className="text-slate-600 hover:text-red-400 text-xs"
																	title="Remove param"
																>
																	{p.required ? <span className="text-slate-600 cursor-default text-[10px]">required</span> : "x"}
																</button>
															</div>
															{p.description && (
																<p className="text-[10px] text-slate-600 italic leading-tight">{p.description}</p>
															)}
															<div className="flex gap-2">
																<input
																	value={p.key}
																	onChange={(e) => updateParam(i, e.target.value, p.value)}
																	placeholder="key"
																	readOnly={!!p.required}
																	className={`w-28 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 font-mono outline-none focus:border-fleet-500 ${p.required ? "opacity-60" : ""}`}
																/>
																<input
																	value={p.value}
																	onChange={(e) => updateParam(i, p.key, e.target.value)}
																	placeholder="value"
																	className="flex-1 bg-zinc-800 border-zinc-600 rounded px-2 py-1 text-xs text-zinc-100 outline-none focus:border-fleet-500"
																/>
															</div>
														</div>
													))}
												</div>
											)}
											{!toolParams.some((p) => p.required) && (
												<button onClick={addParam} className="mt-1.5 text-xs text-fleet-500 hover:text-fleet-400">+ Add param</button>
											)}
										</div>
									)}

									{/* MCP Call JSON preview */}
									{selectedServer && selectedTool && (
										<div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
											<p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Generated</p>
											<pre className="text-xs text-slate-400 font-mono whitespace-pre-wrap">
												{JSON.stringify({
													server: selectedServer,
													tool: selectedTool,
													params: Object.fromEntries(toolParams.filter((p) => p.key.trim()).map((p) => [p.key.trim(), p.value])),
													...(llmAnalyze.trim() ? { llm_analyze: llmAnalyze.trim() } : {}),
												}, null, 2)}
											</pre>
										</div>
									)}

									{/* LLM Analysis */}
									{selectedTool && (
										<div>
											<label className="text-[10px] text-slate-500 uppercase tracking-wider flex items-center gap-1">
												AI Analysis <span className="text-slate-600 font-normal">(optional — Fritz analyzes the tool result)</span>
											</label>
											<textarea
												value={llmAnalyze}
												onChange={(e) => setLlmAnalyze(e.target.value)}
												placeholder='e.g. "Summarize the pending tasks by priority and suggest which to act on first"'
												rows={2}
												className="w-full mt-1 bg-zinc-800 border-zinc-600 rounded px-2 py-1.5 text-xs text-zinc-200 placeholder-zinc-600 resize-none outline-none focus:border-fleet-500"
											/>
										</div>
									)}
								</div>
							) : (
								<textarea
									value={content}
									onChange={(e) => setContent(e.target.value)}
									placeholder={language === "python" ? "# Python script\nprint('hello')" : language === "powershell" ? "# PowerShell script\nWrite-Output 'hello'" : "# Shell script\necho hello"}
									spellCheck={false}
									className="w-full h-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 font-mono resize-none outline-none focus:border-fleet-500"
								/>
							)}
						</div>
					</div>
				)}

				{/* View mode */}
				{selectedScript && !editing && (
					<div className="flex-1 flex flex-col overflow-hidden">
						<div className="flex items-center gap-3 p-3 border-b border-slate-800 flex-wrap">
							<Code className="w-4 h-4 text-fleet-400" />
							<span className="text-sm font-semibold text-white">{selectedScript.name}</span>
							<span className={`text-[10px] uppercase ${langColor(selectedScript.language)}`}>{selectedScript.language}</span>
							{selectedScript.description && <span className="text-xs text-slate-500">{selectedScript.description}</span>}
							<div className="flex-1" />
							<button onClick={() => handleEdit(selectedScript)} className="text-xs text-slate-400 hover:text-white bg-slate-800 border border-slate-700 rounded px-2 py-1">Edit</button>
							<button onClick={() => runScript()} disabled={running} className="flex items-center gap-1 text-xs text-emerald-400 hover:text-emerald-300 bg-emerald-950/30 border border-emerald-800 rounded px-2 py-1 disabled:opacity-50">
								{running ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
								Run
							</button>
							<button onClick={() => deleteScript(selectedScript.id)} className="text-xs text-red-400 hover:text-red-300 bg-red-950/30 border border-red-800 rounded px-2 py-1"><Trash2 className="w-3 h-3" /></button>
						</div>

						<div className="flex-1 overflow-auto p-3">
							{selectedScript.language === "mcp_call" ? (
								<div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
									<p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">MCP Call Payload</p>
									<pre className="text-xs text-slate-300 font-mono whitespace-pre-wrap">{selectedScript.content}</pre>
								</div>
							) : (
								<pre className="w-full h-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm text-slate-200 font-mono overflow-auto whitespace-pre-wrap">{selectedScript.content}</pre>
							)}
						</div>

						{/* Run result panel */}
						{runResult && (
							<div className="border-t border-slate-800">
								<div className={`flex items-center gap-2 px-3 py-2 text-xs ${runResult.success ? "bg-emerald-950/20 text-emerald-400" : "bg-red-950/20 text-red-400"}`}>
									{runResult.success ? <Zap className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
									Exit code: {runResult.exit_code}
									<span className="text-slate-600">|</span>
									{(runResult.result as string) && <span className="text-slate-400">Result: {typeof runResult.result === "string" ? runResult.result : JSON.stringify(runResult.result).slice(0, 200)}</span>}
								</div>
								{(runResult.stdout as string || runResult.stderr as string) && (
									<div className="max-h-48 overflow-auto p-3 bg-slate-950 font-mono text-xs space-y-1">
										{(runResult.stdout as string) && <pre className="text-emerald-300 whitespace-pre-wrap">{(runResult.stdout as string)}</pre>}
										{(runResult.stderr as string) && <pre className="text-red-300 whitespace-pre-wrap">{(runResult.stderr as string)}</pre>}
									</div>
								)}
								{!(runResult.stdout as string) && !(runResult.stderr as string) && !runResult.result && (
									<div className="p-3 text-xs text-slate-600 bg-slate-950">No output</div>
								)}
							</div>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
