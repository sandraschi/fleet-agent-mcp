import { create } from "zustand";

const BACKOFF = [1, 2, 4, 8, 16, 30];
const BACKEND = "http://127.0.0.1:10996";

interface ConnectionState {
	state: "connecting" | "connected" | "offline";
	lastError: string | null;
	startPolling: () => void;
}

export const useConnection = create<ConnectionState>((set, _get) => ({
	state: "connecting",
	lastError: null,

	startPolling: () => {
		let attempt = 0;
		let stopped = false;

		const tick = async () => {
			if (stopped) return;
			try {
				const r = await fetch(`${BACKEND}/api/health`, { signal: AbortSignal.timeout(5000) });
				if (r.ok) {
					set({ state: "connected", lastError: null });
					attempt = 0;
				} else {
					set({ state: "offline", lastError: `HTTP ${r.status}` });
				}
			} catch (e) {
				const msg = e instanceof Error ? e.message : "Network error";
				set({ state: "offline", lastError: msg });
			}
			attempt = Math.min(++attempt, BACKOFF.length - 1);
			setTimeout(tick, BACKOFF[attempt] * 1000);
		};

		tick();

		(async () => {
			try {
				const { listen } = await import("@tauri-apps/api/event");
				await listen<string>("backend-status", (event) => {
					if (event.payload === "ready") set({ state: "connected" });
					else if (event.payload?.startsWith("error:")) set({ state: "offline", lastError: event.payload });
				});
			} catch {
				/* not in Tauri */
			}
		})();

		return () => { stopped = true; };
	},
}));
