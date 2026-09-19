import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";
import { copyFileSync } from "node:fs";

const output = fileURLToPath(
  new URL("../life_slimming/public/life_portal/", import.meta.url),
);
const entry = fileURLToPath(
  new URL("../life_slimming/www/life_portal.html", import.meta.url),
);

export default defineConfig(({ command }) => ({
  base:
    command === "build"
      ? "/assets/life_slimming/life_portal/"
      : "/life_portal/",
  plugins: [
    vue(),
    {
      name: "life-portal-frappe-entry",
      apply: "build",
      writeBundle() {
        copyFileSync(`${output}/index.html`, entry);
      },
    },
  ],
  build: { outDir: output, emptyOutDir: true },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      ["/api", "/login", "/update-password", "/assets", "/files", "/app"].map(
        (path) => [
          path,
          {
            target: "http://127.0.0.1:8000",
            headers: {
              Host: "mysite.local",
              "X-Frappe-Site-Name": "mysite.local",
            },
            cookieDomainRewrite: "",
          },
        ],
      ),
    ),
  },
}));
