import { defineConfig } from "@playwright/test";

const useDockerDeployment =
  process.env.PW_USE_DOCKER === "1" || process.env.PW_USE_DOCKER === "true";
const baseURL =
  process.env.PW_BASE_URL ??
  (useDockerDeployment ? "http://localhost" : "http://localhost:3000");

export default defineConfig({
  testDir: "tests/e2e",
  use: {
    baseURL,
    headless: true,
  },
  ...(useDockerDeployment
    ? {}
    : {
        webServer: {
          command: "pnpm dev",
          url: baseURL,
          reuseExistingServer: true,
          timeout: 120 * 1000,
        },
      }),
});
