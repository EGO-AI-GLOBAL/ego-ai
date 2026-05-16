/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("fs");
const path = require("path");

function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 1) continue;
    const key = t.slice(0, i).trim();
    let val = t.slice(i + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!process.env[key]) process.env[key] = val;
  }
}

loadEnv();

const defaultUrl = "https://COLOQUE-AQUI-SEU-APP.streamlit.app";
const appUrl = (process.env.EGO_APP_URL || defaultUrl).replace(/\/$/, "");

/** @type {import('@capacitor/cli').CapacitorConfig} */
const config = {
  appId: "com.egoai.assistant",
  appName: "EGO-AI",
  webDir: "www",
  server: {
    url: appUrl,
    cleartext: false,
    androidScheme: "https",
    allowNavigation: [
      appUrl,
      "*.streamlit.app",
      "*.supabase.co",
      "accounts.google.com",
      "*.google.com",
      "*.stripe.com",
    ],
  },
  android: {
    allowMixedContent: false,
    backgroundColor: "#0f0f12",
  },
  ios: {
    contentInset: "automatic",
    backgroundColor: "#0f0f12",
    scrollEnabled: true,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 2000,
      launchAutoHide: true,
      backgroundColor: "#0f0f12",
      androidSplashResourceName: "splash",
      androidScaleType: "CENTER_CROP",
      showSpinner: false,
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0f0f12",
    },
  },
};

module.exports = config;
