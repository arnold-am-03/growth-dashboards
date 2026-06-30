// Buscador (por titulo) + filtro por etiquetas (KPI) en el mosaico.
(function () {
  const search = document.getElementById("buscador");
  const chips = Array.from(document.querySelectorAll(".chip"));
  const cards = Array.from(document.querySelectorAll(".tile"));
  const empty = document.getElementById("sin-resultados");
  if (!cards.length) return;

  const active = new Set();

  function norm(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function apply() {
    const q = norm(search ? search.value : "");
    let visibles = 0;

    cards.forEach(function (card) {
      const title = norm(card.dataset.title);
      const tags = (card.dataset.tags || "").split("|").filter(Boolean);

      const matchTitle = !q || title.includes(q);
      const matchTags =
        active.size === 0 || tags.some((t) => active.has(t));

      const show = matchTitle && matchTags;
      card.style.display = show ? "" : "none";
      if (show) visibles++;
    });

    if (empty) empty.style.display = visibles ? "none" : "block";
  }

  if (search) search.addEventListener("input", apply);

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      const tag = chip.dataset.tag;
      if (active.has(tag)) {
        active.delete(tag);
        chip.classList.remove("on");
      } else {
        active.add(tag);
        chip.classList.add("on");
      }
      apply();
    });
  });
})();
