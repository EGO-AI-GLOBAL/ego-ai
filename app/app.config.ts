import type { ExpoConfig } from "expo/config";

const apiUrl = (process.env.EXPO_PUBLIC_API_URL || "").trim();
const appEnv = (process.env.APP_ENV || process.env.NODE_ENV || "development").toLowerCase();
const easProfile = (process.env.EAS_BUILD_PROFILE || "").trim();
const isProd = appEnv === "production" || easProfile === "production";
const useDevClient =
  easProfile === "development" || (!easProfile && appEnv !== "production");
const allowHttp =
  process.env.EXPO_PUBLIC_ALLOW_HTTP === "1" ||
  (apiUrl.startsWith("http://") && process.env.NODE_ENV !== "production");

if (isProd && apiUrl && !apiUrl.startsWith("https://")) {
  throw new Error("Produção exige EXPO_PUBLIC_API_URL com https://");
}

const config: ExpoConfig = {
  name: "Ego-IA",
  slug: "ego-ai",
  version: "1.0.35",
  orientation: "portrait",
  scheme: "egoai",
  userInterfaceStyle: "automatic",
  // New Architecture + WebRTC costuma falhar no Gradle do EAS; reativar depois.
  newArchEnabled: false,
  icon: "./assets/icon.png",
  splash: {
    image: "./assets/splash-icon.png",
    resizeMode: "contain",
    backgroundColor: "#0A122A",
  },
  ios: {
    supportsTablet: true,
    bundleIdentifier: "com.egoai.app",
    buildNumber: "18",
    infoPlist: {
      ITSAppUsesNonExemptEncryption: false,
      LSApplicationQueriesSchemes: ["itms-beta", "itms-apps"],
      NSMicrophoneUsageDescription:
        "O EGO-AI usa o microfone para mensagens de voz e chamada ao vivo com o assistente.",
      NSPhotoLibraryUsageDescription:
        "O EGO-AI acede às fotos para ler texto em imagens que anexar ao chat.",
      NSCameraUsageDescription:
        "O EGO-AI usa a câmara para fotografar documentos e extrair o texto.",
    },
  },
  android: {
    versionCode: 67,
    package: "com.egoai.app",
    adaptiveIcon: {
      /** Mesmo PNG do iOS — evita ícone minúsculo dentro do círculo no launcher. */
      foregroundImage: "./assets/icon.png",
      backgroundColor: "#121c2c",
    },
    permissions: [
      "RECORD_AUDIO",
      "MODIFY_AUDIO_SETTINGS",
      "POST_NOTIFICATIONS",
      "SCHEDULE_EXACT_ALARM",
      "USE_EXACT_ALARM",
      "CAMERA",
      "READ_MEDIA_IMAGES",
    ],
    /** Evita o teclado tapar a caixa de mensagem no chat. */
    softwareKeyboardLayoutMode: "resize",
  },
  plugins: [
    "expo-router",
    "expo-secure-store",
    [
      "expo-av",
      {
        microphonePermission:
          "O EGO-AI precisa do microfone para mensagens de voz ao assistente.",
      },
    ],
    [
      "expo-image-picker",
      {
        photosPermission:
          "O EGO-AI acede às fotos para ler texto em imagens anexadas ao chat.",
        cameraPermission:
          "O EGO-AI usa a câmara para fotografar páginas e extrair o texto.",
      },
    ],
    [
      "expo-notifications",
      {
        icon: "./assets/icon.png",
        color: "#22D3EE",
        sounds: [],
      },
    ],
    [
      "expo-build-properties",
      {
        android: {
          minSdkVersion: 24,
          targetSdkVersion: 35,
          compileSdkVersion: 35,
          kotlinVersion: "1.9.25",
          usesCleartextTraffic: allowHttp,
        },
      },
    ],
    "./plugins/withXcode26FmtFix",
  ],
  experiments: {
    typedRoutes: true,
    tsconfigPaths: true,
  },
  extra: {
    eas: {
      projectId:
        process.env.EAS_PROJECT_ID || "558cc924-3323-4d68-a82b-aa237bf16369",
    },
    privacyPolicyUrl:
      process.env.EXPO_PUBLIC_PRIVACY_POLICY_URL ||
      "https://egoai.com.br/privacidade/",
    accountDeletionUrl:
      process.env.EXPO_PUBLIC_ACCOUNT_DELETION_URL ||
      "https://egoai.com.br/exclusao-conta/",
    websiteUrl: process.env.EXPO_PUBLIC_WEBSITE_URL || "https://egoai.com.br",
    supportEmail:
      process.env.EXPO_PUBLIC_SUPPORT_EMAIL || "contato@egoai.com.br",
    apiUrl,
  },
};

export default config;
