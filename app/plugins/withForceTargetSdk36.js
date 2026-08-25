const { withAppBuildGradle } = require("expo/config-plugins");

/**
 * Força compileSdk + targetSdk 36 (Android 16) no :app.
 * Idempotente — não duplica se já existir.
 */
function withForceTargetSdk36(config) {
  return withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;

    if (!contents.includes("ego-force-compile-sdk-36")) {
      contents = contents.replace(
        /android\s*\{/,
        `android {
    // @generated ego-force-compile-sdk-36
    compileSdkVersion 36
    // @generated end ego-force-compile-sdk-36`
      );
    }

    if (!contents.includes("ego-force-target-sdk-36")) {
      contents = contents.replace(
        /defaultConfig\s*\{/,
        `defaultConfig {
        // @generated ego-force-target-sdk-36
        targetSdkVersion 36
        // @generated end ego-force-target-sdk-36`
      );
    }

    cfg.modResults.contents = contents;
    return cfg;
  });
}

module.exports = withForceTargetSdk36;
