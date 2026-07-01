import { defineConfig } from "@playwright/test";

const BACKEND_PORT = 10996;
const FRONTEND_PORT = 10997;

export default defineConfig({
    testDir: "./e2e",
    timeout: 60000,
    retries: 1,
    use: {
        baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
        headless: true,
        screenshot: "only-on-failure",
    },
    webServer: {
        command: `uv run python -m fleet_agent.server --http --port ${BACKEND_PORT} --host 127.0.0.1`,
        port: BACKEND_PORT,
        cwd: "../",
        timeout: 30000,
        reuseExistingServer: true,
    },
});
