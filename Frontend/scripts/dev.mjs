import { spawn } from "node:child_process";
import path from "node:path";

const nextBin = path.join(process.cwd(), "node_modules/next/dist/bin/next");
const ansiPattern = /\x1B\[[0-9;]*m/g;

function openBrowser(url) {
  if (process.platform === "win32") {
    spawn("cmd", ["/c", "start", "", url], { detached: true, stdio: "ignore" }).unref();
  } else if (process.platform === "darwin") {
    spawn("open", [url], { detached: true, stdio: "ignore" }).unref();
  } else {
    spawn("xdg-open", [url], { detached: true, stdio: "ignore" }).unref();
  }
}

const child = spawn(process.execPath, [nextBin, "dev", ...process.argv.slice(2)], {
  stdio: ["inherit", "pipe", "inherit"],
  env: { ...process.env, FORCE_COLOR: process.env.FORCE_COLOR ?? "1" },
});

let opened = Boolean(process.env.NO_OPEN);

child.stdout.on("data", (chunk) => {
  process.stdout.write(chunk);
  if (opened) return;

  const match = chunk
    .toString("utf8")
    .replace(ansiPattern, "")
    .match(/Local:\s+(https?:\/\/[^\s]+)/);
  if (match) {
    opened = true;
    openBrowser(match[1]);
  }
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}

child.on("exit", (code) => process.exit(code ?? 0));
