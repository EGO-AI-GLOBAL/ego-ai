/**
 * Verificação local antes do EAS Build (evita gastar crédito na nuvem).
 * Uso: node scripts/preflight-build.mjs [--skip-bundle]
 */
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  statSync,
} from "fs";
import { dirname, join, sep } from "path";
import { fileURLToPath } from "url";
import { spawnSync } from "child_process";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const appDir = join(scriptDir, "..");
const repoRoot = join(appDir, "..");
const backupSrc = join(repoRoot, "app_local_backup", "src");
const backupAssets = join(repoRoot, "app_local_backup", "assets");
const marketingImg = join(repoRoot, "marketing", "landing", "img");
const skipBundle = process.argv.includes("--skip-bundle");

const REQUIRED_SRC = [
  "components/UsageDashboard.tsx",
  "components/ChatPreview.tsx",
  "components/TokenUsageBar.tsx",
  "components/AudioSpeedControl.tsx",
  "components/LegalMarkdown.tsx",
  "constants/audioSpeed.ts",
  "constants/plans.ts",
  "constants/teamStripeCheckout.ts",
  "storage/sessionStorage.ts",
  "security/playIntegrity.ts",
  "utils/usageStats.ts",
  "utils/speechText.ts",
  "utils/webVoiceCapture.ts",
];

const REQUIRED_AVATAR_PNG = [
  "avatar-f1.png",
  "avatar-m1.png",
  "avatar-f2.png",
  "avatar-f3.png",
  "avatar-f4.png",
  "avatar-f5.png",
  "avatar-m2.png",
  "avatar-m3.png",
  "avatar-m4.png",
  "avatar-m5.png",
  "avatar-g1.png",
  "avatar-g2.png",
];

const REQUIRED_AVATAR_MP4 = REQUIRED_AVATAR_PNG.map((n) =>
  n.replace(".png", "-speaking.mp4")
);

let errors = 0;

function ok(msg) {
  console.log(`  OK  ${msg}`);
}

function warn(msg) {
  console.log(`  AVISO  ${msg}`);
}

function fail(msg) {
  console.log(`  ERRO  ${msg}`);
  errors += 1;
}

function ensureDir(path) {
  if (!existsSync(path)) mkdirSync(path, { recursive: true });
}

function isRealPng(filePath) {
  if (!existsSync(filePath)) return false;
  const head = readFileSync(filePath).subarray(0, 4);
  return (
    head[0] === 0x89 &&
    head[1] === 0x50 &&
    head[2] === 0x4e &&
    head[3] === 0x47
  );
}

function copyFileForce(src, dest, label) {
  if (!existsSync(src)) {
    fail(`${label}: origem ausente (${src})`);
    return false;
  }
  ensureDir(dirname(dest));
  copyFileSync(src, dest);
  return true;
}

function copyIfMissing(src, dest, label) {
  if (existsSync(dest)) return false;
  if (!copyFileForce(src, dest, label)) return false;
  ok(`copiado ${label}`);
  return true;
}

function repairSrcFromBackup() {
  if (!existsSync(backupSrc)) {
    warn("app_local_backup/src nao encontrado — pulando reparo automatico");
    return;
  }
  for (const rel of REQUIRED_SRC) {
    const dest = join(appDir, "src", rel);
    const src = join(backupSrc, rel);
    copyIfMissing(src, dest, rel);
  }
  // Qualquer outro ficheiro em backup/src que falte em app/src
  const walk = (dir, base = "") => {
    for (const name of readdirSync(dir)) {
      const full = join(dir, name);
      const rel = base ? `${base}/${name}` : name;
      if (statSync(full).isDirectory()) {
        walk(full, rel);
        continue;
      }
      const dest = join(appDir, "src", rel);
      const src = join(backupSrc, rel);
      if (!existsSync(dest) && existsSync(src)) {
        copyIfMissing(src, dest, rel);
      }
    }
  };
  walk(backupSrc);
}

function repairAvatars() {
  const assetsDir = join(appDir, "assets");
  ensureDir(assetsDir);
  for (const name of REQUIRED_AVATAR_PNG) {
    const dest = join(assetsDir, name);
    const fromBackup = join(backupAssets, name);
    const fromMarketing = join(marketingImg, name);
    const needsFix = !isRealPng(dest);
    if (!needsFix) continue;
    if (isRealPng(fromBackup)) {
      copyFileForce(fromBackup, dest, name);
      ok(`PNG real (backup): ${name}`);
    } else if (isRealPng(fromMarketing)) {
      copyFileForce(fromMarketing, dest, name);
      ok(`PNG real (marketing): ${name}`);
    } else if (existsSync(dest)) {
      fail(
        `${name} nao e PNG valido (JPEG com extensao .png quebra o Gradle Android)`
      );
    } else {
      fail(`avatar PNG em falta: ${name}`);
    }
  }
  for (const name of REQUIRED_AVATAR_MP4) {
    const dest = join(assetsDir, name);
    const fromBackup = join(backupAssets, name);
    if (existsSync(dest)) continue;
    if (existsSync(fromBackup)) copyIfMissing(fromBackup, dest, name);
    else fail(`avatar MP4 em falta: ${name}`);
  }
}

function checkDeps() {
  const expoRouter = join(appDir, "node_modules", "expo-router", "package.json");
  if (!existsSync(expoRouter)) {
    fail("node_modules incompleto — rode RESTAURAR-NODE-MODULES.bat");
  } else {
    ok("node_modules / expo-router");
  }
}

function checkOnboardingGuards() {
  console.log("\n[3b/4] Onboarding (cadastro → avatar → chat)...");
  const moodGarden = join(
    appDir,
    "src",
    "components",
    "moodMonsters",
    "MoodGardenWidgetCard.tsx"
  );
  if (existsSync(moodGarden)) {
    const t = readFileSync(moodGarden, "utf8");
    const hookAt = t.indexOf("const subtitle = useMemo");
    const guardAt = t.indexOf("if (!care?.question) return null");
    if (hookAt < 0 || guardAt < 0 || hookAt > guardAt) {
      fail(
        "MoodGardenWidgetCard: useMemo deve vir ANTES de return null (crash utilizador novo)"
      );
    } else {
      ok("MoodGardenWidgetCard hooks order");
    }
    if (t.includes("colors.card")) {
      fail("MoodGardenWidgetCard: nao usar colors.card");
    }
  }
  const engagement = join(appDir, "src", "components", "AvatarEngagementCard.tsx");
  if (existsSync(engagement)) {
    const t = readFileSync(engagement, "utf8");
    if (!t.includes("colors.bgCard") || t.includes("colors.card")) {
      fail("AvatarEngagementCard: usar colors.bgCard, nunca colors.card");
    } else {
      ok("AvatarEngagementCard colors.bgCard");
    }
  }
  for (const rel of [
    "app/(main)/choose-avatar.tsx",
    "app/forgot-password.tsx",
    "app/reset-password.tsx",
  ]) {
    const p = join(appDir, rel.replace(/\//g, sep));
    if (!existsSync(p)) fail(`onboarding em falta: ${rel}`);
    else ok(rel);
  }
}

function checkRequiredFiles() {
  for (const rel of REQUIRED_SRC) {
    const p = join(appDir, "src", rel);
    if (!existsSync(p)) fail(`ficheiro em falta: src/${rel}`);
    else ok(`src/${rel}`);
  }
  for (const name of REQUIRED_AVATAR_PNG) {
    const p = join(appDir, "assets", name);
    if (!existsSync(p)) fail(`asset em falta: assets/${name}`);
    else if (!isRealPng(p))
      fail(`assets/${name} nao e PNG valido (use app_local_backup/assets)`);
    else ok(`assets/${name} (PNG ok)`);
  }
  for (const name of REQUIRED_AVATAR_MP4) {
    const p = join(appDir, "assets", name);
    if (!existsSync(p)) fail(`asset em falta: assets/${name}`);
    else ok(`assets/${name}`);
  }
  for (const base of ["icon.png", "splash-icon.png", "adaptive-icon.png"]) {
    const p = join(appDir, "assets", base);
    if (!existsSync(p)) fail(`asset em falta: assets/${base}`);
    else ok(`assets/${base}`);
  }
}

function bundleAndroid() {
  console.log("\n[4/4] Teste de bundle Android (igual ao EAS)...");
  const env = {
    ...process.env,
    EXPO_PUBLIC_API_URL:
      process.env.EXPO_PUBLIC_API_URL ||
      "https://ego-ai-production-a2c2.up.railway.app",
    APP_ENV: "production",
    EAS_BUILD_PROFILE: "production",
  };
  const r = spawnSync(
    process.platform === "win32" ? "npx.cmd" : "npx",
    ["expo", "export", "--platform", "android"],
    { cwd: appDir, env, stdio: "inherit", shell: true }
  );
  if (r.status !== 0) {
    fail("expo export falhou — corrija os erros acima antes do EAS Build");
  } else {
    ok("bundle Android gerado (pasta dist/)");
  }
}

console.log("=== Preflight EGO-AI (testar antes do build na nuvem) ===\n");

console.log("[1/4] Dependencias...");
checkDeps();

console.log("\n[2/4] Reparar ficheiros em falta (backup; PNG real obrigatorio)...");
repairSrcFromBackup();
repairAvatars();

console.log("\n[3/4] Lista obrigatoria...");
checkRequiredFiles();
checkOnboardingGuards();

if (!skipBundle && errors === 0) {
  bundleAndroid();
} else if (skipBundle) {
  console.log("\n[4/4] Bundle ignorado (--skip-bundle)");
}

console.log("");
if (errors > 0) {
  console.log(`FALHOU: ${errors} problema(s). Nao envie o build para a Expo ainda.`);
  process.exit(1);
}
console.log("TUDO OK — pode rodar 6-eas-build.bat com seguranca.");
process.exit(0);
