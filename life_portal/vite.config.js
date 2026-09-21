import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";
import { copyFileSync, readFileSync } from "node:fs";

const runtimeConfig = fileURLToPath(
  new URL("../life_slimming/public/js/portal_config.js", import.meta.url),
);

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
      name: "life-portal-runtime-config",
      // Inject after Vite rewrites URLs so the app base is not added twice.
      transformIndexHtml: {
        order: "post",
        handler() {
          return [
            {
              tag: "script",
              attrs: {
                src:
                  command === "build"
                    ? "/assets/life_slimming/js/portal_config.js"
                    : "/life_portal/portal_config.js",
              },
              injectTo: "head-prepend",
            },
          ];
        },
      },
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const path = req.url?.split("?")[0];
          if (
            !["/life_portal/portal_config.js", "/portal_config.js"].includes(
              path,
            )
          )
            return next();
          res.setHeader(
            "Content-Type",
            "application/javascript; charset=utf-8",
          );
          res.setHeader("Cache-Control", "no-store");
          res.end(readFileSync(runtimeConfig, "utf8"));
        });
      },
    },
    {
      name: "life-portal-frappe-entry",
      apply: "build",
      writeBundle() {
        copyFileSync(`${output}/index.html`, entry);
      },
    },
  ],
  esbuild: { drop: command === "build" ? ["console", "debugger"] : [] },
  build: { outDir: output, emptyOutDir: true },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      [
        "/life_portal_module",
        "/api",
        "/login",
        "/update-password",
        "/assets",
        "/files",
        "/app",
      ].map((path) => [
        path,
        {
          target: "http://127.0.0.1:8000",
          headers: {
            Host: "mysite.local",
            "X-Frappe-Site-Name": "mysite.local",
          },
          cookieDomainRewrite: "",
        },
      ]),
    ),
  },
}));
