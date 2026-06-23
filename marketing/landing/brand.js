/**
 * Carrega marketing/brand/config.json e aplica marca na landing.
 * Hospede a pasta marketing/ (ou landing + brand + img) no mesmo domínio.
 */
(function () {
  const CONFIG_PATH = "../brand/config.json";

  function applyColors(c) {
    if (!c) return;
    const r = document.documentElement.style;
    r.setProperty("--bg", c.bg || r.getPropertyValue("--bg"));
    r.setProperty("--card", c.card || r.getPropertyValue("--card"));
    r.setProperty("--border", c.border || r.getPropertyValue("--border"));
    r.setProperty("--primary", c.primary || r.getPropertyValue("--primary"));
    r.setProperty("--primary-dim", c.primaryDim || r.getPropertyValue("--primary-dim"));
    r.setProperty("--text", c.text || r.getPropertyValue("--text"));
    r.setProperty("--muted", c.muted || r.getPropertyValue("--muted"));
    r.setProperty("--success", c.success || r.getPropertyValue("--success"));
    r.setProperty("--warn", c.warn || r.getPropertyValue("--warn"));
  }

  function withUtm(url, utm) {
    if (!url || url === "#" || !utm) return url;
    const sep = url.includes("?") ? "&" : "?";
    return url + sep + utm;
  }

  function applyBrand(cfg) {
    const name = cfg.brandName || "EGO-AI";
    document.title = `${name} — ${cfg.tagline || "Chega de telas frias"}`;
    const meta = document.querySelector('meta[name="description"]');
    if (meta) {
      meta.content = `${name} — Luna e Leo, assistente com voz e rosto. ${cfg.tagline || ""}`;
    }

    const logoImg = document.getElementById("brand-logo");
    const logoText = document.getElementById("brand-logo-text");
    if (logoImg && cfg.logoPath) {
      logoImg.src = cfg.logoPath;
      logoImg.alt = name;
      logoImg.hidden = false;
    }
    if (logoText) {
      const parts = name.split("-");
      if (parts.length >= 2) {
        logoText.innerHTML = `${parts[0]}<span>-${parts.slice(1).join("-")}</span>`;
      } else {
        logoText.textContent = name;
      }
    }

    const luna = document.getElementById("avatar-luna");
    const leo = document.getElementById("avatar-leo");
    if (luna && cfg.avatarLuna) luna.src = cfg.avatarLuna;
    if (leo && cfg.avatarLeo) leo.src = cfg.avatarLeo;

    applyColors(cfg.colors);

    const play = (cfg.playStoreUrl || "").trim();
    const ios = (cfg.appStoreUrl || "").trim();
    const utm = cfg.utm?.landingDefault || "";

    const playEl = document.getElementById("footer-cta-play");
    const iosEl = document.getElementById("footer-cta-ios");
    const hint = document.getElementById("download-hint");

    function enableStoreLink(el, url, label) {
      if (!el || !url) return;
      const a = document.createElement("a");
      a.className = el.className.replace("store-badge", "").trim() + " btn-buy";
      a.id = el.id;
      a.href = withUtm(url, utm);
      a.textContent = label;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      el.replaceWith(a);
    }

    if (hint) {
      if (play && ios) {
        hint.textContent = "Disponível na Google Play e na App Store.";
      } else if (play) {
        hint.textContent = "Disponível na Google Play. App Store em breve.";
      } else {
        hint.textContent =
          "Android (Google Play) e iPhone (App Store) — links ativos no lançamento público.";
      }
    }

    if (play) enableStoreLink(playEl, play, "Baixar na Google Play");
    if (ios) enableStoreLink(iosEl, ios, "Baixar na App Store");

    ["header-email", "footer-email", "legal-email"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && cfg.supportEmail) {
        el.href = `mailto:${cfg.supportEmail}`;
        if (id === "header-email" || id === "footer-email") el.textContent = cfg.supportEmail;
      }
    });

    const stripe = cfg.stripe || {};
    const planUtm = utm ? utm + "&utm_content=plan" : "";
    const map = {
      "plan-cta-connection": stripe.connection,
      "plan-cta-premium": stripe.premium,
      "plan-cta-total": stripe.total,
    };
    Object.entries(map).forEach(([id, url]) => {
      const el = document.getElementById(id);
      if (el && url) {
        el.href = withUtm(url, planUtm);
        el.target = "_blank";
        el.rel = "noopener noreferrer";
      }
    });

    const footerDomain = document.getElementById("footer-domain");
    if (footerDomain && cfg.domain) footerDomain.textContent = cfg.domain;

    const footerEmail = document.getElementById("footer-email");
    if (footerEmail && cfg.supportEmail) {
      footerEmail.href = `mailto:${cfg.supportEmail}`;
      footerEmail.textContent = cfg.supportEmail;
    }

    const ig = document.getElementById("footer-instagram");
    if (ig && cfg.instagram) {
      const handle = cfg.instagram.replace("@", "");
      ig.href = `https://instagram.com/${handle}`;
      ig.textContent = cfg.instagram;
    }

    const home = document.getElementById("logo-home");
    if (home && cfg.siteUrl) home.href = cfg.siteUrl;

    const footerBrand = document.getElementById("footer-brand");
    if (footerBrand) footerBrand.textContent = name;
  }

  fetch(CONFIG_PATH)
    .then((r) => (r.ok ? r.json() : null))
    .then(applyBrand)
    .catch(() => {
      /* fallback: CSS e HTML estáticos */
    });
})();
