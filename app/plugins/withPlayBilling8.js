const {
  withAppBuildGradle,
  withGradleProperties,
  withProjectBuildGradle,
} = require("expo/config-plugins");

/**
 * Play Console (prazo 31/08/2026): updates precisam de Play Billing Library 8+.
 * react-native-iap@12 traz 7.0.0 — forçamos 8.0.0 no Gradle.
 *
 * Expo SDK 52 / Kotlin 1.9: billing-ktx 8 é compilado com Kotlin 2.x metadata,
 * por isso adicionamos -Xskip-metadata-version-check (workaround conhecido).
 */
function withPlayBilling8(config) {
  config = withGradleProperties(config, (cfg) => {
    const key = "RNIap_playBillingSdkVersion";
    const value = "8.0.0";
    const existing = cfg.modResults.find(
      (item) => item.type === "property" && item.key === key
    );
    if (existing) {
      existing.value = value;
    } else {
      cfg.modResults.push({ type: "property", key, value });
    }
    return cfg;
  });

  config = withProjectBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("playBillingSdkVersion")) {
      return cfg;
    }
    // Garante ext no root para o getExtOrDefault do react-native-iap
    if (contents.includes("ext {")) {
      contents = contents.replace(
        /ext\s*\{/,
        `ext {\n        playBillingSdkVersion = "8.0.0"`
      );
    } else if (contents.includes("buildscript {")) {
      contents = contents.replace(
        /buildscript\s*\{/,
        `buildscript {\n    ext {\n        playBillingSdkVersion = "8.0.0"\n    }`
      );
    }
    cfg.modResults.contents = contents;
    return cfg;
  });

  config = withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("Xskip-metadata-version-check")) {
      return cfg;
    }

    const kotlinBlock = `
    // Play Billing 8 (Kotlin 2 metadata) no Expo SDK 52 / Kotlin 1.9
    tasks.withType(org.jetbrains.kotlin.gradle.tasks.KotlinCompile).configureEach {
        kotlinOptions {
            freeCompilerArgs += ["-Xskip-metadata-version-check"]
        }
    }
`;

    if (contents.includes("android {")) {
      // Preferir after android { ... } closing is hard; append before dependencies or at end
      if (contents.includes("dependencies {")) {
        contents = contents.replace(
          /dependencies\s*\{/,
          `${kotlinBlock}\ndependencies {`
        );
      } else {
        contents += `\n${kotlinBlock}\n`;
      }
    } else {
      contents += `\n${kotlinBlock}\n`;
    }

    // Força resolução da dependência em todo o projeto app
    if (!contents.includes("com.android.billingclient:billing")) {
      const forceBilling = `
    // Force Google Play Billing Library 8+ (Play Console deadline 2026-08-31)
    configurations.all {
        resolutionStrategy {
            force "com.android.billingclient:billing:8.0.0"
            force "com.android.billingclient:billing-ktx:8.0.0"
        }
    }
`;
      if (contents.includes("dependencies {")) {
        contents = contents.replace(
          /dependencies\s*\{/,
          `${forceBilling}\ndependencies {`
        );
      } else {
        contents += `\n${forceBilling}\n`;
      }
    }

    cfg.modResults.contents = contents;
    return cfg;
  });

  return config;
}

module.exports = withPlayBilling8;
