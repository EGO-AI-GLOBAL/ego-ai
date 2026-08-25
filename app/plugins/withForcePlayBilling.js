const { withAppBuildGradle, withProjectBuildGradle } = require("expo/config-plugins");

/**
 * Última linha de defesa Play: Billing Library ≥ 8.0.0 em TODO o grafo Gradle.
 * - force nas configurations (mata transitivas antigas)
 * - implementation directa no :app (Bundle Explorer vê 8.x)
 */
function withForcePlayBilling(config) {
  config = withProjectBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (!contents.includes("ego-force-play-billing-8")) {
      contents += `

// @generated begin ego-force-play-billing-8 - expo prebuild
allprojects {
    configurations.all {
        resolutionStrategy {
            force "com.android.billingclient:billing:8.0.0"
            force "com.android.billingclient:billing-ktx:8.0.0"
        }
    }
}
// @generated end ego-force-play-billing-8
`;
    }
    cfg.modResults.contents = contents;
    return cfg;
  });

  config = withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("ego-app-billing-ktx-8")) return cfg;
    if (contents.includes("dependencies {")) {
      contents = contents.replace(
        /dependencies\s*\{/,
        `dependencies {
    // @generated begin ego-app-billing-ktx-8
    implementation "com.android.billingclient:billing-ktx:8.0.0"
    // @generated end ego-app-billing-ktx-8`
      );
    }
    cfg.modResults.contents = contents;
    return cfg;
  });

  return config;
}

module.exports = withForcePlayBilling;
