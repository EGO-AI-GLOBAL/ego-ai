const { withAppBuildGradle } = require("expo/config-plugins");

/**
 * Garante targetSdkVersion / compileSdkVersion 36 no :app (Android 16).
 * A Play ainda reporta API 35 em produção — força no build.gradle do app.
 */
function withForceTargetSdk36(config) {
  return withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("ego-force-target-sdk-36")) return cfg;

    // Força defaultConfig + compileOptions block markers
    if (contents.includes("defaultConfig {")) {
      contents = contents.replace(
        /defaultConfig\s*\{/,
        `defaultConfig {
        // @generated ego-force-target-sdk-36
        targetSdkVersion 36
        // @generated end ego-force-target-sdk-36`
      );
    }

    if (contents.includes("android {") && !contents.includes("compileSdkVersion 36")) {
      contents = contents.replace(
        /android\s*\{/,
        `android {
    // @generated ego-force-compile-sdk-36
    compileSdkVersion 36
    // @generated end ego-force-compile-sdk-36`
      );
    }

    cfg.modResults.contents = contents;
    return cfg;
  });
}

module.exports = withForceTargetSdk36;
