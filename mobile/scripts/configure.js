/**
 * Grava EGO_APP_URL em mobile/.env (uso: npm run configure -- https://seu-app.streamlit.app)
 */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..");
const envPath = path.join(root, ".env");

const url = process.argv[2];
if (!url || !url.startsWith("https://")) {
  console.error("Uso: npm run configure -- https://SEU-APP.streamlit.app");
  process.exit(1);
}

const clean = url.replace(/\/$/, "");
const body = `# Gerado por npm run configure\nEGO_APP_URL=${clean}\n`;
fs.writeFileSync(envPath, body, "utf8");
console.log("OK: EGO_APP_URL =", clean);
console.log("Próximo: npm run cap:sync");
