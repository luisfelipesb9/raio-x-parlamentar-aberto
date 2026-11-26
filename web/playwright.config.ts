import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const WEB = "http://localhost:3000";
const API = "http://localhost:8000";
const raiz = path.resolve(__dirname, "..");

/**
 * E2E contra a API REAL (por padrão data/sample/raio_x_sample.duckdb; troque com RAIO_X_DB) e o build de produção do web.
 * Se já houver servidores nas portas 3000/8000 eles são reaproveitados (fora do CI).
 */
export default defineConfig({
  testDir: "../tests/e2e",
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: { baseURL: WEB, trace: "retain-on-failure", locale: "pt-BR" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "mobile-375", use: { ...devices["Desktop Chrome"], viewport: { width: 375, height: 812 }, hasTouch: true } },
  ],
  webServer: [
    {
      command: "uv run uvicorn api.main:app --port 8000",
      cwd: raiz,
      env: {
        RAIO_X_DB: process.env.RAIO_X_DB ?? "data/sample/raio_x_sample.duckdb",
        // Sal de TESTE dos ids de pessoa (a API não tem sal padrão e não sobe sem ele).
        RAIO_X_ID_SALT: process.env.RAIO_X_ID_SALT ?? "sal-somente-para-testes",
      },
      url: `${API}/deputados?page_size=1`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm build && pnpm start",
      cwd: __dirname,
      env: { NEXT_PUBLIC_E2E: "1", NEXT_PUBLIC_API_URL: API },
      url: WEB,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
    },
  ],
});
