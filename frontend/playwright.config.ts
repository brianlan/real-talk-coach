import { defineConfig } from "@playwright/test";

const useDockerDeployment = process.env.PW_USE_DOCKER === "1";
const baseURL = useDockerDeployment
  ? process.env.PW_BASE_URL ?? "http://localhost"
  : process.env.PW_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "tests/e2e",
  use: {
    baseURL,
    headless: true,
  },
  webServer: useDockerDeployment
    ? undefined
    : {
        command: "pnpm dev",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 120 * 1000,
      },
});
