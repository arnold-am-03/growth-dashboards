// Pantalla de carga con la imagen de static/brand/loading.svg en loop.
// Aparece si la siguiente página tarda más de 350 ms (típico tras la
// siesta del plan free) y se oculta sola al llegar la respuesta.
(function () {
  var capa = document.getElementById("cargando");
  if (!capa) return;
  var temporizador = null;

  function mostrar() {
    if (temporizador) return;
    temporizador = setTimeout(function () {
      capa.hidden = false;
      requestAnimationFrame(function () { capa.classList.add("on"); });
    }, 350);
  }

  function ocultar() {
    if (temporizador) { clearTimeout(temporizador); temporizador = null; }
    capa.classList.remove("on");
    capa.hidden = true;
  }

  document.addEventListener("click", function (e) {
    var a = e.target.closest ? e.target.closest("a[href]") : null;
    if (!a) return;
    if (a.target === "_blank" || a.hasAttribute("download")) return;
    var url = new URL(a.href, location.href);
    if (url.origin !== location.origin) return;
    if (url.pathname === location.pathname && url.hash) return;
    mostrar();
  });

  document.addEventListener("submit", function () { mostrar(); });

  // al volver con el botón atrás (bfcache) o al terminar de cargar
  window.addEventListener("pageshow", ocultar);
})();
