/** Links Stripe para /planos — lê marketing/brand/config.json no site publicado. */
(function () {
  const CONFIG_PATH = "../brand/config.json";
  const FALLBACK = {
    connection: "https://buy.stripe.com/dRm5kFaYmbTs5TydNE4ow0M",
    premium: "https://buy.stripe.com/14A7sNgiG6z8chWgZQ4ow02",
    total: "https://buy.stripe.com/5kQeVf6I60aK95K6lc4ow03",
  };
  const UTM = "utm_source=site&utm_medium=planos&utm_campaign=egoai_checkout";

  function withUtm(url) {
    if (!url || url === "#") return url;
    return url + (url.includes("?") ? "&" : "?") + UTM;
  }

  function apply(cfg) {
    const stripe = cfg.stripe || {};
    const map = {
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
