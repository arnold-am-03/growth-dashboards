// Tooltip reactivo para los graficos SVG. Lee data-tip de barras y puntos.
(function () {
  let tip = null;

  function ensureTip() {
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "chart-tip";
      document.body.appendChild(tip);
    }
    return tip;
  }

  function hide() {
    if (tip) tip.classList.remove("on");
  }

  document.addEventListener("mousemove", function (e) {
    const el = e.target.closest ? e.target.closest("[data-tip]") : null;
    if (!el) {
      hide();
      return;
    }
    const t = ensureTip();
    t.textContent = el.getAttribute("data-tip");
    t.classList.add("on");

    const pad = 14;
    const r = t.getBoundingClientRect();
    let x = e.clientX + pad;
    let y = e.clientY + pad;
    if (x + r.width > window.innerWidth) x = e.clientX - r.width - pad;
    if (y + r.height > window.innerHeight) y = e.clientY - r.height - pad;
    t.style.left = x + "px";
    t.style.top = y + "px";
  });

  document.addEventListener("scroll", hide, true);
  window.addEventListener("blur", hide);
})();
