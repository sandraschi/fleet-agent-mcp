import { test, expect } from "@playwright/test";

const BE = "http://127.0.0.1:10996";

test.describe("Fleet Audit", () => {
    test("Backend health returns 200", async ({ request }) => {
        const resp = await request.get(`${BE}/api/health`);
        expect(resp.status()).toBe(200);
        const body = await resp.json();
        expect(body.status).toBe("ok");
        expect(body.server).toBe("fleet-agent");
        expect(typeof body.tool_count).toBe("number");
        expect(body.tool_count).toBeGreaterThan(0);
    });

    test("Backend diagnostics returns tools", async ({ request }) => {
        const resp = await request.get(`${BE}/api/v1/diagnostics`);
        expect(resp.status()).toBe(200);
        const body = await resp.json();
        expect(body.tools.length).toBeGreaterThan(0);
        expect(body.system.windows).toBe(true);
    });

    test("Frontend SPA loads", async ({ page }) => {
        await page.goto("/", { timeout: 15000 });
        await page.waitForTimeout(3000);
        await expect(page.locator("#root")).toBeAttached();
    });

    test("Dashboard page loads", async ({ page }) => {
        await page.goto("/", { timeout: 15000 });
        await page.waitForTimeout(2000);
        await expect(page.locator("h1, h2").first()).toBeAttached();
    });
});
