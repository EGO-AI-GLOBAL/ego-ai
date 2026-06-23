/**
 * Carrossel de avatares no site — dados em avatars-site.json
 */
(function () {
  const strip = document.getElementById("avatar-strip");
  const speech = document.getElementById("avatar-speech");
  if (!strip || !speech) return;

  function renderSpeech(item) {
    speech.innerHTML =
      "<p><strong>" +
      item.name +
      "</strong> (" +
      item.plan +
      ") — " +
      item.quote +
      "</p>";
  }

  function setActive(card, item) {
    strip.querySelectorAll(".avatar-card").forEach((c) => c.classList.remove("active"));
    card.classList.add("active");
    renderSpeech(item);
  }

  fetch("avatars-site.json")
    .then((r) => (r.ok ? r.json() : []))
    .then((list) => {
      if (!Array.isArray(list) || !list.length) return;
      list.forEach((item, i) => {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "avatar-card" + (i === 0 ? " active" : "");
        card.setAttribute("role", "listitem");
        card.innerHTML =
          '<img src="' +
          item.img +
          '" alt="' +
          item.name +
          '" width="72" height="72" loading="lazy" />' +
          '<div class="name">' +
          item.name +
          "</div>" +
          '<div class="plan-tag">' +
          item.plan +
          "</div>";
        card.addEventListener("click", () => setActive(card, item));
        strip.appendChild(card);
      });
      renderSpeech(list[0]);
    })
    .catch(() => {});
})();
