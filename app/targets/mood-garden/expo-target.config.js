/** @type {import('@bacons/apple-targets/app.plugin').ConfigFunction} */
module.exports = (config) => ({
  type: "widget",
  name: "MoodGardenWidget",
  displayName: "Jardim dos Monstrinhos",
  deploymentTarget: "15.1",
  colors: {
    $accent: "#22C55E",
    $widgetBackground: "#ECFDF5",
  },
  entitlements: {
    "com.apple.security.application-groups":
      config.ios?.entitlements?.["com.apple.security.application-groups"] ?? [
        "group.com.egoai.app.widget",
      ],
  },
});
