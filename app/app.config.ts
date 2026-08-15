import type { ExpoConfig } from "expo/config";
import fs from "fs";
import path from "path";

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

/** Firebase EGO (GA4) — só activa plugin se os ficheiros existirem (project EGO, não ShapeScan). */
const androidGoogleServices = path.join(__dirname, "google-services.json");
const iosGoogleServices = path.join(__dirname, "GoogleService-Info.plist");
const hasFirebaseAndroid = fs.existsSync(androidGoogleServices);
const hasFirebaseIos = fs.existsSync(iosGoogleServices);
const hasFirebase = hasFirebaseAndroid || hasFirebaseIos;

const config: ExpoConfig = {
  name: "Ego-IA",
  slug: "ego-ai",
  version: "1.0.112",
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
    buildNumber: "117",
    appleTeamId: "7XVMZQ2Z33",
    entitlements: {
      "com.apple.security.application-groups": ["group.com.egoai.app.widget"],
    },
    ...(hasFirebaseIos ? { googleServicesFile: "./GoogleService-Info.plist" } : {}),
    infoPlist: {
      CFBundleDevelopmentRegion: "pt-BR",
      CFBundleLocalizations: ["pt-BR"],
      ITSAppUsesNonExemptEncryption: false,
      LSApplicationQueriesSchemes: ["itms-beta", "itms-apps", "whatsapp", "instagram"],
      NSMicrophoneUsageDescription:
        "O EGO-AI usa o microfone para mensagens de voz e chamada ao vivo com o assistente.",
      NSPhotoLibraryUsageDescription:
        "O EGO-AI acede às fotos para ler texto em imagens que anexar ao chat.",
      NSCameraUsageDescription:
        "O EGO-AI usa a câmara para fotografar documentos e extrair o texto.",
    },
  },
  android: {
    versionCode: 170,
    package: "com.egoai.app",
    ...(hasFirebaseAndroid ? { googleServicesFile: "./google-services.json" } : {}),
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
      /** Play / Android 13+: AdMob — alinha com a declaração de ID de publicidade. */
      "com.google.android.gms.permission.AD_ID",
    ],
    /** Play: galeria via Photo Picker — sem READ_MEDIA_IMAGES/VIDEO. */
    blockedPermissions: [
      "android.permission.READ_MEDIA_IMAGES",
      "android.permission.READ_MEDIA_VIDEO",
      "android.permission.READ_MEDIA_VISUAL_USER_SELECTED",
      "android.permission.READ_EXTERNAL_STORAGE",
      "android.permission.WRITE_EXTERNAL_STORAGE",
    ],
    /** Evita o teclado tapar a caixa de mensagem no chat. */
    softwareKeyboardLayoutMode: "resize",
  },
  plugins: [
    "expo-router",
    "@bacons/apple-targets",
    ...(hasFirebase ? ["@react-native-firebase/app"] : []),
    [
      "react-native-android-widget",
      {
        widgets: [
          {
            name: "MoodGarden",
            label: "Jardim dos Monstrinhos",
            minWidth: "250dp",
            minHeight: "110dp",
            targetCellWidth: 4,
            targetCellHeight: 2,
            description: "Humor, missões e sequência do jardim.",
            updatePeriodMillis: 1800000,
          },
          {
            name: "EgoDeBolso",
            label: "EGO de Bolso",
            minWidth: "250dp",
            minHeight: "110dp",
            targetCellWidth: 4,
            targetCellHeight: 2,
            description: "Missões do dia e desafio semanal do companheiro.",
            updatePeriodMillis: 1800000,
          },
        ],
      },
    ],
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
        /** false = não declara READ_MEDIA_* (Photo Picker do sistema). iOS já tem NSPhotoLibraryUsageDescription. */
        photosPermission: false,
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
          targetSdkVersion: 36,
          compileSdkVersion: 36,
          buildToolsVersion: "36.0.0",
          /** SDK 53 default (Kotlin 2.0); RN 0.79 + Expo ≥53.0.14 = 16 KB. */
          kotlinVersion: "2.0.21",
          usesCleartextTraffic: allowHttp,
        },
        ...(hasFirebaseIos
          ? {
              ios: {
                useFrameworks: "static" as const,
              },
            }
          : {}),
      },
    ],
    "./plugins/withXcode26FmtFix",
    "./plugins/withKotlinSkipMetadata",
    "expo-iap",
    [
      "react-native-google-mobile-ads",
      {
        /** Teste Google por defeito — troca por IDs reais via EXPO_PUBLIC_ADMOB_*_APP_ID. */
        androidAppId:
          process.env.EXPO_PUBLIC_ADMOB_ANDROID_APP_ID ||
          "ca-app-pub-3940256099942544~3347511713",
        iosAppId:
          process.env.EXPO_PUBLIC_ADMOB_IOS_APP_ID ||
          "ca-app-pub-3940256099942544~1458002511",
        delayAppMeasurementInit: true,
      },
    ],
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
    firebaseAnalyticsReady: hasFirebase,
  },
};

export default config;
