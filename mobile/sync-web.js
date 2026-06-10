// Копирует PWA-ассеты из src/jarvis/server/webapp в ./www,
// чтобы Android-обёртка использовала тот же код, что и сервер.
const fs = require("fs");
const path = require("path");

const src = path.resolve(__dirname, "..", "src", "jarvis", "server", "webapp");
const dst = path.resolve(__dirname, "www");

fs.rmSync(dst, { recursive: true, force: true });
fs.mkdirSync(dst, { recursive: true });

for (const name of fs.readdirSync(src)) {
  fs.copyFileSync(path.join(src, name), path.join(dst, name));
}
console.log(`Скопировано в www: ${fs.readdirSync(dst).join(", ")}`);
