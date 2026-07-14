/** Links Stripe PJ para /planos — lê marketing/brand/config.json no site publicado. */
(function () {
  const CONFIG_PATH = "../brand/config.json";
  const FALLBACK = {
    launch: "https://buy.stripe.com/7sY3cu923evNaqP6ovfYY04",
    connection: "https://buy.stripe.com/4gM5kC6TV4Vd6az3cjfYY05",
    premium: "https://buy.stripe.com/3cIeVc5PRevN56vcMTfYY02",
    total: "https://buy.stripe.com/14AeVcdijevN8iH3cjfYY03",
  };
  const UTM = "utm_source=site&utm_medium=planos&utm_campaign=egoai_checkout";

  function withUtm(url) {
    if (!url || url === "#") return url;
    return url + (url.includes("?") ? "&" : "?") + UTM;
  }

  function apply(cfg) {
    const stripe = cfg.stripe || {};
    const map = {
      "plan-cta-launch": stripe.launch || FALLBACK.launch,
      "plan-cta-connection": stripe.connection || FALLBACK.connection,
      "plan-cta-premium": stripe.premium || FALLBACK.premium,
      "plan-cta-total": stripe.total || FALLBACK.total,
    };
    Object.entries(map).forEach(function ([id, url]) {
      const el = document.getElementById(id);
      if (el && url) {
        el.href = withUtm(url);
        el.target = "_blank";
        el.rel = "noopener noreferrer";
      }
    });
    if (cfg.supportEmail) {
      const em = document.getElementById("footer-email");
      if (em) {
        em.href = "mailto:" + cfg.supportEmail;
        em.textContent = cfg.supportEmail;
      }
    }
  }

  fetch(CONFIG_PATH)
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(function (cfg) {
      apply(cfg || { stripe: FALLBACK, supportEmail: "contato@egoai.com.br" });
    })
    .catch(function () {
      apply({ stripe: FALLBACK, supportEmail: "contato@egoai.com.br" });
    });
})();
