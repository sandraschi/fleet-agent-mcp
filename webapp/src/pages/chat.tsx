import { Bot, Download, Send, Terminal, Trash2, User } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Message {
	role: "user" | "assistant" | "system";
	content: string;
	ts?: string;
}

const PERSONALITIES: { id: string; name: string; prompt: string }[] = [
	{
		id: "fritz",
		name: "Fritz (Default)",
		prompt:
			"You are Fritz, a proactive fleet conductor agent. Be direct, technical, and concise. Lead with action. Use bullet points for multi-step answers.",
	},
	{
		id: "research",
		name: "Research Assistant",
		prompt:
			"You are a research analyst. Provide thorough, well-structured analysis with citations and references. Explore multiple perspectives before concluding.",
	},
	{
		id: "reviewer",
		name: "Expert Reviewer",
		prompt:
			"You are a senior code reviewer. Be critical but constructive. Point out specific issues, suggest fixes, and explain the reasoning behind each observation.",
	},
	{
		id: "summarizer",
		name: "Quick Summarizer",
		prompt:
			"You are a concise summarizer. Respond in 3-5 bullet points max. Lead with the most important insight. Omit fluff and pleasantries.",
	},
	{
		id: "custom",
		name: "Custom",
		prompt: "",
	},
];

const EXAMPLE_PROMPTS = [
	{ label: "Fleet Pulse", text: "Run the morning fleet pulse report" },
	{ label: "Workflows", text: "List all registered workflows and their status" },
	{ label: "Tasks", text: "Show my pending high-priority tasks" },
	{ label: "Knowledge", text: "Search memory cards for FastMCP patterns" },
	{ label: "Evolution", text: "Show me recent corrections from the evolution log" },
	{ label: "Health", text: "Check the arxiv + aiwatcher pipeline health" },
];

const STORAGE_KEY = "fleet-agent-chat-history";
const PERSONALITY_KEY = "fleet-agent-chat-personality";

function loadMessages(): Message[] {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (raw) {
			const msgs = JSON.parse(raw) as Message[];
			return msgs.slice(-100);
		}
	} catch {
		/* corrupt storage */
	}
	return [];
}

function saveMessages(messages: Message[]) {
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-100)));
	} catch {
		/* storage full */
	}
}

function buildSystemPrompt(
	personalityId: string,
	personalityPrompt: string,
	customPrompt: string,
): string {
	if (personalityId === "custom") return customPrompt || "You are Fritz, a fleet conductor agent.";
	return `You are a fleet conductor agent assisting Sandra with her MCP server fleet.\n\n---\n\n## Role\n${personalityPrompt}`;
}

export function ChatPage() {
	const [messages, setMessages] = useState<Message[]>(loadMessages);
	const [input, setInput] = useState("");
	const [streaming, setStreaming] = useState(false);
	const [model, setModel] = useState("");
	const [models, setModels] = useState<string[]>([]);
	const [error, setError] = useState<string | null>(null);
	const [providerOk, setProviderOk] = useState<boolean | null>(null);
	const [personalityId, setPersonalityId] = useState(() => {
		try {
			return localStorage.getItem(PERSONALITY_KEY) || "fritz";
		} catch {
			return "fritz";
		}
	});
	const [customPrompt, setCustomPrompt] = useState("");
	const bottomRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLTextAreaElement>(null);

	const personality = PERSONALITIES.find((p) => p.id === personalityId) || PERSONALITIES[0];

	useEffect(() => {
		try {
			localStorage.setItem(PERSONALITY_KEY, personalityId);
		} catch {
			/* ignore */
		}
	}, [personalityId]);

	useEffect(() => {
		fetch(`${API_BASE}/api/settings`)
			.then((r) => r.json())
			.then((s) => {
				if (s.model) setModel(s.model);
				if (s.base_url) setProviderOk(true);
			})
			.catch(() => setProviderOk(false));
		fetch(`${API_BASE}/api/models`)
			.then((r) => r.json())
			.then((d) => {
				setModels((d.models ?? []).map((m: { name: string }) => m.name));
				setProviderOk(true);
			})
			.catch(() => setProviderOk(null));
	}, []);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [messages]);

	const sendMessage = useCallback(async () => {
		const text = input.trim();
		if (!text || streaming) return;
		setInput("");
		setError(null);

		const userMsg: Message = { role: "user", content: text, ts: new Date().toISOString() };
		const updated = [...messages, userMsg];
		setMessages(updated);
		saveMessages(updated);
		setStreaming(true);

		const assistantMsg: Message = { role: "assistant", content: "" };
		setMessages((prev) => [...prev, assistantMsg]);

		const systemPrompt = buildSystemPrompt(personalityId, personality.prompt, customPrompt);

		try {
			const res = await fetch(`${API_BASE}/api/chat`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					messages: [
						{ role: "system", content: systemPrompt },
						...updated,
					],
					model: model || undefined,
				}),
			});

			if (!res.ok) {
				const errText = await res.text().catch(() => `HTTP ${res.status}`);
				throw new Error(errText);
			}

			const reader = res.body?.getReader();
			if (!reader) throw new Error("No response body");

			const decoder = new TextDecoder();
			let buffer = "";

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split("\n");
				buffer = lines.pop() ?? "";

				for (const line of lines) {
					if (!line.startsWith("data: ")) continue;
					try {
						const data = JSON.parse(line.slice(6));
						if (data.c) {
							setMessages((prev) => {
								const last = [...prev];
								const idx = last.length - 1;
								if (last[idx]?.role === "assistant") {
									last[idx] = {
										...last[idx],
										content: last[idx].content + data.c,
									};
								}
								return last;
							});
						}
						if (data.done) {
							setMessages((prev) => {
								saveMessages(prev);
								return prev;
							});
							setStreaming(false);
						}
						if (data.error) {
							setError(data.error);
							setStreaming(false);
						}
					} catch {
						/* skip parse errors */
					}
				}
			}
		} catch (e) {
			const errMsg = e instanceof Error ? e.message : "Chat failed";
			setError(errMsg);
			setStreaming(false);
		}
	}, [input, streaming, messages, model, personalityId, personality, customPrompt]);

	const handleSend = () => sendMessage();

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	};

	const clearChat = () => {
		setMessages([]);
		setError(null);
		try {
			localStorage.removeItem(STORAGE_KEY);
		} catch {
			/* ignore */
		}
		inputRef.current?.focus();
	};

	const exportChat = () => {
		if (messages.length === 0) return;
		const lines = messages.map((m) => {
			const ts = m.ts ? `[${new Date(m.ts).toLocaleString()}] ` : "";
			return `${ts}${m.role === "user" ? "You" : "Fritz"}: ${m.content}`;
		});
		const blob = new Blob([lines.join("\n\n")], { type: "text/plain" });
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `fleet-agent-chat-${new Date().toISOString().slice(0, 19)}.txt`;
		a.click();
		URL.revokeObjectURL(url);
	};

	const handlePersonalityChange = (id: string) => {
		setPersonalityId(id);
		if (id !== "custom") setCustomPrompt("");
	};

	const providerLabel =
		providerOk === true
			? "Connected"
			: providerOk === false
				? "Offline"
				: "Detecting...";

	const providerColor = providerOk === true ? "text-emerald-400" : providerOk === false ? "text-red-400" : "text-amber-400";

	return (
		<div className="flex flex-col h-[calc(100vh-7rem)]" data-testid="chat-page">
			{/* Controls bar */}
			<div className="flex items-center gap-3 mb-4 shrink-0 flex-wrap" data-testid="chat-controls">
				<Bot className="w-6 h-6 text-fleet-400" />
				<h2 className="text-xl font-bold text-white">Chat</h2>
				<div className="flex-1" />

				{/* Provider status */}
				<span className={`text-xs font-mono ${providerColor}`} data-testid="provider-status">
					{providerLabel}
				</span>

				{/* Model select */}
				<select
					value={model}
					onChange={(e) => setModel(e.target.value)}
					className="bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs font-mono focus:border-fleet-500 outline-none"
					data-testid="chat-model"
				>
					<option value="">Default model</option>
					{models.map((m) => (
						<option key={m} value={m}>
							{m}
						</option>
					))}
				</select>

				{/* Personality select */}
				<select
					value={personalityId}
					onChange={(e) => handlePersonalityChange(e.target.value)}
					data-testid="personality-select"
					className="bg-zinc-800 text-zinc-100 border-zinc-600 rounded-lg px-2 py-1.5 text-xs font-mono focus:border-fleet-500 outline-none"
				>
					{PERSONALITIES.map((p) => (
						<option key={p.id} value={p.id}>
							{p.name}
						</option>
					))}
				</select>

				{/* Export */}
				<button
					onClick={exportChat}
					disabled={messages.length === 0}
					data-testid="chat-export"
					className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
						messages.length === 0
							? "bg-slate-900 border border-slate-800 text-slate-600 cursor-not-allowed"
							: "bg-slate-900 border border-slate-700 text-slate-400 hover:text-white"
					}`}
				>
					<Download className="w-3.5 h-3.5" />
					Export
				</button>

				{/* Clear */}
				<button
					onClick={clearChat}
					disabled={messages.length === 0}
					data-testid="chat-clear"
					className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
						messages.length === 0
							? "bg-slate-900 border border-slate-800 text-slate-600 cursor-not-allowed"
							: "bg-slate-900 border border-slate-700 text-slate-400 hover:text-white"
					}`}
				>
					<Trash2 className="w-3.5 h-3.5" />
					Clear
				</button>
			</div>

			{/* Custom prompt editor */}
			{personalityId === "custom" && (
				<textarea
					value={customPrompt}
					onChange={(e) => setCustomPrompt(e.target.value)}
					placeholder="Enter your custom system prompt..."
					rows={3}
					className="mb-3 bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-500 resize-none outline-none focus:border-fleet-500"
				/>
			)}

			{/* Messages */}
			<div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2" data-testid="chat-messages">
				{messages.length === 0 && (
					<div className="flex flex-col items-center justify-center h-full text-slate-500">
						<Bot className="w-12 h-12 mb-3 text-slate-700" />
						<p className="text-sm">Chat with Fritz — your fleet agent</p>
						<p className="text-xs text-slate-600 mt-1">
							Personality: {personality.name}
						</p>
					</div>
				)}

				{messages.map((msg, i) => (
					<div
						key={i}
						className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
					>
						{msg.role === "assistant" && (
							<div className="p-2 rounded-lg bg-slate-800 h-fit mt-1">
								<Bot className="w-4 h-4 text-fleet-400" />
							</div>
						)}
						<div
							className={`max-w-[75%] rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
								msg.role === "user"
									? "bg-fleet-800 text-white rounded-br-sm"
									: "bg-slate-800/80 text-slate-200 rounded-bl-sm"
							}`}
						>
							{msg.content ||
								(i === messages.length - 1 && streaming ? (
									<span className="inline-flex gap-0.5">
										<span
											className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
											style={{ animationDelay: "0ms" }}
										/>
										<span
											className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
											style={{ animationDelay: "150ms" }}
										/>
										<span
											className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"
											style={{ animationDelay: "300ms" }}
										/>
									</span>
								) : (
									""
								))}
						</div>
						{msg.role === "user" && (
							<div className="p-2 rounded-lg bg-fleet-900 h-fit mt-1">
								<User className="w-4 h-4 text-fleet-300" />
							</div>
						)}
					</div>
				))}

				{/* Example prompts (shown when no messages) */}
				{messages.length === 0 && (
					<div data-testid="example-prompts" className="flex flex-wrap gap-2 justify-center mt-4">
						{EXAMPLE_PROMPTS.map((p) => (
							<button
								key={p.label}
								onClick={() => setInput(p.text)}
								className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-full text-xs text-slate-300 hover:bg-slate-700 hover:border-fleet-600 transition-colors"
							>
								{p.label}
							</button>
						))}
					</div>
				)}

				{/* Error rendered as assistant message */}
				{error && (
					<div className="flex gap-3 justify-start">
						<div className="p-2 rounded-lg bg-slate-800 h-fit mt-1">
							<Terminal className="w-4 h-4 text-red-400" />
						</div>
						<div className="max-w-[75%] rounded-lg px-4 py-2.5 text-sm leading-relaxed bg-red-950/30 text-red-300 border border-red-800 rounded-bl-sm">
							{error}
						</div>
					</div>
				)}

				<div ref={bottomRef} />
			</div>

			{/* Input */}
			<div className="shrink-0 border border-slate-800 rounded-lg bg-slate-900/80 p-2 flex gap-2">
				<textarea
					ref={inputRef}
					value={input}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={handleKeyDown}
					placeholder="Message Fritz..."
					rows={1}
					data-testid="chat-input"
					className="flex-1 bg-transparent border-none outline-none text-sm text-slate-200 placeholder-slate-500 resize-none px-2 py-1.5"
				/>
				<button
					onClick={handleSend}
					disabled={!input.trim() || streaming}
					data-testid="chat-send"
					className="px-3 py-2 bg-fleet-700 hover:bg-fleet-600 disabled:bg-slate-800 text-white rounded-lg transition-colors disabled:text-slate-500"
				>
					{streaming ? (
						<Bot className="w-4 h-4 animate-pulse" />
					) : (
						<Send className="w-4 h-4" />
					)}
				</button>
			</div>
		</div>
	);
}
