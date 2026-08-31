import { defineConfig } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const FRONTEND_PORT = 5173;
const BACKEND_PORT = 8001; // container-mapped port, separate from the real dev backend (8000)

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // tests share one backend+DB; keep them sequential and deterministic
  workers: 1,
  retries: 0,
  timeout: 60_000,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    video: "on",
    trace: "on",
    screenshot: "on",
  },
  webServer: [
    {
      // Brings up the isolated test-only Postgres + backend containers
      // (see docker-compose.test.yml). Idempotent: safe if already running.
      command: "docker compose -f docker-compose.test.yml up -d --build --wait",
      url: `http://localhost:${BACKEND_PORT}/health`,
      timeout: 120_000,
      reuseExistingServer: true,
      cwd: path.resolve(__dirname),
    },
    {
      command: `npx vite --port ${FRONTEND_PORT}`,
      url: `http://localhost:${FRONTEND_PORT}`,
      timeout: 30_000,
      reuseExistingServer: false,
      cwd: path.resolve(__dirname, "../frontend"),
      env: {
        BACKEND_URL: `http://localhost:${BACKEND_PORT}`,
      },
    },
  ],
});
