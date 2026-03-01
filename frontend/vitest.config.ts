import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./"),
    },
  },
  test: {
    include: ["tests/**/*.{test,spec}.{ts,tsx}", "hooks/__tests__/**/*.{test,spec}.{ts,tsx}", "app/**/__tests__/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["tests/e2e/**"],
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
