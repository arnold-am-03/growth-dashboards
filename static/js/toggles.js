// Conmutadores del dashboard:
// 1) Panorama por canal: botones [data-canal] cambian los valores de las
//    tarjetas que llevan data-v-<canal> / data-n-<canal>.
// 2) Referencia de comparación: cada fila .cmp-row puede traer opciones
//    [data-opcion] con valor numérico y formateado; al elegir una se
//    actualiza el valor esperado y se recalcula el delta.
(function () {
  // --- 1) canal ---
  document.querySelectorAll(".switch[data-switch='canal']").forEach(function (sw) {
    var alcance = document.getElementById(sw.dataset.target);
    if (!alcance) return;
    sw.querySelectorAll("button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        sw.querySelectorAll("button").forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        var canal = btn.dataset.canal;
        alcance.querySelectorAll("[data-v-" + canal + "]").forEach(function (el) {
          el.textContent = el.getAttribute("data-v-" + canal);
        });
      });
    });
  });

  // --- 2) referencia de comparación ---
  function pintarDelta(fila, esperadoNum) {
    var badge = fila.querySelector(".delta");
    var realNum = parseFloat(fila.dataset.real);
    if (!badge || !isFinite(realNum) || !isFinite(esperadoNum) || esperadoNum === 0) return;
    var d = (realNum - esperadoNum) / Math.abs(esperadoNum);
    var mejorAlto = (fila.dataset.mejor || "alto") === "alto";
    var positivo = (d >= 0 && mejorAlto) || (d < 0 && !mejorAlto);
    badge.textContent = (d >= 0 ? "+" : "") + (d * 100).toFixed(1) + "%";
    badge.classList.remove("up", "down", "flat");
    badge.classList.add(positivo ? "up" : "down");
  }

  document.querySelectorAll(".cmp-row").forEach(function (fila) {
    var botones = fila.querySelectorAll(".cmp-opciones button");
    if (!botones.length) return;
    var esperadoEl = fila.querySelector(".cmp-val.expected .n");
    botones.forEach(function (btn) {
      btn.addEventListener("click", function () {
        botones.forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        if (esperadoEl) esperadoEl.textContent = btn.dataset.fmt;
        pintarDelta(fila, parseFloat(btn.dataset.num));
      });
    });
  });
})();
