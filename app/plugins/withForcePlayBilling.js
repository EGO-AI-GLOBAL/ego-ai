const { withProjectBuildGradle } = require("expo/config-plugins");

/**
 * Força Google Play Billing Library ≥ 8.0.0 em TODO o projeto.
 * A Play rejeita updates se qualquer variante/transitiva trouxer billing antigo.
 * Ver: Status da política → Biblioteca Google Play Faturamento (prazo 31/08).
 */
function withForcePlayBilling(config) {
  return withProjectBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== "groovy") return cfg;
    let contents = cfg.modResults.contents;
    if (contents.includes("ego-force-play-billing-8")) return cfg;

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
    cfg.modResults.contents = contents;
    return cfg;
  });
}

module.exports = withForcePlayBilling;
