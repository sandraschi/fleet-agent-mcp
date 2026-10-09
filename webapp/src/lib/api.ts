const isTauri =
	typeof window !== "undefined" &&
	("__TAURI__" in window || "__TAURI_INTERNALS__" in window);

// Same-origin relative by default (vite proxy); absolute backend only inside Tauri.
export const API_BASE = isTauri ? "http://127.0.0.1:10996" : "";
