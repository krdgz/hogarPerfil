(function () {
  "use strict";

  const search = document.getElementById("buscar-nucleo");
  const rows = Array.from(document.querySelectorAll("#tabla-listado tbody tr[data-search]"));
  const count = document.getElementById("conteo-nucleos");
  const empty = document.getElementById("sin-resultados");

  search.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    rows.forEach(row => {
      const matches = row.dataset.search.includes(query);
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} ${visible === 1 ? "núcleo" : "núcleos"}`;
    empty.hidden = visible !== 0 || rows.length === 0;
  });
})();