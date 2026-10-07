(function () {
  "use strict";

  // ---------- Cargar catálogos desde el JSON embebido ----------
  const CAT = JSON.parse(document.getElementById("catalogos-data").textContent);
  const NUCLEO = JSON.parse(document.getElementById("nucleo-data").textContent || "null");
  const MODO = JSON.parse(document.getElementById("form-mode").textContent);
  const RETURN_TO = JSON.parse(document.getElementById("return-to-data").textContent || '"/nucleos"');

  // ---------- Utilidades ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function option(value, label, selected = false) {
    const o = document.createElement("option");
    o.value = value;
    o.textContent = label;
    if (selected) o.selected = true;
    return o;
  }

  function fillSelect(el, items, { placeholder = "-- Seleccione --", valueKey = "id", labelFn } = {}) {
    el.innerHTML = "";
    el.appendChild(option("", placeholder));
    items.forEach((it) => {
      el.appendChild(option(it[valueKey], labelFn ? labelFn(it) : `${it.codigo} - ${it.nombre}`));
    });
  }

  function siguienteCodigo(codigo) {
    const digits = String(codigo ?? "").trim();
    if (!/^\d+$/.test(digits)) return "";
    const nextDigits = digits.split("");
    let carry = 1;
    for (let index = nextDigits.length - 1; index >= 0 && carry; index--) {
      const sum = Number(nextDigits[index]) + carry;
      nextDigits[index] = String(sum % 10);
      carry = Math.floor(sum / 10);
    }
    if (carry) nextDigits.unshift(String(carry));
    return nextDigits.join("");
  }

  if (!NUCLEO) {
    const inputCodigo = $("#codigo");
    let cargandoCodigo = false;
    const sugerirCodigo = async () => {
      if (cargandoCodigo || inputCodigo.value.trim()) return;
      cargandoCodigo = true;
      try {
        const response = await fetch("/nucleos/api/ultimo-codigo");
        if (!response.ok) return;
        const data = await response.json();
        const suggestion = siguienteCodigo(data.codigo);
        if (suggestion && !inputCodigo.value.trim()) inputCodigo.value = suggestion;
      } catch {
        return;
      } finally {
        cargandoCodigo = false;
      }
    };
    inputCodigo.addEventListener("focus", sugerirCodigo);
    inputCodigo.addEventListener("click", sugerirCodigo);
  }

  // ---------- Filtrado encadenado Provincia → Municipio → Consejo → Circunscripción/Bodega ----------
  const selProv = $("#provincia_id");
  const selMun  = $("#municipio_id");
  const selCon  = $("#consejo_popular_id");
  const inputCir = $("#circunscripcion_codigo");
  const inputBod = $("#bodega_codigo");
  const inputDireccion = $("#direccion");
  const memoriaUbicacionKey = "nucleo-form-ubicacion-v1";
  let restaurandoUbicacion = false;

  fillSelect(selProv, CAT.provincias, { placeholder: "-- Provincia --", labelFn: p => `${p.codigo} - ${p.nombre}` });
  fillSelect(selMun, [], { placeholder: "-- Municipio --" });
  fillSelect(selCon, [], { placeholder: "-- Consejo --" });
  function fillCodeList(input, listId, items) {
    const list = $(listId);
    list.replaceChildren(...items.map(item => option(item.codigo, String(item.codigo))));
    input.disabled = !selCon.value;
    input.value = "";
  }

  fillCodeList(inputCir, "#circunscripciones-list", []);
  fillCodeList(inputBod, "#bodegas-list", []);

  selProv.addEventListener("change", () => {
    const pid = Number(selProv.value);
    const items = CAT.municipios.filter(m => m.provincia_id === pid);
    fillSelect(selMun, items, { placeholder: "-- Municipio --" });
    fillSelect(selCon, [], { placeholder: "-- Consejo --" });
    fillCodeList(inputCir, "#circunscripciones-list", []);
    fillCodeList(inputBod, "#bodegas-list", []);
  });

  selMun.addEventListener("change", () => {
    const mid = Number(selMun.value);
    const items = CAT.consejos.filter(c => c.municipio_id === mid);
    fillSelect(selCon, items, { placeholder: "-- Consejo --" });
    fillCodeList(inputCir, "#circunscripciones-list", []);
    fillCodeList(inputBod, "#bodegas-list", []);
  });

  selCon.addEventListener("change", () => {
    const cid = Number(selCon.value);
    fillCodeList(inputCir, "#circunscripciones-list", CAT.circunscripciones.filter(c => c.consejo_popular_id === cid));
    fillCodeList(inputBod, "#bodegas-list", CAT.bodegas.filter(b => b.consejo_popular_id === cid));
  });

  function guardarUbicacionEnCache() {
    if (restaurandoUbicacion) return;
    const zona = document.querySelector("input[name=zona_residencia]:checked");
    const valores = {
      provincia_id: selProv.value,
      municipio_id: selMun.value,
      consejo_popular_id: selCon.value,
      circunscripcion_codigo: inputCir.value,
      bodega_codigo: inputBod.value,
      direccion: inputDireccion.value,
      zona_residencia_id: zona ? zona.value : "",
    };
    try {
      localStorage.setItem(memoriaUbicacionKey, JSON.stringify(valores));
    } catch (error) {
      console.warn("No se pudo guardar la ubicación del formulario en el navegador", error);
    }
  }

  function restaurarUbicacionDesdeCache() {
    let valores;
    try {
      valores = JSON.parse(localStorage.getItem(memoriaUbicacionKey) || "null");
    } catch {
      return;
    }
    if (!valores) return;

    restaurandoUbicacion = true;
    if (Array.from(selProv.options).some(item => item.value === valores.provincia_id)) {
      selProv.value = valores.provincia_id;
      selProv.dispatchEvent(new Event("change"));
      if (Array.from(selMun.options).some(item => item.value === valores.municipio_id)) {
        selMun.value = valores.municipio_id;
        selMun.dispatchEvent(new Event("change"));
        if (Array.from(selCon.options).some(item => item.value === valores.consejo_popular_id)) {
          selCon.value = valores.consejo_popular_id;
          selCon.dispatchEvent(new Event("change"));
          inputCir.value = valores.circunscripcion_codigo || "";
          inputBod.value = valores.bodega_codigo || "";
        }
      }
    }
    inputDireccion.value = valores.direccion || "";
    const zona = Array.from(document.querySelectorAll("input[name=zona_residencia]"))
      .find(item => item.value === valores.zona_residencia_id);
    if (zona) zona.checked = true;
    restaurandoUbicacion = false;
    guardarUbicacionEnCache();
  }

  [selProv, selMun, selCon].forEach(select => select.addEventListener("change", guardarUbicacionEnCache));
  [inputCir, inputBod, inputDireccion].forEach(input => input.addEventListener("input", guardarUbicacionEnCache));
  document.querySelectorAll("input[name=zona_residencia]").forEach(input =>
    input.addEventListener("change", guardarUbicacionEnCache));
  restaurarUbicacionDesdeCache();

  const selectKeyBuffers = new WeakMap();
  document.addEventListener("pointerover", event => {
    if (event.target instanceof HTMLSelectElement) event.target.focus({ preventScroll: true });
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Delete") return;
    const target = event.target;

    if (target instanceof HTMLSelectElement) {
      if (!Array.from(target.options).some(item => item.value === "")) return;
      event.preventDefault();
      if (target.value !== "") {
        target.value = "";
        target.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }

    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
    if (target.readOnly) return;
    if (target instanceof HTMLInputElement && ["button", "submit", "reset", "image", "hidden", "file", "range", "color"].includes(target.type)) return;

    event.preventDefault();
    if (target instanceof HTMLInputElement && ["checkbox", "radio"].includes(target.type)) {
      if (target.checked) {
        target.checked = false;
        target.dispatchEvent(new Event("change", { bubbles: true }));
      }
      return;
    }

    if (target.value !== "") {
      target.value = "";
      target.dispatchEvent(new Event("input", { bubbles: true }));
      target.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
  document.addEventListener("keydown", event => {
    const select = event.target;
    if (!(select instanceof HTMLSelectElement) || !/^\d$/.test(event.key)) return;
    event.preventDefault();
    const previous = selectKeyBuffers.get(select);
    const buffer = previous && Date.now() - previous.time < 800 ? previous.value + event.key : event.key;
    const options = Array.from(select.options).filter(item => item.value);
    const match = options.find(item => item.textContent.trim().startsWith(buffer))
      || options.find(item => item.textContent.trim().startsWith(event.key));
    selectKeyBuffers.set(select, { value: match ? buffer : event.key, time: Date.now() });
    if (match) {
      select.value = match.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  const focusableSelector = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]):not(.btn-remove), a[href]';
  const fieldSelector = 'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';
  let lastArrowLeft = { target: null, time: 0 };
  document.addEventListener("keydown", event => {
    if (event.key !== "ArrowLeft") lastArrowLeft = { target: null, time: 0 };
    const target = event.target;
    if (target instanceof HTMLSelectElement) {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
      event.preventDefault();
      lastArrowLeft = { target: null, time: 0 };
      const fields = $$(fieldSelector).filter(field =>
        field.tabIndex >= 0 && field.getClientRects().length > 0
      );
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        const index = fields.indexOf(target);
        const nextIndex = index + (event.key === "ArrowLeft" ? -1 : 1);
        if (nextIndex >= 0 && nextIndex < fields.length) {
          fields[nextIndex].focus({ preventScroll: true });
        }
        return;
      }

      const currentRect = target.getBoundingClientRect();
      const currentCenterY = currentRect.top + currentRect.height / 2;
      const currentCenterX = currentRect.left + currentRect.width / 2;
      const direction = event.key === "ArrowUp" ? -1 : 1;
      const candidates = fields.filter(field => field !== target).map(field => {
        const rect = field.getBoundingClientRect();
        return {
          field,
          centerY: rect.top + rect.height / 2,
          centerX: rect.left + rect.width / 2,
        };
      }).filter(item => (item.centerY - currentCenterY) * direction > 4);
      if (!candidates.length) return;
      const nearestRowDistance = Math.min(...candidates.map(item =>
        Math.abs(item.centerY - currentCenterY)
      ));
      const next = candidates
        .filter(item => Math.abs(Math.abs(item.centerY - currentCenterY) - nearestRowDistance) < 8)
        .sort((a, b) => Math.abs(a.centerX - currentCenterX) - Math.abs(b.centerX - currentCenterX))[0];
      next.field.focus({ preventScroll: true });
      return;
    }
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) return;
    if (target.matches('[type="radio"], [type="checkbox"]')) return;

    if (event.key === "ArrowLeft") {
      const now = Date.now();
      if (lastArrowLeft.target === target && now - lastArrowLeft.time <= 450) {
        event.preventDefault();
        const controls = $$(focusableSelector).filter(control =>
          control.tabIndex >= 0 && control.getClientRects().length > 0
        );
        const index = controls.indexOf(target);
        if (index > 0) controls[index - 1].focus();
        lastArrowLeft = { target: null, time: 0 };
      } else {
        lastArrowLeft = { target, time: now };
      }
      return;
    }

    if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
    const controls = $$(focusableSelector).filter(control =>
      control !== target && control.tabIndex >= 0 && control.getClientRects().length > 0
    );
    const currentRect = target.getBoundingClientRect();
    const currentCenterY = currentRect.top + currentRect.height / 2;
    const currentCenterX = currentRect.left + currentRect.width / 2;
    const direction = event.key === "ArrowUp" ? -1 : 1;
    const candidates = controls.map(control => {
      const rect = control.getBoundingClientRect();
      return {
        control,
        centerY: rect.top + rect.height / 2,
        centerX: rect.left + rect.width / 2,
      };
    }).filter(item => (item.centerY - currentCenterY) * direction > 4);
    if (!candidates.length) return;
    const nearestRowDistance = Math.min(...candidates.map(item =>
      Math.abs(item.centerY - currentCenterY)
    ));
    const next = candidates
      .filter(item => Math.abs(Math.abs(item.centerY - currentCenterY) - nearestRowDistance) < 8)
      .sort((a, b) => Math.abs(a.centerX - currentCenterX) - Math.abs(b.centerX - currentCenterX))[0];
    event.preventDefault();
    next.control.focus();
  });

  document.addEventListener("click", event => {
    const strategyChoice = event.target.closest('#tbody-estrategias input[type="checkbox"]');
    if (strategyChoice && strategyChoice.checked) {
      strategyChoice.closest("tr").querySelectorAll('input[type="checkbox"]').forEach(choice => {
        if (choice !== strategyChoice) choice.checked = false;
      });
      return;
    }

    const fillButton = event.target.closest("[data-fill-target]");
    if (fillButton) {
      const selector = fillButton.dataset.fillTarget;
      const value = fillButton.dataset.fillValue;
      const inputs = $$(selector);
      const alreadyFilledForAll = inputs.length > 0 && inputs.every(input =>
        boolFromSiNo(input.value) === (value === "Si")
      );
      inputs.forEach(input => {
        input.value = alreadyFilledForAll ? "" : value;
        normalizaSiNo(input);
      });
      return;
    }

    const strategyButton = event.target.closest("[data-fill-strategies]");
    if (strategyButton) {
      const value = strategyButton.dataset.fillStrategies;
      const rows = $$("#tbody-estrategias tr");
      const alreadySelectedForAll = rows.length > 0 && rows.every(row => {
        const selected = row.querySelector('input[type="checkbox"]:checked');
        return selected && selected.value === value;
      });
      rows.forEach(row => {
        row.querySelectorAll('input[type="checkbox"]').forEach(choice => {
          choice.checked = !alreadySelectedForAll && choice.value === value;
        });
      });
    }
  });

  // ---------- Fila de persona (sección 2) ----------
  const tbodyPersonas = $("#tbody-personas");
  const tbodyOcup = $("#tbody-ocupacion");

  function buildOptionList(items) {
    const frag = document.createDocumentFragment();
    frag.appendChild(option("", ""));
    items.forEach(it => frag.appendChild(option(it.id, `${it.codigo}`)));
    return frag;
  }

  function addPersonaRow() {
    const tr = document.createElement("tr");
    tr.className = "persona-row";

    tr.innerHTML = `
      <td class="col-num num"></td>
      <td></td>
      <td><input type="text" class="f-nombre"></td>
      <td><input type="text" class="f-cedula" maxlength="11" inputmode="numeric" pattern="[0-9]{11}" title="Deje vacío o escriba exactamente 11 números" autocomplete="off"></td>
      <td><select class="f-color"></select></td>
      <td><select class="f-parentesco"></select></td>
      <td><select class="f-sexo"></select></td>
      <td><select class="f-escolaridad"></select></td>
      <td><select class="f-sne"></select></td>
      <td><select class="f-consumidor"><option value=""> </option><option value="true">Si</option><option value="false">No</option></select></td>
      <td><select class="f-fuente"></select></td>
      <td><input type="number" step="0.01" min="0" class="f-ingreso"></td>
      <td class="col-x"><button type="button" class="btn-remove" title="Eliminar" tabindex="-1">×</button></td>
    `;
    tbodyPersonas.appendChild(tr);

    const inputCedula = tr.querySelector(".f-cedula");
    inputCedula.addEventListener("input", () => {
      inputCedula.value = inputCedula.value.replace(/[^0-9]/g, "").slice(0, 11);
    });

    // llenar selects con los catálogos (mostramos código para tabular rápido)
    fillSelect(tr.querySelector(".f-color"), CAT.colores_piel, { placeholder: "", labelFn: x => `${x.codigo}` });
    fillSelect(tr.querySelector(".f-parentesco"), CAT.parentescos, { placeholder: "", labelFn: x => `${x.codigo}` });
    fillSelect(tr.querySelector(".f-sexo"), CAT.sexos, { placeholder: "", labelFn: x => `${x.codigo}` });
    fillSelect(tr.querySelector(".f-escolaridad"), CAT.escolaridades, { placeholder: "", labelFn: x => `${x.codigo}` });
    fillSelect(tr.querySelector(".f-sne"), CAT.vinculaciones_sne, { placeholder: "", labelFn: x => `${x.codigo}` });
    fillSelect(tr.querySelector(".f-fuente"), CAT.fuentes_ingreso, { placeholder: "", labelFn: x => `${x.codigo}` });

    // títulos con nombres para que al desplegar se vea el nombre
    decorateOptionsWithName(tr.querySelector(".f-color"), CAT.colores_piel);
    decorateOptionsWithName(tr.querySelector(".f-parentesco"), CAT.parentescos);
    decorateOptionsWithName(tr.querySelector(".f-sexo"), CAT.sexos);
    decorateOptionsWithName(tr.querySelector(".f-escolaridad"), CAT.escolaridades);
    decorateOptionsWithName(tr.querySelector(".f-sne"), CAT.vinculaciones_sne);
    decorateOptionsWithName(tr.querySelector(".f-fuente"), CAT.fuentes_ingreso);

    // perfil (dropdown a la izquierda del nombre) - se inserta en la celda vacía #2
    const perfilCell = tr.children[1];
    const selPerfil = document.createElement("select");
    selPerfil.className = "f-perfil";
    fillSelect(selPerfil, CAT.perfiles, { placeholder: "", labelFn: x => `${x.codigo} - ${x.nombre}` });
    perfilCell.appendChild(selPerfil);

    // Botón eliminar
    tr.querySelector(".btn-remove").addEventListener("click", () => {
      const idx = Array.from(tbodyPersonas.querySelectorAll(".persona-row")).indexOf(tr);
      const nombre = tr.querySelector(".f-nombre").value.trim() || "sin nombre";
      if (!window.confirm(`¿Desea borrar a la persona No. ${idx + 1} (${nombre}) y sus datos de ocupación?`)) return;
      const ocupacionCorrespondiente = tbodyOcup.querySelectorAll(".ocup-row")[idx];
      tr.remove();
      if (ocupacionCorrespondiente) ocupacionCorrespondiente.remove();
      syncOcupacion();
    });

    syncOcupacion();
  }

  function decorateOptionsWithName(select, catalog) {
    Array.from(select.options).forEach((opt, i) => {
      if (!opt.value) return;
      const item = catalog.find(c => String(c.id) === opt.value);
      if (item) opt.textContent = `${item.codigo} - ${item.nombre}`;
    });
  }

  function renumber() {
    Array.from(tbodyPersonas.querySelectorAll(".persona-row")).forEach((tr, i) => {
      tr.querySelector(".num").textContent = i + 1;
    });
  }

  // ---------- Sección 3: ocupación sincronizada ----------
  function buildOcupacionRow(no) {
    const tr = document.createElement("tr");
    tr.className = "ocup-row";
    tr.innerHTML = `
      <td class="col-num">${no}</td>
      <td><select class="o-trabaja"><option value=""></option><option value="1">1</option><option value="2">2</option></select></td>
      <td><select class="o-sector" data-tipo="sector_estatal"></select></td>
      <td><select class="o-sector" data-tipo="empresa_mixta"></select></td>
      <td><select class="o-sector" data-tipo="sector_agropecuario"></select></td>
      <td><select class="o-sector" data-tipo="sector_no_estatal"></select></td>
      <td><select class="o-sector" data-tipo="trabajo_informal"></select></td>
      <td><select class="o-motivo"></select></td>
    `;
    const selTrabaja = tr.querySelector(".o-trabaja");
    selTrabaja.options[1].textContent = "1 - Sí";
    selTrabaja.options[1].dataset.codigo = "1";
    selTrabaja.options[2].textContent = "2 - No";
    selTrabaja.options[2].dataset.codigo = "2";
    selTrabaja.addEventListener("focus", () => {
      selTrabaja.options[1].textContent = "1 - Sí";
      selTrabaja.options[2].textContent = "2 - No";
    });
    selTrabaja.addEventListener("blur", () => {
      selTrabaja.options[1].textContent = "1";
      selTrabaja.options[2].textContent = "2";
    });
    const catalogosSector = {
      sector_estatal: CAT.sectores_estatal,
      empresa_mixta: CAT.empresas_mixtas,
      sector_agropecuario: CAT.sectores_agropecuario,
      sector_no_estatal: CAT.sectores_no_estatal,
      trabajo_informal: CAT.trabajos_informales,
    };
    tr.querySelectorAll(".o-sector").forEach(select => {
      const tipo = select.dataset.tipo;
      const catalogo = catalogosSector[tipo];
      fillSelect(select, catalogo, { placeholder: "", labelFn: item => `${item.codigo}` });
      Array.from(select.options).forEach(optionItem => {
        const item = catalogo.find(entry => String(entry.id) === optionItem.value);
        if (item) {
          optionItem.dataset.codigo = item.codigo;
          optionItem.textContent = `${item.codigo} - ${item.nombre}`;
        }
      });
      select.addEventListener("focus", () => {
        Array.from(select.options).forEach(optionItem => {
          if (optionItem.value) optionItem.textContent = `${optionItem.dataset.codigo} - ${catalogo.find(item => String(item.id) === optionItem.value).nombre}`;
        });
      });
      select.addEventListener("blur", () => {
        Array.from(select.options).forEach(optionItem => {
          if (optionItem.value) optionItem.textContent = optionItem.dataset.codigo;
        });
      });
      select.addEventListener("change", () => {
        if (select.value) selTrabaja.value = "1";
      });
    });

    const selMotivo = tr.querySelector(".o-motivo");
    fillSelect(selMotivo, CAT.motivos_no_trabaja,
      { placeholder: "", labelFn: item => `${item.codigo}` });
    Array.from(selMotivo.options).forEach(optionItem => {
      if (!optionItem.value) return;
      const item = CAT.motivos_no_trabaja.find(entry => String(entry.id) === optionItem.value);
      optionItem.dataset.codigo = item.codigo;
      optionItem.dataset.nombre = item.nombre;
    });
    selMotivo.addEventListener("change", () => {
      if (selMotivo.value) selTrabaja.value = "2";
    });
    selMotivo.addEventListener("focus", () => {
      Array.from(selMotivo.options).forEach(optionItem => {
        if (optionItem.value) optionItem.textContent = `${optionItem.dataset.codigo} - ${optionItem.dataset.nombre}`;
      });
    });
    selMotivo.addEventListener("blur", () => {
      Array.from(selMotivo.options).forEach(optionItem => {
        if (optionItem.value) optionItem.textContent = optionItem.dataset.codigo;
      });
    });

    return tr;
  }

  function syncOcupacion() {
    const count = tbodyPersonas.querySelectorAll(".persona-row").length;
    const actuales = tbodyOcup.querySelectorAll(".ocup-row");
    // ajustar cantidad
    if (actuales.length < count) {
      for (let i = actuales.length; i < count; i++) {
        tbodyOcup.appendChild(buildOcupacionRow(i + 1));
      }
    } else if (actuales.length > count) {
      for (let i = actuales.length - 1; i >= count; i--) {
        actuales[i].remove();
      }
    }
    renumber();
    Array.from(tbodyOcup.querySelectorAll(".ocup-row")).forEach((tr, i) => {
      tr.querySelector(".col-num").textContent = i + 1;
    });
  }

  // ---------- Autocompletado si/no (s/n → Si/No) ----------
  function normalizaSiNo(input) {
    const v = input.value.trim().toLowerCase();
    if (v === "s" || v === "si" || v === "sí") {
      input.value = "Si"; input.classList.add("valido"); input.classList.remove("invalido");
    } else if (v === "n" || v === "no") {
      input.value = "No"; input.classList.add("valido"); input.classList.remove("invalido");
    } else if (v === "") {
      input.classList.remove("valido", "invalido");
    } else {
      input.classList.add("invalido"); input.classList.remove("valido");
    }
  }

  document.addEventListener("input", (e) => {
    if (e.target.classList && e.target.classList.contains("si-no")) {
      normalizaSiNo(e.target);
    }
  });

  // ---------- Botón agregar fila ----------
  $("#btn-add-persona").addEventListener("click", () => {
    addPersonaRow();
    tbodyPersonas.querySelector(".persona-row:last-child .f-nombre")?.focus();
  });

  $("#btn-promedio-ingresos").addEventListener("click", () => {
    const personas = $$("#tbody-personas .persona-row").filter(tr =>
      tr.querySelector(".f-nombre").value.trim() || tr.querySelector(".f-cedula").value.trim()
    );
    const sumaIngresos = personas.reduce((total, tr) => {
      const ingreso = Number(tr.querySelector(".f-ingreso").value);
      return total + (Number.isFinite(ingreso) && ingreso > 0 ? ingreso : 0);
    }, 0);
    const promedio = personas.length ? sumaIngresos / personas.length : 0;
    const resultado = $("#resultado-promedio-ingresos");
    const formatoCUP = new Intl.NumberFormat("es-CU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    resultado.textContent = `Promedio: ${formatoCUP.format(promedio)} CUP (${personas.length} ${personas.length === 1 ? "persona" : "personas"})`;
    resultado.classList.toggle("promedio-alto", promedio >= 4000);
    resultado.classList.toggle("promedio-normal", promedio < 4000);
  });

  // ---------- Cargar filas iniciales ----------
  for (let i = 0; i < (NUCLEO ? NUCLEO.personas.length : 5); i++) addPersonaRow();

  // ---------- Serialización ----------
  function boolFromSiNo(txt) {
    const v = (txt || "").trim().toLowerCase();
    if (v === "si" || v === "sí" || v === "s") return true;
    if (v === "no" || v === "n") return false;
    return null;
  }

  function collectPersonas() {
    const out = [];
    $$("#tbody-personas .persona-row").forEach((tr) => {
      const nombre = tr.querySelector(".f-nombre").value.trim();
      const cedula = tr.querySelector(".f-cedula").value.trim();
      if (!nombre && !cedula) return;
      out.push({
        perfil_id: Number(tr.querySelector(".f-perfil").value) || null,
        nombre_apellidos: nombre,
        cedula: cedula,
        color_piel_id: Number(tr.querySelector(".f-color").value) || null,
        parentesco_id: Number(tr.querySelector(".f-parentesco").value) || null,
        sexo_id: Number(tr.querySelector(".f-sexo").value) || null,
        nivel_escolaridad_id: Number(tr.querySelector(".f-escolaridad").value) || null,
        vinculacion_sne_id: Number(tr.querySelector(".f-sne").value) || null,
        esta_en_registro_consumidor: tr.querySelector(".f-consumidor").value === "" ? null : tr.querySelector(".f-consumidor").value === "true",
        fuente_ingreso_id: Number(tr.querySelector(".f-fuente").value) || null,
        ingreso_mensual_cup: parseFloat(tr.querySelector(".f-ingreso").value) || null,
      });
    });
    return out;
  }

  function collectOcupaciones() {
    const personas = $$("#tbody-personas .persona-row");
    const out = personas.map((pTr, idx) => {
      const oTr = $$("#tbody-ocupacion .ocup-row")[idx];
      if (!oTr) return null;
      const codigoTrabaja = oTr.querySelector(".o-trabaja").value;
      const trabaja = codigoTrabaja === "" ? null : codigoTrabaja === "1";
      const ocupaciones = Array.from(oTr.querySelectorAll(".o-sector"))
        .filter(select => select.value)
        .map(select => ({ tipo_ocupacion: select.dataset.tipo, ocupacion_catalogo_id: Number(select.value) }));
      const motivo = Number(oTr.querySelector(".o-motivo").value) || null;
      return {
        trabaja,
        ocupaciones,
        motivo_no_trabaja_id: motivo,
      };
    });
    return out;
  }

  function collectGastos() {
    const out = [];
    $$("#tbody-gastos tr").forEach((tr) => {
      const monto = parseFloat(tr.querySelector(".g-monto").value);
      const orden = parseInt(tr.querySelector(".g-orden").value, 10);
      if (isNaN(monto) && isNaN(orden)) return;
      out.push({
        tipo_gasto_id: Number(tr.dataset.id),
        monto_cup: isNaN(monto) ? 0 : monto,
        orden_importancia: isNaN(orden) ? null : orden,
      });
    });
    return out;
  }

  function collectDiversidad() {
    const out = [];
    $$("#tbody-diversidad tr").forEach((tr) => {
      const gusta = boolFromSiNo(tr.querySelector(".d-gusta").value);
      const mercado = boolFromSiNo(tr.querySelector(".d-mercado").value);
      const frec = parseInt(tr.querySelector(".d-frec").value, 10);
      if (gusta === null && mercado === null && (isNaN(frec) || frec === 0)) return;
      out.push({
        grupo_alimento_id: Number(tr.dataset.id),
        gusta,
        encontrado_en_mercado: mercado,
        frecuencia_semanal_dias: isNaN(frec) ? 0 : frec,
      });
    });
    return out;
  }

  function collectEstrategias() {
    const out = [];
    $$("#tbody-estrategias tr").forEach((tr) => {
      const selected = tr.querySelector("input[type=checkbox]:checked");
      if (!selected) return;
      out.push({
        estrategia_id: Number(tr.dataset.id),
        aplica: selected.value === "true",
      });
    });
    return out;
  }

  function setValue(selector, value) {
    const element = $(selector);
    if (element) element.value = value == null ? "" : String(value);
  }

  function cargarNucleo(nucleo) {
    setValue("#codigo", nucleo.codigo);
    setValue("#fecha_entrevista", nucleo.fecha_entrevista);
    setValue("#entrevistador_nombre", nucleo.entrevistador_nombre);
    setValue("#provincia_id", nucleo.provincia_id);
    selProv.dispatchEvent(new Event("change"));
    setValue("#municipio_id", nucleo.municipio_id);
    selMun.dispatchEvent(new Event("change"));
    setValue("#consejo_popular_id", nucleo.consejo_popular_id);
    selCon.dispatchEvent(new Event("change"));
    setValue("#circunscripcion_codigo", nucleo.circunscripcion_codigo);
    setValue("#bodega_codigo", nucleo.bodega_codigo);
    setValue("#direccion", nucleo.direccion);
    setValue("#observaciones", nucleo.observaciones);
    setValue("#procede_ayuda", nucleo.procede_ayuda);
    const zona = document.querySelector(`input[name="zona_residencia"][value="${nucleo.zona_residencia_id}"]`);
    if (zona) zona.checked = true;

    nucleo.personas.forEach((persona, index) => {
      const row = $$("#tbody-personas .persona-row")[index];
      const ocupacionRow = $$("#tbody-ocupacion .ocup-row")[index];
      if (!row || !ocupacionRow) return;
      const fields = {
        ".f-perfil": persona.perfil_id,
        ".f-nombre": persona.nombre_apellidos,
        ".f-cedula": persona.cedula,
        ".f-color": persona.color_piel_id,
        ".f-parentesco": persona.parentesco_id,
        ".f-sexo": persona.sexo_id,
        ".f-escolaridad": persona.nivel_escolaridad_id,
        ".f-sne": persona.vinculacion_sne_id,
        ".f-consumidor": persona.esta_en_registro_consumidor,
        ".f-fuente": persona.fuente_ingreso_id,
        ".f-ingreso": persona.ingreso_mensual_cup,
        ".o-trabaja": persona.trabaja == null ? "" : persona.trabaja ? "1" : "2",
        ".o-motivo": persona.motivo_no_trabaja_id,
      };
      Object.entries(fields).forEach(([selector, value]) => {
        const element = row.querySelector(selector) || ocupacionRow.querySelector(selector);
        if (element) element.value = value == null ? "" : String(value);
      });
      persona.ocupaciones.forEach(item => {
        const select = ocupacionRow.querySelector(`.o-sector[data-tipo="${item.tipo_ocupacion}"]`);
        if (select) select.value = String(item.ocupacion_catalogo_id);
      });
    });

    const gastos = new Map(nucleo.gastos.map(item => [String(item.tipo_gasto_id), item]));
    $$("#tbody-gastos tr").forEach(row => {
      const item = gastos.get(row.dataset.id);
      if (!item) return;
      row.querySelector(".g-monto").value = item.monto_cup;
      row.querySelector(".g-orden").value = item.orden_importancia ?? "";
    });
    const diversidad = new Map(nucleo.diversidad.map(item => [String(item.grupo_alimento_id), item]));
    $$("#tbody-diversidad tr").forEach(row => {
      const item = diversidad.get(row.dataset.id);
      if (!item) return;
      row.querySelector(".d-gusta").value = item.gusta == null ? "" : item.gusta ? "Si" : "No";
      row.querySelector(".d-mercado").value = item.encontrado_en_mercado == null ? "" : item.encontrado_en_mercado ? "Si" : "No";
      row.querySelector(".d-frec").value = item.frecuencia_semanal_dias;
    });
    const estrategias = new Map(nucleo.estrategias.map(item => [String(item.estrategia_id), item]));
    $$("#tbody-estrategias tr").forEach(row => {
      const item = estrategias.get(row.dataset.id);
      if (!item) return;
      const choice = row.querySelector(`input[value="${item.aplica ? "true" : "false"}"]`);
      if (choice) choice.checked = true;
    });
  }

  function establecerSoloLectura(lectura) {
    document.querySelectorAll(".page input, .page select, .page textarea, #btn-add-persona, .btn-remove, .btn-bulk")
      .forEach(control => { control.disabled = lectura; });
    ["#btn-guardar", "#btn-guardar-top"].forEach(id => {
      const el = $(id);
      if (el) el.hidden = lectura;
    });
    [
      ["#btn-editar", "#btn-editar-top"],
      ["#btn-cancelar-edicion", "#btn-cancelar-edicion-top"],
      ["#btn-eliminar", "#btn-eliminar-top"],
    ].forEach(([a, b]) => {
      if (a) $(a).hidden = !lectura;
      if (b) $(b).hidden = !lectura;
      if (a === "#btn-cancelar-edicion" || b === "#btn-cancelar-edicion-top") {
        if (a) $(a).hidden = lectura;
        if (b) $(b).hidden = lectura;
      }
    });
    document.body.classList.toggle("modo-consulta", lectura);
  }

  if (NUCLEO) {
    cargarNucleo(NUCLEO);
    establecerSoloLectura(true);
    [
      ["#btn-editar", "#btn-editar-top"],
      ["#btn-cancelar-edicion", "#btn-cancelar-edicion-top"],
      ["#btn-eliminar", "#btn-eliminar-top"],
    ].forEach(([primaryId, secondaryId]) => {
      const primary = $(primaryId);
      const secondary = $(secondaryId);
      [primary, secondary].filter(Boolean).forEach(el => {
        el.addEventListener("click", () => {
          if (primaryId.includes("editar")) return establecerSoloLectura(false);
          if (primaryId.includes("cancelar")) return window.location.reload();
          if (primaryId.includes("eliminar")) {
            if (!window.confirm(`¿Eliminar el núcleo ${NUCLEO.codigo} y todos sus datos asociados? Esta acción no se puede deshacer.`)) return;
            return fetch(`/nucleos/${NUCLEO.id}`, { method: "DELETE" }).then(res => {
              if (res.ok) window.location.assign(RETURN_TO);
              else window.alert("No se pudo eliminar el núcleo. Intente nuevamente.");
            });
          }
        });
      });
    });
  }

  // ---------- Envío ----------
  ["#btn-guardar", "#btn-guardar-top"].forEach(id => {
    const el = $(id);
    if (el) {
      el.addEventListener("click", async () => {
        const status = $("#msg-status");
        status.textContent = "Enviando...";

        const zona = document.querySelector("input[name=zona_residencia]:checked");

        const personas = collectPersonas();
        const personaConCedulaInvalida = $$("#tbody-personas .persona-row").find((tr, index) => {
          const cedula = tr.querySelector(".f-cedula").value.trim();
          return cedula !== "" && !/^[0-9]{11}$/.test(cedula);
        });
        if (personaConCedulaInvalida) {
          const nombre = personaConCedulaInvalida.querySelector(".f-nombre").value.trim();
          const personaNumero = Array.from(tbodyPersonas.querySelectorAll(".persona-row")).indexOf(personaConCedulaInvalida) + 1;
          status.textContent = `El carné de ${nombre || `la persona No. ${personaNumero}`} debe tener exactamente 11 números o dejarse vacío.`;
          status.style.color = "crimson";
          personaConCedulaInvalida.querySelector(".f-cedula").focus();
          return;
        }
        const ocupaciones = collectOcupaciones();
        // combinar ocupaciones dentro de cada persona (por índice)
        personas.forEach((p, i) => {
          const o = ocupaciones[i] || {};
          p.trabaja = o.trabaja ?? null;
          p.ocupaciones = o.ocupaciones ?? [];
          p.motivo_no_trabaja_id = o.motivo_no_trabaja_id ?? null;
        });

        const procedeVal = $("#procede_ayuda").value;
        const procede = procedeVal === "" ? null : procedeVal === "true";

        const payload = {
          codigo: $("#codigo").value.trim(),
          fecha_entrevista: $("#fecha_entrevista").value || null,
          entrevistador_nombre: $("#entrevistador_nombre").value.trim() || null,
          provincia_id: Number(selProv.value),
          municipio_id: Number(selMun.value),
          consejo_popular_id: Number(selCon.value),
          circunscripcion_codigo: inputCir.value.trim() || null,
          bodega_codigo: inputBod.value.trim() || null,
          zona_residencia_id: zona ? Number(zona.value) : 0,
          direccion: $("#direccion").value.trim() || null,
          procede_ayuda: procede,
          observaciones: $("#observaciones").value.trim() || null,
          personas,
          gastos: collectGastos(),
          diversidad: collectDiversidad(),
          estrategias: collectEstrategias(),
        };

        if (!payload.codigo) { status.textContent = "Falta el código del núcleo"; return; }
        if (!payload.provincia_id || !payload.municipio_id || !payload.consejo_popular_id) {
          status.textContent = "Complete Provincia, Municipio y Consejo Popular"; return;
        }
        if (!payload.zona_residencia_id) { status.textContent = "Seleccione la zona de residencia"; return; }

        try {
          const res = await fetch(NUCLEO ? `/nucleos/${NUCLEO.id}` : "/nucleos", {
            method: NUCLEO ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            status.textContent = typeof err.detail === "string"
              ? err.detail
              : Array.isArray(err.detail)
                ? err.detail.map(item => item.msg).join(" ")
                : "No se pudo guardar el núcleo. Revise los datos e intente nuevamente.";
            status.style.color = "crimson";
            return;
          }
          const data = await res.json();
          const query = new URLSearchParams({ guardado: "true" });
          if (NUCLEO) {
            query.set("return_to", RETURN_TO);
            window.location.assign(`/nucleos/${data.id}?${query.toString()}`);
          } else {
            query.set("codigo_guardado", data.codigo);
            window.location.assign(`/nucleos/nuevo?${query.toString()}`);
          }
        } catch (ex) {
          status.textContent = "Error de red: " + ex.message;
          status.style.color = "crimson";
        }
      });
    }
  });
})();