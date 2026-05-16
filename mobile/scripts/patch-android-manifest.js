/**
 * Garante permissão INTERNET no AndroidManifest após `cap add android`.
 */
const fs = require("fs");
const path = require("path");

const manifest = path.join(
  __dirname,
  "..",
  "android",
  "app",
  "src",
  "main",
  "AndroidManifest.xml"
);
if (!fs.existsSync(manifest)) {
  process.exit(0);
}
const xml = fs.readFileSync(manifest, "utf8");
if (xml.includes("android.permission.INTERNET")) {
  process.exit(0);
}
const patched = xml.replace(
  /<application/,
  '  <uses-permission android:name="android.permission.INTERNET" />\n    <application'
);
fs.writeFileSync(manifest, patched, "utf8");
console.log("patch-android-manifest: added INTERNET permission");
