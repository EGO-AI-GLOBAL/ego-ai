const { withAppBuildGradle, withProjectBuildGradle } = require("expo/config-plugins");

/**
 * Expo SDK 53 / Kotlin 2.0 + Play Billing 8 (metadata Kotlin 2.1+).
 * expo-iap já skipa no próprio módulo; o :app também resolve billing-ktx e
 * precisa do mesmo freeCompilerArgs.
 */
function withKotlinSkipMetadata(config) {
  config = withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("Xskip-metadata-version-check")) return cfg;

    const block = `
    // Billing 8 (Kotlin metadata) no Expo SDK 53
    tasks.withType(org.jetbrains.kotlin.gradle.tasks.KotlinCompile).configureEach {
        kotlinOptions {
            freeCompilerArgs += ["-Xskip-metadata-version-check"]
        }
    }
`;
    if (contents.includes("dependencies {")) {
      contents = contents.replace(/dependencies\s*\{/, `${block}\ndependencies {`);
    } else {
      contents += `\n${block}\n`;
    }
    cfg.modResults.contents = contents;
    return cfg;
  });

  config = withProjectBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("play-billing-kotlin-skip-all")) return cfg;

    contents += `

// @generated begin play-billing-kotlin-skip-all - expo prebuild
subprojects { sub ->
    sub.pluginManager.withPlugin("org.jetbrains.kotlin.android") {
        sub.tasks.withType(org.jetbrains.kotlin.gradle.tasks.KotlinCompile).configureEach {
            kotlinOptions {
                freeCompilerArgs += ["-Xskip-metadata-version-check"]
            }
        }
    }
    sub.pluginManager.withPlugin("kotlin-android") {
        sub.tasks.withType(org.jetbrains.kotlin.gradle.tasks.KotlinCompile).configureEach {
            kotlinOptions {
                freeCompilerArgs += ["-Xskip-metadata-version-check"]
            }
        }
    }
}
// @generated end play-billing-kotlin-skip-all
`;
    cfg.modResults.contents = contents;
    return cfg;
  });

  return config;
}

module.exports = withKotlinSkipMetadata;
