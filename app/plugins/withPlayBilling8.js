const {
  withAppBuildGradle,
  withGradleProperties,
  withProjectBuildGradle,
} = require("expo/config-plugins");

/**
 * Play Console (prazo 31/08/2026): updates precisam de Play Billing Library 8+.
 * react-native-iap@12 traz 7.0.0 — forçamos 8.0.0 no Gradle.
 *
 * Expo SDK 52 / Kotlin 1.9: billing-ktx 8 traz metadata Kotlin 2.1.
 * O skip-metadata tem de chegar ao :react-native-iap (não só ao app).
 * Evitar sub.afterEvaluate — falha se o projeto já foi evaluated.
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

    if (!contents.includes("playBillingSdkVersion")) {
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
    }

    // Remove bloco antigo com afterEvaluate (quebra o Gradle)
    contents = contents.replace(
      /\n*\/\/ @generated begin play-billing-8-kotlin-skip[\s\S]*?\/\/ @generated end play-billing-8-kotlin-skip\n*/g,
      "\n"
    );

    if (!contents.includes("play-billing-8-kotlin-skip")) {
      contents += `

// @generated begin play-billing-8-kotlin-skip - expo prebuild
// Billing 8 (Kotlin 2.1 metadata) no Expo SDK 52 / Kotlin 1.9
subprojects { sub ->
    def applyBilling8Workarounds = {
        sub.tasks.withType(org.jetbrains.kotlin.gradle.tasks.KotlinCompile).configureEach {
            kotlinOptions {
                freeCompilerArgs += ["-Xskip-metadata-version-check"]
            }
        }
        sub.configurations.configureEach {
            resolutionStrategy {
                force "com.android.billingclient:billing:8.0.0"
                force "com.android.billingclient:billing-ktx:8.0.0"
            }
        }
    }
    if (sub.state.executed) {
        applyBilling8Workarounds()
    } else {
        sub.afterEvaluate { applyBilling8Workarounds() }
    }
}
// @generated end play-billing-8-kotlin-skip
`;
    }

    cfg.modResults.contents = contents;
    return cfg;
  });

  config = withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;

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
