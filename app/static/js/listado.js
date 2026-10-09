(function () {
  "use strict";

  const estados = document.querySelectorAll(".estado-nucleo");
  const valorAEstado = value => value === "true" ? true : value === "false" ? false : null;
  const textoEstado = value => value === "true" ? "Procede" : value === "false" ? "No procede" : "Pendiente";

  estados.forEach(select => {
    select.addEventListener("change", async () => {
      const valorAnterior = select.dataset.valorActual ?? "";
      const nuevoValor = select.value;
      const estadoAnterior = textoEstado(valorAnterior);
      const nuevoEstado = textoEstado(nuevoValor);
      if (!window.confirm(`¿Cambiar el núcleo ${select.dataset.codigo} de «${estadoAnterior}» a «${nuevoEstado}»?`)) {
        select.value = valorAnterior;
        return;
      }

      select.disabled = true;
      const feedback = select.parentElement.querySelector(".estado-feedback");
      feedback.textContent = "Guardando…";
      try {
        const response = await fetch(`/nucleos/${select.closest("tr").dataset.nucleoId}/estado`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ procede_ayuda: valorAEstado(nuevoValor) }),
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || "No se pudo actualizar el estado.");
        }
        window.location.reload();
      } catch (error) {
        select.value = valorAnterior;
        feedback.textContent = error.message;
        window.alert(error.message);
      } finally {
        select.disabled = false;
      }
    });
    select.dataset.valorActual = select.value;
  });

  document.querySelectorAll(".btn-calcular-promedio").forEach(button => {
    button.addEventListener("click", async () => {
      const resultado = button.parentElement.querySelector(".promedio-nucleo");
      if (!resultado.hidden) {
        resultado.hidden = true;
        button.textContent = "Calcular";
        button.setAttribute("aria-expanded", "false");
        return;
      }
      if (button.dataset.calculado === "true") {
        resultado.hidden = false;
        button.textContent = "Ocultar";
        button.setAttribute("aria-expanded", "true");
        return;
      }

      button.disabled = true;
      button.textContent = "Calculando…";
      resultado.hidden = false;
      resultado.textContent = "Calculando…";
      try {
        const nucleoId = button.closest("tr").dataset.nucleoId;
        const response = await fetch(`/nucleos/api/${nucleoId}/promedio-ingresos`);
        if (!response.ok) throw new Error("No se pudo calcular el promedio.");
        const data = await response.json();
        const formatoCUP = new Intl.NumberFormat("es-CU", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
        resultado.textContent = `${formatoCUP.format(data.promedio)} CUP`;
        resultado.classList.toggle("promedio-alto", data.promedio >= 4000);
        button.dataset.calculado = "true";
        button.textContent = "Ocultar";
        button.setAttribute("aria-expanded", "true");
      } catch (error) {
        resultado.textContent = error.message;
        button.textContent = "Reintentar";
      } finally {
        button.disabled = false;
      }
    });
  });
})();