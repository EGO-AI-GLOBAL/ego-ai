const { withDangerousMod } = require("@expo/config-plugins");
const {
  mergeContents,
} = require("@expo/config-plugins/build/utils/generateCode");
const fs = require("fs");
const path = require("path");

const FMT_PATCH = `
  # @generated begin xcode26-fmt-fix - expo prebuild (fmt 11 + Xcode 26)
  fmt_base = File.join(installer.sandbox.root, 'fmt', 'include', 'fmt', 'base.h')
  if File.exist?(fmt_base)
    content = File.read(fmt_base)
    unless content.include?('Xcode 26 workaround')
      patched = content.gsub(
        /^(#elif defined\\(__cpp_consteval\\)\\n# define FMT_USE_CONSTEVAL) 1/,
        "// Xcode 26 workaround: disable consteval\\n\\1 0"
      )
      if patched != content
        File.chmod(0644, fmt_base)
        File.write(fmt_base, patched)
      end
    end
  end
  # @generated end xcode26-fmt-fix`;

/** RN 0.76 ships fmt 11.0.2, which fails on Xcode 26+ without this Podfile patch. */
function withXcode26FmtFix(config) {
  return withDangerousMod(config, [
    "ios",
    async (cfg) => {
      const podfile = path.join(cfg.modRequest.platformProjectRoot, "Podfile");
      if (!fs.existsSync(podfile)) {
        return cfg;
      }
      const src = fs.readFileSync(podfile, "utf8");
      if (src.includes("xcode26-fmt-fix")) {
        return cfg;
      }
      const result = mergeContents({
        tag: "xcode26-fmt-fix",
        src,
        newSrc: FMT_PATCH,
        anchor: /post_install do \|installer\|/,
        offset: 1,
        comment: "#",
      });
      if (!result.didMerge) {
        throw new Error(
          "withXcode26FmtFix: não encontrou post_install no Podfile."
        );
      }
      fs.writeFileSync(podfile, result.contents);
      return cfg;
    },
  ]);
}

module.exports = withXcode26FmtFix;
