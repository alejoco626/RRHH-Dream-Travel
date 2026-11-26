"use strict";
/* ===== Reclutamiento: candidatos, matriz, resumen del proceso y programación ===== */
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const DIAS_SEM = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];
const fmtF = (iso) => (iso && /^\d{4}-\d{2}-\d{2}/.test(iso) ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) : "");
const fmtH = (hhmm) => { if (!hhmm) return ""; const [hh, mm] = hhmm.split(":").map(Number); return `${((hh + 11) % 12) + 1}:${String(mm).padStart(2, "0")} ${hh < 12 ? "a. m." : "p. m."}`; };
const pct = (v) => (v === null || v === undefined ? "—" : Math.round(v * 100) + " %");
let cfgSel = null;
async function configSel() { if (!cfgSel) cfgSel = await llamar("sel_config"); return cfgSel; }
const claseEstado = (e) => ({ "Nuevo": "", "En evaluación": "av", "Entrevista": "az", "Finalista": "ok", "Contratado": "ok", "Descartado": "mal", "Declinó": "mal" }[e] || "");
const claseGrupo = (g) => (g && g.startsWith("A") ? "ok" : g && g.startsWith("B") ? "av" : g && g.startsWith("C") ? "mal" : "");
const claseAsist = (a) => (a === "Confirmada" ? "ok" : ["De baja", "No respondió"].includes(a) ? "mal" : ["Reagendar", "Pendiente de confirmar", "Enviar link"].includes(a) ? "av" : "");
const claseSit = (s) => ({ "Atrasada": "mal", "Hoy": "av", "Próxima": "az", "Cerrada": "" }[s] || "");
const CORTO = { cv: "CV", ventas: "Ventas", llamada: "Llamada", simulacion: "Simulación", bitrix: "Bitrix24", excel: "Excel" };
function chip(t, c) { return h("span", { class: "chip " + (c || "") }, t); }
function chipPct(v, cfg) { if (v === null || v === undefined) return h("span", { class: "tenue" }, "—"); return chip(pct(v), v >= cfg.umbral_a ? "ok" : v >= cfg.umbral_b ? "av" : "mal"); }
function campoF(etiqueta, ctrl, { req, completo } = {}) { return h("label", { class: "campo" + (completo ? " completo" : "") }, h("span", { class: req ? "req" : "" }, etiqueta), h("span", { class: "x" }, ctrl)); }
function selectDe(opciones, valor, extra) { const s = h("select", extra || {}, opciones.map((o) => h("option", { value: o, selected: o === valor }, o))); return s; }
function sinFilas(t) { return h("div", { class: "vacio" }, t); }
function skTabla() { return h("div", { class: "tarjeta" }, esqueleto(8)); }

/* ============================ CANDIDATOS ============================ */
async function paginaCandidatos(m, ctx) {
  const cfg = await configSel();
  const est = { estado: "__activos", grupo: "", buscar: "", id: null, datos: null };
  const franja = h("div", { class: "franja-etapas" });
  const tabla = h("div", { class: "scroll", style: { flex: 1 } });
  const detalle = h("div", { class: "form tarjeta det" }, h("div", { class: "vacio" }, "Elige un candidato para ver su ficha"));
  const busca = h("input", { placeholder: "Buscar por nombre, teléfono o correo…" });
  const selGrupo = h("select", {}, h("option", { value: "" }, "Todos los grupos"), cfg.grupos.map((g) => h("option", { value: g }, g)));
  const total = h("div", { class: "total" });
  const pagina = h("div", { class: "pagina" },
    cabecera(m.titulo, "Registro de candidatos, igual que en el libro: un candidato por fila",
      h("button", { class: "btn fan", onclick: cargarJson }, "Cargar datos (JSON)"),
      h("button", { class: "btn fan", onclick: exportarJson }, "Exportar datos"),
      h("button", { class: "btn pri", onclick: () => editar(null) }, "+ Nuevo candidato")),
    franja,
    h("div", { class: "cuerpo" }, h("div", { class: "lista tarjeta" }, h("div", { class: "barra" }, busca, selGrupo, total), tabla), detalle));

  async function cargarJson() {
    const e = await intentar(() => llamar("datos_elegir")); if (!e) return;
    let modo = "agregar";
    if (e.cambian) {
      modo = await modal("Cargar datos", h("div", {}, h("p", {}, `El archivo trae ${e.candidatos} candidatos nuevos y ${e.programacion} actividades nuevas.`),
        h("p", {}, `Además, ${e.cambian} candidatos que ya están en la app tienen datos distintos (estado, observaciones, evaluación…).`),
        h("p", { class: "tenue" }, "Si actualizas, lo del archivo reemplaza lo que ya estaba en esos campos. Se crea un respaldo antes.")),
        [{ texto: "Cancelar", valor: false }, { texto: "Solo agregar nuevos", valor: "agregar" }, { texto: "Agregar y actualizar", tipo: "pri", valor: "actualizar" }]);
      if (!modo) return;
    }
    const r = await intentar(() => llamar("datos_aplicar", e.ruta, modo === "actualizar")); if (!r) return;
    toast(r.mensaje); pagina.refrescar();
  }
  async function exportarJson() { const r = await intentar(() => llamar("datos_exportar")); if (r) toast(r.mensaje); }

  function pintarFranja(r) {
    const activos = cfg.activos.reduce((a, e) => a + (r.por_estado[e] || 0), 0);
    const items = [["__activos", "En proceso", activos], ...cfg.estados.map((e) => [e, e, r.por_estado[e] || 0])];
    const max = Math.max(1, ...items.map((x) => x[2]));
    franja.replaceChildren(...items.map(([k, t, n]) => h("div", { class: "etapa" + (est.estado === k ? " sel" : ""), onclick: () => { est.estado = est.estado === k ? "" : k; pagina.refrescar(); } },
      h("b", {}, n), h("small", {}, t), h("div", { class: "bar", style: { width: (n / max * 100) + "%" } }))));
  }

  function pintarTabla(r) {
    if (!r.filas.length) { tabla.replaceChildren(sinFilas(r.todos ? "Ningún candidato coincide con el filtro." : "Aún no hay candidatos. Agrega uno o carga el archivo de datos.")); total.textContent = "0"; return; }
    const cab = ["Candidato", "Asistencia", "Estado", "Prueba", "Entrevista", "Resultado", "Grupo"];
    const cuerpo = r.filas.map((f) => h("tr", { class: "fila-nueva" + (f.id === est.id ? " sel" : ""), onclick: () => abrir(f.id) },
      h("td", { title: f.nombre }, h("b", {}, f.nombre), f.entrevista_hoy ? chip("Hoy", "av") : null, h("small", { class: "sub-nombre" }, f.puesto)),
      h("td", {}, chip(f.asistencia, claseAsist(f.asistencia))), h("td", {}, chip(f.estado, claseEstado(f.estado))),
      h("td", {}, fmtH(f.horario_prueba)), h("td", {}, [fmtF(f.fecha_entrevista).slice(0, 5), fmtH(f.hora_entrevista)].filter(Boolean).join(" · ")),
      h("td", {}, chipPct(f.comparable, cfg)), h("td", {}, f.grupo === "Pendiente de evaluar" ? h("span", { class: "tenue" }, f.hechas ? `Faltan ${f.falta.length}` : "Sin evaluar") : chip(f.grupo.split(":")[0], claseGrupo(f.grupo)))));
    tabla.replaceChildren(h("table", { class: "compacta" }, h("thead", {}, h("tr", {}, cab.map((c) => h("th", {}, c)))), h("tbody", {}, cuerpo)));
    total.textContent = `${r.total} de ${r.todos}`;
  }

  async function abrir(id) {
    est.id = id;
    const r = est.datos; const f = r && r.filas.find((x) => x.id === id);
    if (!f) { detalle.replaceChildren(h("div", { class: "vacio" }, "Elige un candidato para ver su ficha")); return; }
    $$("tbody tr", tabla).forEach((tr, i) => tr.classList.toggle("sel", r.filas[i] && r.filas[i].id === id));
    const fila = (t, v) => (v ? h("div", { class: "dato" }, h("small", {}, t), h("div", {}, v)) : null);
    const barrasP = h("div", { class: "mini-pruebas" }, cfg.pruebas.map(([k, n]) => h("div", { class: "mp" }, h("small", {}, CORTO[k]), chipPct(f.resultados[k], cfg))));
    const cierres = cfg.estados.filter((e) => e !== f.estado);
    detalle.replaceChildren(
      h("div", { class: "franja" }),
      h("div", { class: "det-cab" }, h("h2", {}, f.nombre), h("div", {}, chip(f.estado, claseEstado(f.estado)), " ", chip(f.puesto, ""), f.ronda ? chip(f.ronda + " ronda", "") : null)),
      h("div", { class: "det-cuerpo scroll" },
        h("div", { class: "resultado-grande" }, h("div", {}, h("small", {}, "Promedio comparable"), h("b", {}, pct(f.comparable))), h("div", {}, h("small", {}, "Posición"), h("b", {}, f.ranking ? "#" + f.ranking : "—")), h("div", {}, h("small", {}, "Grupo"), chip(f.grupo.split(":")[0] === "Pendiente de evaluar" ? "Sin grupo" : f.grupo, claseGrupo(f.grupo)))),
        barrasP,
        f.falta.length && f.hechas ? h("div", { class: "aviso-falta" }, "Falta registrar: " + f.falta.join(", ").toLowerCase()) : null,
        f.sugerencia ? h("div", { class: "sugerencia" }, h("span", {}, `Siguiente paso sugerido: ${f.sugerencia}`), h("button", { class: "btn pri peq", onclick: () => cambiarEstado(f, f.sugerencia) }, "Aplicar")) : null,
        fila("Teléfono", f.telefono), fila("Correo", f.correo), fila("Fuente", f.fuente), fila("Se postuló", fmtF(f.fecha_aplicacion)),
        fila("Prueba de habilidades", f.horario_prueba ? [fmtF(f.fecha_prueba), fmtH(f.horario_prueba)].filter(Boolean).join(" · ") : ""),
        fila("Entrevista", f.fecha_entrevista ? [fmtF(f.fecha_entrevista), fmtH(f.hora_entrevista)].filter(Boolean).join(" · ") : ""),
        fila("Motivo", f.motivo), fila("Observaciones", f.observaciones), fila("Pendientes por confirmar", f.pendientes),
        h("div", { class: "dato" }, h("small", {}, "Mover a"), h("div", { class: "mover" }, cierres.map((e) => h("button", { class: "btn sec peq", onclick: () => cambiarEstado(f, e) }, e))))),
      h("div", { class: "acciones" },
        h("button", { class: "btn pri", onclick: () => evaluar(f.id) }, "Evaluar"),
        h("button", { class: "btn sec", onclick: () => editar(f.id) }, "Editar"),
        h("button", { class: "btn peligro", onclick: () => eliminar(f) }, "Eliminar")));
  }

  async function cambiarEstado(f, nuevo) {
    let motivo = "";
    if (cfg.cerrados.includes(nuevo) && nuevo !== "Contratado") { motivo = await preguntar("Motivo", `¿Por qué pasa a «${nuevo}»? (opcional)`, f.motivo || "", true); if (motivo === null) return; }
    const r = await intentar(() => llamar("candidato_estado", f.id, nuevo, motivo)); if (r === undefined) return;
    toast(`${f.nombre}: ${nuevo}`); await pagina.refrescar(); abrir(f.id);
  }

  async function eliminar(f) {
    if (!(await confirmar(`¿Eliminar a ${f.nombre} y toda su evaluación? No se puede deshacer.`, "Eliminar candidato", true, "Eliminar"))) return;
    if ((await intentar(() => llamar("candidato_eliminar", f.id))) === undefined) return;
    toast("Candidato eliminado"); est.id = null; await pagina.refrescar();
    detalle.replaceChildren(h("div", { class: "vacio" }, "Elige un candidato para ver su ficha"));
  }

  async function editar(id) {
    const r = await intentar(() => llamar("candidato_obtener", id)); if (!r) return;
    const v = r.valores, ctl = {};
    const t = (k, ph) => (ctl[k] = h("input", { value: v[k] || "", placeholder: ph || "" }));
    const f = (k) => { const i = t(k); mascaraFecha(i); i.value = fmtF(v[k]) || ""; return i; };
    const hr = (k) => { const i = t(k, "15:00"); i.value = v[k] || ""; return i; };
    const sl = (k, ops) => (ctl[k] = selectDe(ops, v[k]));
    const motivo = (ctl.motivo = h("textarea", { value: v.motivo || "", placeholder: "Por qué no continúa" }));
    const cuerpo = h("div", { class: "rejilla" },
      campoF("Candidato", t("nombre"), { req: true, completo: true }), campoF("Puesto", sl("puesto", cfg.puestos)), campoF("Fuente", sl("fuente", cfg.fuentes)),
      campoF("Teléfono / WhatsApp", t("telefono", "5555 1234")), campoF("Correo", t("correo")),
      campoF("Fecha de aplicación", f("fecha_aplicacion")), campoF("Asistencia", sl("asistencia", cfg.asistencias)),
      campoF("Ronda", sl("ronda", cfg.rondas)), campoF("Estado", sl("estado", cfg.estados)),
      campoF("Fecha de la prueba", f("fecha_prueba")), campoF("Horario de la prueba", hr("horario_prueba")),
      campoF("Fecha de entrevista", f("fecha_entrevista")), campoF("Hora de entrevista", hr("hora_entrevista")),
      campoF("Observaciones", (ctl.observaciones = h("textarea", { value: v.observaciones || "" })), { completo: true }),
      campoF("Pendientes por confirmar", (ctl.pendientes = h("textarea", { value: v.pendientes || "", style: { minHeight: "46px" } })), { completo: true }),
      campoF("Motivo del cierre", motivo, { completo: true }));
    const guardar = async (confirmarDup) => {
      const vals = {}; for (const k in ctl) vals[k] = ctl[k].value;
      const r2 = await intentar(() => llamar("candidato_guardar", id, vals, !!confirmarDup)); if (!r2) return false;
      if (r2.confirmar) { if (!(await confirmar(r2.confirmar + "\n\n¿Guardar de todos modos?", "Posible duplicado", false, "Guardar"))) return false; return guardar(true); }
      (r2.avisos || []).forEach((a) => toast(a, "info")); toast("Candidato guardado"); est.id = r2.id; await pagina.refrescar(); abrir(r2.id); return true;
    };
    await modal(id ? "Editar candidato" : "Nuevo candidato", cuerpo, [{ texto: "Cancelar", valor: false }, { texto: "Guardar", tipo: "pri", valor: true, antes: async () => (await guardar()) }], { ancho: "720px" });
  }

  async function evaluar(id) { await abrirEvaluacion(id, cfg); await pagina.refrescar(); abrir(id); }

  let ultimo = 0;
  pagina.refrescar = async () => {
    const mi = ++ultimo;
    if (!est.datos) { tabla.replaceChildren(esqueleto(9)); }
    const r = await intentar(() => llamar("candidatos", est.buscar, est.estado, est.grupo)); if (!r || mi !== ultimo) return;
    est.datos = r; pintarFranja(r); pintarTabla(r);
  };
  pagina.abrirRegistro = async (id) => {
    if (!est.datos || !est.datos.filas.some((x) => x.id === id)) { est.estado = ""; est.grupo = ""; selGrupo.value = ""; busca.value = ""; est.buscar = ""; est.id = id; await pagina.refrescar(); }
    abrir(id);
  };
  busca.addEventListener("input", debounce(() => { est.buscar = busca.value; pagina.refrescar(); }));
  selGrupo.addEventListener("change", () => { est.grupo = selGrupo.value; pagina.refrescar(); });
  pagina.nuevoCon = async () => editar(null);
  const baseRef = pagina.refrescar;
  pagina.refrescar = async (o) => { await baseRef(o); if (est.id) abrir(est.id); };
  return pagina;
}

/* ---------- ventana de evaluación por criterios ---------- */
async function abrirEvaluacion(id, cfg) {
  const r = await intentar(() => llamar("evaluacion_obtener", id)); if (!r) return;
  const det = r.detalle, bloques = [];
  const resumen = h("div", { class: "resumen-eval" }, h("span", { class: "tenue" }, "Calificando…"));
  const calcular = debounce(async () => {
    const c = await intentar(() => llamar("evaluacion_calcular", det), true); if (!c) return;
    resumen.replaceChildren(h("div", {}, h("small", {}, "Promedio comparable (CV, ventas, simulación)"), h("b", {}, pct(c.comparable)), c.comparable === null ? h("small", { class: "tenue" }, " faltan: " + ["cv", "ventas", "simulacion"].filter((k) => c.resultados[k] === null).map((k) => cfg.pruebas.find((p) => p[0] === k)[1].toLowerCase()).join(", ")) : null),
      h("div", {}, chip(c.grupo, claseGrupo(c.grupo))));
    bloques.forEach((b, i) => { const k = cfg.pruebas[i][0]; b.pct.replaceChildren(chipPct(c.resultados[k], cfg)); });
  }, 120);
  const secciones = det.secciones.map((sec, i) => {
    const ch = h("span", {});
    const filas = sec.criterios.map((cr) => {
      const botones = [];
      if (cr.maximo === 10) {
        const inp = h("input", { type: "number", min: 0, max: 10, step: 0.5, value: cr.calificacion ?? "", class: "num-eval", placeholder: "0–10" });
        inp.addEventListener("input", () => { cr.calificacion = inp.value === "" ? null : Number(inp.value); calcular(); });
        return h("div", { class: "ce" }, h("span", { class: "ct" }, cr.criterio), inp);
      }
      for (let n = 0; n <= 5; n++) {
        const b = h("button", { type: "button", class: "nt" + (cr.calificacion === n ? " on" : ""), onclick: () => { cr.calificacion = cr.calificacion === n ? null : n; botones.forEach((x, k) => x.classList.toggle("on", cr.calificacion === k)); calcular(); } }, n);
        botones.push(b);
      }
      return h("div", { class: "ce" }, h("span", { class: "ct" }, cr.criterio), h("div", { class: "notas" }, botones));
    });
    if (cfg.secciones[i].global) {
      const inp = h("input", { type: "number", min: 0, max: 10, step: 0.5, value: sec.global ?? "", class: "num-eval", placeholder: "0–10" });
      inp.addEventListener("input", () => { sec.global = inp.value === "" ? null : Number(inp.value); calcular(); });
      filas.push(h("div", { class: "ce global" }, h("span", { class: "ct" }, "Nota global sobre 10 (solo si no hay detalle por criterio)"), inp));
    }
    const bloque = h("details", { class: "sec-eval", open: i === 0 }, h("summary", {}, h("b", {}, sec.nombre), ch), h("div", { class: "crits" }, filas));
    bloques.push({ pct: ch });
    return bloque;
  });
  const obs = h("textarea", { value: r.observaciones || "", placeholder: "Observaciones del evaluador" });
  const pen = h("textarea", { value: det.pendientes || "", placeholder: "Pendientes por confirmar", style: { minHeight: "46px" } });
  pen.addEventListener("input", () => { det.pendientes = pen.value; });
  const rec = h("input", { value: r.recomendacion || "", placeholder: "Recomendación (si está vacía se calcula sola)" });
  const cuerpo = h("div", { class: "eval" }, h("div", { class: "escala" }, cfg.escala), resumen, secciones, campoF("Observaciones", obs, {}), campoF("Pendientes por confirmar", pen, {}), campoF("Recomendación", rec, {}));
  calcular();
  let sugerencia = null;
  const ok = await modal(`Evaluación · ${r.nombre}`, cuerpo, [{ texto: "Cancelar", valor: false }, { texto: "Guardar evaluación", tipo: "pri", valor: true, antes: async () => {
    det.pendientes = pen.value;
    const g = await intentar(() => llamar("evaluacion_guardar", id, det, obs.value, rec.value, "", false)); if (!g) return false;
    sugerencia = g.sugerencia; toast("Evaluación guardada"); return true;
  } }], { ancho: "820px", fijo: true });
  if (ok && sugerencia && (await confirmar(`Según el resultado, lo recomendado es pasar a «${sugerencia}». ¿Aplicarlo ahora?`, "Siguiente paso", false, "Sí, aplicar")))
    await intentar(() => llamar("candidato_estado", id, sugerencia, ""));
}

/* ============================ MATRIZ Y RANKING ============================ */
async function paginaMatriz(m, ctx) {
  const cuerpo = h("div", { class: "scroll", style: { flex: 1 } }, skTabla());
  const filtro = h("select", {}, [["act", "Solo en proceso"], ["todos", "Todos"]].map(([v, t]) => h("option", { value: v }, t)));
  const bus = h("input", { placeholder: "Buscar candidato…" });
  const pagina = h("div", { class: "pagina" }, cabecera(m.titulo, "Resultados por prueba, promedio comparable y grupo. La posición se calcula sola", h("button", { class: "btn fan", onclick: () => pagina.refrescar() }, "Actualizar")),
    h("div", { class: "tarjeta", style: { flex: 1, minHeight: 0, display: "flex", flexDirection: "column" } }, h("div", { class: "barra" }, bus, filtro, h("div", { class: "total", id: "mt-total" })), cuerpo));
  let datos = null;
  function pintar() {
    if (!datos) return;
    const q = bus.value.trim().toLowerCase(), act = filtro.value === "act";
    const filas = datos.filas.filter((f) => (!act || ["Nuevo", "En evaluación", "Entrevista", "Finalista", "Contratado"].includes(f.estado)) && (!q || f.nombre.toLowerCase().includes(q)));
    const cfg = datos;
    const falta = datos.faltan.filter((f) => !q || f.nombre.toLowerCase().includes(q));
    const celda = (v) => h("td", { class: "cel-p", style: v === null ? {} : { background: `color-mix(in srgb, ${v >= cfg.umbral_a ? "var(--ok)" : v >= cfg.umbral_b ? "var(--aviso)" : "var(--mal)"} ${Math.round(18 + v * 22)}%, transparent)` } }, v === null ? h("span", { class: "tenue" }, "—") : pct(v));
    const tabla = h("table", { class: "matriz" }, h("thead", {}, h("tr", {}, h("th", {}, "#"), h("th", {}, "Candidato"), h("th", {}, "Estado"), datos.pruebas.map(([k, n]) => h("th", { title: n }, CORTO[k])), h("th", {}, "Comparable"), h("th", {}, "Grupo"), h("th", {}, "Recomendación"))),
      h("tbody", {}, filas.map((f) => h("tr", { class: "fila-nueva", onclick: () => ctx.ir("candidatos", { id: f.id }) },
        h("td", {}, f.ranking ? h("b", {}, f.ranking) : h("span", { class: "tenue" }, "—")), h("td", {}, h("b", {}, f.nombre)), h("td", {}, chip(f.estado, claseEstado(f.estado))),
        datos.pruebas.map(([k]) => celda(f.resultados[k])), h("td", {}, chipPct(f.comparable, cfg)),
        h("td", {}, f.grupo === "Pendiente de evaluar" ? h("span", { class: "tenue" }, "Pendiente") : chip(f.grupo.split(":")[0], claseGrupo(f.grupo))), h("td", { title: f.recomendacion }, f.recomendacion)))));
    cuerpo.replaceChildren(filas.length ? tabla : sinFilas("Sin candidatos para mostrar."),
      ...(falta.length ? [h("div", { class: "falta" }, h("h3", {}, `Falta registrar (${falta.length})`), h("p", { class: "tenue" }, "Candidatos en proceso con evaluación incompleta."), falta.map((f) => h("div", { class: "item click", onclick: () => ctx.ir("candidatos", { id: f.id }) }, h("span", { class: "n" }, f.nombre), h("span", { class: "s" }, f.falta.join(", ").toLowerCase()))))] : []));
    $("#mt-total").textContent = `${filas.length} candidatos`;
  }
  pagina.refrescar = async () => {
    if (!datos) cuerpo.replaceChildren(skTabla());
    const r = await intentar(() => llamar("matriz")); if (!r) return; datos = r; pintar();
  };
  bus.addEventListener("input", debounce(pintar)); filtro.addEventListener("change", pintar);
  return pagina;
}

/* ============================ RESUMEN DEL PROCESO ============================ */
async function paginaProceso(m, ctx) {
  const raiz = h("div", { class: "grid-res" });
  const pagina = h("div", { class: "pagina" }, cabecera(m.titulo, "Cómo va la convocatoria: personas, resultados y lo que sigue"), h("div", { class: "scroll", style: { flex: 1, paddingRight: "6px" } }, raiz));
  const kpi = (clase, ic, n, t, sub, ir) => h("div", { class: `tarjeta kpi ${clase}`, style: ir ? { cursor: "pointer" } : {}, onclick: ir }, h("div", { class: "ic" }, ic), h("div", {}, h("div", { class: "num", "data-n": n }, "0"), h("div", {}, t), h("small", {}, sub || "")));
  const anima = () => $$(".num[data-n]", raiz).forEach((n) => { const fin = Number(n.dataset.n), t0 = performance.now(); const paso = (t) => { const p = Math.min(1, (t - t0) / 450); n.textContent = Math.round(fin * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(paso); }; requestAnimationFrame(paso); });
  pagina.refrescar = async () => {
    if (!raiz.children.length) raiz.replaceChildren(...Array.from({ length: 4 }, () => h("div", { class: "tarjeta s3" }, esqueleto(3))));
    const cfg = await configSel();
    const r = await intentar(() => llamar("proceso")); if (!r) return;
    const val = (lista, e) => (lista.find((x) => x.etiqueta === e) || { valor: 0 }).valor;
    const activos = ["Nuevo", "En evaluación", "Entrevista", "Finalista"].reduce((a, e) => a + val(r.estados, e), 0);
    const embudo = ["Nuevo", "En evaluación", "Entrevista", "Finalista", "Contratado"].map((e) => ({ etiqueta: e, valor: val(r.estados, e) }));
    const cierres = ["Descartado", "Declinó"].map((e) => ({ etiqueta: e, valor: val(r.estados, e) }));
    const sinCero = (l) => l.filter((x) => x.valor > 0);
    raiz.replaceChildren(
      h("div", { class: "s3" }, kpi("", "👥", r.total, "Candidatos", `${activos} en proceso`, () => ctx.ir("candidatos"))),
      h("div", { class: "s3" }, kpi("o", "📞", r.por_confirmar, "Por confirmar", "sin confirmar asistencia", () => ctx.ir("candidatos"))),
      h("div", { class: "s3" }, kpi("v", "⭐", val(r.grupos, "A: finalista"), "Grupo A", `${val(r.grupos, "B: con potencial")} en grupo B`, () => ctx.ir("matriz"))),
      h("div", { class: "s3" }, kpi("m", "✅", val(r.estados, "Contratado"), "Contratados", `${r.con_seis} con las 6 pruebas`)),
      h("div", { class: "s6" }, tarjeta("Embudo de selección", barrasH(embudo, { color: "var(--c1)" }), { nota: "Personas en cada etapa del proceso", extra: h("button", { class: "btn fan peq", onclick: () => ctx.ir("candidatos") }, "Ver candidatos") })),
      h("div", { class: "s6" }, tarjeta("Grupos por resultado", dona(sinCero(r.grupos).filter((x) => !x.etiqueta.startsWith("Pendiente")).map((x) => ({ etiqueta: x.etiqueta, valor: x.valor })), { centro: r.con_ranking }), { color: "c4", nota: "Solo con CV, ventas y simulación calificados" })),
      h("div", { class: "s6" }, tarjeta("Promedio por prueba", barrasH(r.promedio_pruebas.map((x, i) => ({ etiqueta: `${CORTO[cfg.pruebas[i][0]]} (${x.n})`, valor: x.valor || 0 })), { color: "var(--c1)", formato: (v) => fmtNum(v) + " %", max: 100 }), { color: "c3", nota: "Entre paréntesis, cuántos candidatos la tienen" })),
      h("div", { class: "s6" }, tarjeta("Próximas entrevistas", r.entrevistas_proximas.length ? r.entrevistas_proximas.map((e) => h("div", { class: "item" }, h("span", { class: "dot e" }), h("span", { class: "n" }, e.nombre), h("span", { class: "s" }, [fmtF(e.fecha), fmtH(e.hora)].filter(Boolean).join(" · ")))) : h("div", { class: "vacio", style: { padding: "14px" } }, "No hay entrevistas agendadas."), { color: "c2", nota: `Capacidad: ${cfg.capacidad.entrevistas_por_dia} por día, ${cfg.capacidad.entrevistas_horario}` })),
      h("div", { class: "s4" }, tarjeta("Puestos", dona(sinCero(r.puestos)), { nota: "Por puesto al que aplican" })),
      h("div", { class: "s4" }, tarjeta("Fuentes", dona(sinCero(r.fuentes)), { color: "c3", nota: "De dónde llegan" })),
      h("div", { class: "s4" }, tarjeta("Cierres", barrasH(cierres, { color: "var(--c2)" }), { color: "c2", nota: "No continúan en el proceso" })),
      h("div", { class: "s6" }, tarjeta("Asistencia", barrasH(sinCero(r.asistencias), {}), { nota: "Estado de confirmación de todos los candidatos" })),
      h("div", { class: "s6" }, tarjeta("Convocatorias", barrasH(sinCero(r.por_convocatoria), {}), { color: "c4", nota: "Candidatos por ciclo de publicidad" })));
    anima();
  };
  return pagina;
}

/* ============================ PROGRAMACIÓN ============================ */
async function paginaProgramacion(m, ctx) {
  const cfg = await configSel();
  const est = { fase: "", buscar: "", pend: true, vista: "lista", mes: null };
  const franja = h("div", { class: "franja-etapas embudo-prog" });
  const cont = h("div", { class: "scroll", style: { flex: 1 } });
  const bus = h("input", { placeholder: "Buscar actividad o responsable…" });
  const sp = h("input", { type: "checkbox", checked: true, style: { width: "auto" } });
  const tabs = h("div", { class: "tabs" }, [["lista", "Lista"], ["calendario", "Calendario"]].map(([k, t]) => h("button", { class: "tab" + (est.vista === k ? " on" : ""), "data-k": k, onclick: () => { est.vista = k; $$(".tab", tabs).forEach((b) => b.classList.toggle("on", b.dataset.k === k)); pagina.refrescar(); } }, t)));
  const total = h("div", { class: "total" });
  const pagina = h("div", { class: "pagina" }, cabecera(m.titulo, "Embudo aparte: publicidad → pruebas → entrevistas → documentos → firma → capacitación",
    h("button", { class: "btn pri", onclick: () => editar(null) }, "+ Nueva actividad")), franja,
    h("div", { class: "tarjeta", style: { flex: 1, minHeight: 0, display: "flex", flexDirection: "column" } }, h("div", { class: "barra" }, tabs, bus, h("label", { class: "chk" }, sp, " Solo pendientes"), total), cont));

  function pintarFranja(r) {
    const max = Math.max(1, ...r.por_fase.map((x) => x.total));
    franja.replaceChildren(...r.por_fase.map((f, i) => h("div", { class: "etapa" + (est.fase === f.fase ? " sel" : ""), onclick: () => { est.fase = est.fase === f.fase ? "" : f.fase; pagina.refrescar(); } },
      h("small", {}, `${i + 1}. ${f.fase}`), h("b", {}, f.total - f.cerradas), h("small", {}, f.atrasadas ? `${f.atrasadas} atrasada${f.atrasadas > 1 ? "s" : ""}` : f.hoy ? `${f.hoy} hoy` : "al día"),
      f.atrasadas ? h("span", { class: "punto-mal" }) : null, h("div", { class: "bar", style: { width: (f.total / max * 100) + "%" } }))));
  }

  function lista(r) {
    if (!r.filas.length) { cont.replaceChildren(sinFilas("Sin actividades con ese filtro.")); return; }
    const filas = r.filas.map((a) => h("tr", { class: "fila-nueva" + (a.situacion === "Atrasada" ? " atrasado" : ""), onclick: () => editar(a.id) },
      h("td", {}, h("b", {}, fmtF(a.fecha_inicio)), a.fecha_fin && a.fecha_fin !== a.fecha_inicio ? h("small", { class: "tenue" }, " → " + fmtF(a.fecha_fin)) : null),
      h("td", { title: a.actividad }, a.actividad), h("td", {}, chip(a.fase, "")), h("td", {}, a.responsable), h("td", {}, chip(a.estado, a.estado === "Completada" ? "ok" : a.estado === "Sin reporte" ? "" : "av")), h("td", {}, chip(a.situacion, claseSit(a.situacion))),
      h("td", { onclick: (e) => e.stopPropagation() }, a.estado !== "Completada" ? h("button", { class: "btn sec peq", onclick: async () => { const rep = await preguntar("Reporte", "¿Cómo salió? (opcional)", a.reporte || "", true); if (rep === null) return; if ((await intentar(() => llamar("prog_estado", a.id, "Completada", rep))) !== undefined) { toast("Actividad completada"); pagina.refrescar(); } } }, "✓ Completar") : null)));
    cont.replaceChildren(h("table", {}, h("thead", {}, h("tr", {}, ["Fecha", "Actividad", "Fase", "Responsable", "Estado", "Situación", ""].map((c) => h("th", {}, c)))), h("tbody", {}, filas)));
  }

  async function calendario() {
    const hoy = new Date(); if (!est.mes) est.mes = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, "0")}`;
    const r = await intentar(() => llamar("calendario", est.mes)); if (!r) return;
    const [A, M] = r.mes.split("-").map(Number), primero = new Date(A, M - 1, 1), nDias = new Date(A, M, 0).getDate(), desfase = (primero.getDay() + 6) % 7;
    const celdas = [];
    for (let i = 0; i < desfase; i++) celdas.push(h("div", { class: "dia vacio-d" }));
    for (let d = 1; d <= nDias; d++) {
      const iso = `${A}-${String(M).padStart(2, "0")}-${String(d).padStart(2, "0")}`, info = r.dias[iso] || { actividades: [], entrevistas: [] }, dow = (desfase + d - 1) % 7;
      const lleno = info.entrevistas.length >= r.capacidad.entrevistas_por_dia;
      celdas.push(h("div", { class: "dia" + (iso === r.hoy ? " hoy" : "") + (dow > 4 ? " fin" : ""), onclick: () => verDia(iso, info) },
        h("div", { class: "num-dia" }, d), info.actividades.slice(0, 3).map((a) => h("div", { class: "ev f" + (cfg.fases.indexOf(a.fase) + 1) + (a.estado === "Completada" ? " hecho" : ""), title: a.texto }, a.texto)), info.actividades.length > 3 ? h("small", { class: "tenue" }, `+${info.actividades.length - 3} más`) : null,
        info.entrevistas.length ? h("div", { class: "ev ent" + (lleno ? " lleno" : "") }, `☏ ${info.entrevistas.length}/${r.capacidad.entrevistas_por_dia} entrevistas`) : null));
    }
    const mover = (n) => { const f = new Date(A, M - 1 + n, 1); est.mes = `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}`; calendario(); };
    cont.replaceChildren(h("div", { class: "cal-cab" }, h("button", { class: "btn sec peq", onclick: () => mover(-1) }, "‹"), h("b", {}, `${MESES[M - 1]} ${A}`), h("button", { class: "btn sec peq", onclick: () => mover(1) }, "›"), h("button", { class: "btn fan peq", onclick: () => { est.mes = null; calendario(); } }, "Hoy")),
      h("div", { class: "cal" }, DIAS_SEM.map((d) => h("div", { class: "cal-h" }, d)), celdas),
      h("div", { class: "cal-notas" }, h("h3", {}, "Notas del mes"), r.notas.length ? r.notas.map((n) => h("p", {}, n)) : h("p", { class: "tenue" }, "Sin notas."),
        h("p", { class: "tenue" }, `Pruebas: ${r.capacidad.pruebas_horario}. Capacidad ${r.capacidad.pruebas_por_hora} candidatos por hora. Entrevistas: ${r.capacidad.entrevistas_horario}, ${r.capacidad.entrevistas_por_dia} por día.`)));
    total.textContent = "";
  }

  function verDia(iso, info) {
    const cuerpo = h("div", {}, info.actividades.length ? info.actividades.map((a) => h("div", { class: "item click", onclick: () => { $$("#modales .velo").forEach((v) => v.cerrar && v.cerrar()); editar(a.id); } }, h("span", { class: "dot" }), h("span", { class: "n" }, a.texto), h("span", { class: "s" }, [a.responsable, a.estado].filter(Boolean).join(" · ")))) : h("p", { class: "tenue" }, "Sin actividades programadas."),
      info.entrevistas.length ? h("h3", { style: { marginTop: "14px" } }, "Entrevistas") : null, info.entrevistas.map((e) => h("div", { class: "item" }, h("span", { class: "dot e" }), h("span", { class: "n" }, e.nombre), h("span", { class: "s" }, fmtH(e.hora)))));
    modal(fmtF(iso), cuerpo, [{ texto: "Cerrar", tipo: "pri", valor: true }, { texto: "+ Actividad este día", valor: "nueva" }]).then((v) => { if (v === "nueva") editar(null, iso); });
  }

  async function editar(id, fecha) {
    const r = await intentar(() => llamar("prog_obtener", id)); if (!r) return;
    const v = r.valores; if (fecha && !id) v.fecha_inicio = fecha;
    const ctl = {};
    const f = (k) => { const i = h("input", { value: fmtF(v[k]) }); mascaraFecha(i); return (ctl[k] = i); };
    const dl = h("datalist", { id: "dl-resp" }, cfg.responsables.map((x) => h("option", { value: x })));
    const cuerpo = h("div", { class: "rejilla" }, dl,
      campoF("Actividad", (ctl.actividad = h("input", { value: v.actividad })), { req: true, completo: true }),
      campoF("Fecha de inicio", f("fecha_inicio"), { req: true }), campoF("Fecha final", f("fecha_fin")),
      campoF("Fase", (ctl.fase = selectDe(cfg.fases, v.fase))), campoF("Estado", (ctl.estado = selectDe(cfg.estados_act, v.estado))),
      campoF("Responsable", (ctl.responsable = h("input", { value: v.responsable, list: "dl-resp", placeholder: "JACKY Y ADRIANA" })), { completo: true }),
      campoF("Reporte", (ctl.reporte = h("textarea", { value: v.reporte })), { completo: true }), campoF("Notas", (ctl.notas = h("textarea", { value: v.notas, style: { minHeight: "46px" } })), { completo: true }));
    const botones = [{ texto: "Cancelar", valor: false }];
    if (id) botones.splice(1, 0, { texto: "Eliminar", tipo: "peligro", valor: "borrar" });
    botones.push({ texto: "Guardar", tipo: "pri", valor: true, antes: async () => {
      const vals = {}; for (const k in ctl) vals[k] = ctl[k].value;
      const g = await intentar(() => llamar("prog_guardar", id, vals)); if (!g) return false; toast("Actividad guardada"); return true;
    } });
    const res = await modal(id ? "Editar actividad" : "Nueva actividad", cuerpo, botones, { ancho: "640px" });
    if (res === "borrar" && (await confirmar("¿Eliminar esta actividad?", "Eliminar", true, "Eliminar")) && (await intentar(() => llamar("prog_eliminar", id))) !== undefined) toast("Actividad eliminada");
    pagina.refrescar();
  }

  pagina.refrescar = async () => {
    if (!cont.children.length) cont.replaceChildren(esqueleto(8));
    est.buscar = bus.value; est.pend = sp.checked;
    const r = await intentar(() => llamar("prog_listar", est.fase, est.buscar, est.pend)); if (!r) return;
    pintarFranja(r);
    if (est.vista === "lista") { lista(r); total.textContent = `${r.filas.length} actividades`; } else await calendario();
  };
  bus.addEventListener("input", debounce(() => pagina.refrescar())); sp.addEventListener("change", () => pagina.refrescar());
  return pagina;
}
