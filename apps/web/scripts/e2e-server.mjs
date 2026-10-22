import { cpSync, existsSync } from "node:fs";

// Exercise the built standalone server without development compilation or HMR.
// Next does not copy static/public assets into standalone output automatically.
const app = new URL("../", import.meta.url);
const standalone = new URL(".next/standalone/apps/web/", app);
cpSync(new URL(".next/static/", app), new URL(".next/static/", standalone), {
  recursive: true,
});
if (existsSync(new URL("public/", app))) {
  cpSync(new URL("public/", app), new URL("public/", standalone), {
    recursive: true,
  });
}
process.env.HOSTNAME = "127.0.0.1";
process.env.PORT = "3104";
await import(new URL("server.js", standalone).href);
