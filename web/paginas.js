"use strict";
function cabecera(titulo, sub, ...acc) {
  return h("div", { class: "cab" }, h("div", {}, h("h1", {}, titulo), h("p", {}, sub || "")), h("div", { class: "acc" }, acc));
}
function tarjeta(titulo, cuerpo, { color = "", nota, extra, clase = "" } = {}) {
  return h("div", { class: `tarjeta ${color} ${clase}` }, h("div", { class: "franja" }), h("div", { class: "tit" }, h("h3", {}, titulo), extra ? h("span", { style: { marginLeft: "auto" } }, extra) : null), nota ? h("div", { class: "nota" }, nota) : null, h("div", { class: "int" }, cuerpo));
}

/* ======= Resumen ======= */
async function paginaResumen(ctx) {
  const raiz = h("div", { class: "grid-res" });
  const pagina = h("div", { class: "pagina" }, cabecera("Resumen", "Lo que hay que atender hoy y cómo va el proceso"), h("div", { class: "scroll", style: { flex: 1, paddingRight: "6px" } }, raiz));
  const kpi = (clase, ic, num, txt, sub, ir) => h("div", { class: `tarjeta kpi ${clase}`, style: ir ? { cursor: "pointer" } : {}, onclick: ir }, h("div", { class: "ic" }, ic), h("div", {}, h("div", { class: "num", "data-n": num }, "0"), h("div", {}, txt), h("small", {}, sub || "")));
  const anima = (el) => $$(".num[data-n]", el).forEach((n) => { const fin = Number(n.dataset.n), t0 = performance.now(); const paso = (t) => { const p = Math.min(1, (t - t0) / 450); n.textContent = Math.round(fin * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(paso); }; requestAnimationFrame(paso); });
  const lista = (items, vacio, accion) => items.length ? items.map((r) => h("div", { class: "item" + (accion ? " click" : "") , onclick: accion ? () => accion(r) : null }, h("span", { class: "dot " + (r.tipo === "Entrevista" ? "e" : "") }), h("span", { class: "n" }, r.nombre), h("span", { class: "s" }, [r.etapa.replace("Prueba de habilidades", "Habilidades").replace("Pruebas psicométricas", "Psicométricas"), r.hora].filter(Boolean).join(" · ")))) : h("div", { class: "vacio", style: { padding: "14px" } }, vacio);

  pagina.refrescar = async () => {
    if (!raiz.children.length) raiz.replaceChildren(...Array.from({ length: 4 }, () => h("div", { class: "tarjeta s3" }, esqueleto(3))));
    const r = await intentar(() => llamar("resumen")); if (!r) return;
    const g = r.graficas;
    const t = (c) => `${c.Prueba} prueba${c.Prueba !== 1 ? "s" : ""} · ${c.Entrevista} entrevista${c.Entrevista !== 1 ? "s" : ""}`;
    const marcar = async (x) => { if (x.origen !== "embudo") { ctx.ir("pruebas"); return; } const a = await intentar(() => llamar("accion", "embudo", "marcar_recibido", x.id)); if (a) { toast(a.mensaje); pagina.refrescar(); ctx.insignias(); } };
    raiz.replaceChildren(
      h("div", { class: "s3" }, kpi("", "📅", r.hoy.length, "Para hoy", t(r.conteo_hoy))),
      h("div", { class: "s3" }, kpi("o", "🗓", r.manana.length, "Para mañana", t(r.conteo_manana))),
      h("div", { class: "s3" }, kpi("m", "⏰", r.atrasados.length, "Atrasados", "sin marcar como recibidos")),
      h("div", { class: "s3" }, kpi("v", "📎", r.pendientes.total, "Documentos pendientes", "falta subir su archivo", () => ctx.ir("pendientes"))),
      h("div", { class: "s6" }, tarjeta("Hoy", lista(r.hoy, "Nada agendado para hoy."), { nota: "Pruebas y entrevistas de hoy" })),
      h("div", { class: "s6" }, tarjeta("Mañana", lista(r.manana, "Nada agendado para mañana."), { color: "c3", nota: "Para ir confirmando" })),
      h("div", { class: "s8" }, tarjeta("Próximos 14 días", columnas(g.agenda.map((d) => ({ etiqueta: d.etiqueta, valores: [d.pruebas, d.entrevistas] })), { series: [{ nombre: "Pruebas", color: "var(--c1)" }, { nombre: "Entrevistas", color: "var(--c2)" }] }), { nota: `${r.total_por_venir} por venir en total · ${r.total_activos} activos` })),
      h("div", { class: "s4" }, tarjeta("Embudo de selección", dona(g.embudo.map((x) => ({ etiqueta: x.etiqueta, valor: x.valor }))), { color: "c2", nota: "Candidatos activos por etapa" })),
      r.atrasados.length ? h("div", { class: "s12" }, tarjeta("Atrasados", r.atrasados.map((x) => h("div", { class: "item" }, h("span", { class: "dot e" }), h("span", { class: "n" }, x.nombre), h("span", { class: "s" }, `${x.etapa} · ${x.fecha} · ${x.texto}`), h("button", { class: "btn sec peq", onclick: () => marcar(x) }, x.origen === "embudo" ? "Marcar recibido" : "Abrir"))), { color: "c2", nota: "Fecha vencida sin confirmar que asistieron" })) : null,
      h("div", { class: "s6" }, tarjeta("Ranking de candidatos", barrasH(g.ranking.map((x) => ({ etiqueta: x.etiqueta, valor: x.valor })), { formato: (v) => fmtNum(v) + " %", max: 100 }), { color: "c4", nota: "Mejores notas de la prueba de habilidades", extra: h("button", { class: "btn fan peq", onclick: () => ctx.ir("ranking") }, "Ver todo") })),
      h("div", { class: "s6" }, tarjeta("Ausencias por etapa", barrasH(g.ausencias.map((x) => ({ etiqueta: x.etiqueta, valor: x.valor })), {}), { nota: `${r.tarjetas.ausencias_abiertas} abiertas`, extra: h("button", { class: "btn fan peq", onclick: () => ctx.ir("ausencias") }, "Abrir") })),
      h("div", { class: "s7" }, tarjeta(`Días de vacaciones por mes (${new Date().getFullYear()})`, columnas(g.vacaciones_mes.map((x) => ({ etiqueta: x.etiqueta, valores: [x.valor] })), { series: [{ nombre: "Días", color: "var(--c4)" }] }), { color: "c4", nota: `${r.tarjetas.vacaciones_anio} solicitudes este año` })),
      h("div", { class: "s5" }, tarjeta("Personal por departamento", barrasH(g.departamentos.map((x) => ({ etiqueta: x.etiqueta, valor: x.valor })), {}), { nota: `${r.tarjetas.empleados} empleados · ${r.tarjetas.amonestaciones} amonestaciones` })),
      h("div", { class: "s6" }, tarjeta("Cumpleaños próximos", r.cumples.length ? r.cumples.map((c) => h("div", { class: "item" }, h("span", {}, "🎂"), h("span", { class: "n" }, c.nombre), h("span", { class: "s" }, `${c.fecha} (${c.dias === 0 ? "hoy" : c.dias === 1 ? "mañana" : "en " + c.dias + " días"})`))) : h("div", { class: "vacio", style: { padding: "14px" } }, `Sin cumpleaños en los próximos ${r.dias_cumple} días.`), { color: "c3" })),
      h("div", { class: "s6" }, tarjeta("Pendientes de completar", r.pendientes.total ? [r.pendientes.primeros.map((p) => h("div", { class: "item click", onclick: () => ctx.ir(p.tabla, { id: p.id }) }, h("span", { class: "n" }, p.referencia), h("span", { class: "s" }, p.modulo))), r.pendientes.total > 4 ? h("div", { class: "s", style: { color: "var(--sec)", paddingTop: "6px" } }, `y ${r.pendientes.total - 4} más`) : null] : h("div", { class: "vacio", style: { padding: "14px" } }, "Todo al día."), { color: "c2" }))
    );
    anima(raiz);
  };
  return pagina;
}

/* ======= Ranking ======= */
async function paginaRanking(ctx) {
  const st = { plaza: "", incluir: false };
  const tbody = h("tbody"), tarjetas = h("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(210px,1fr))", gap: "12px", marginBottom: "14px" } });
  const selPlaza = h("select", { style: { width: "220px" }, onchange: () => { st.plaza = selPlaza.value; cargar(); } });
  const selEst = h("select", { style: { width: "190px" }, onchange: () => { st.incluir = selEst.value === "1"; cargar(); } }, h("option", { value: "0" }, "Solo activos"), h("option", { value: "1" }, "Con descartados"));
  const total = h("span", { class: "total" });
  async function cargar() {
    const r = await intentar(() => llamar("ranking", st.plaza, st.incluir)); if (!r) return;
    const v = selPlaza.value;
    selPlaza.replaceChildren(h("option", { value: "" }, "Todas las plazas"), ...r.plazas.map((p) => h("option", { value: p }, p))); selPlaza.value = v;
    tarjetas.replaceChildren(...r.mejores.map((m) => h("div", { class: "tarjeta c4", style: { cursor: "pointer", outline: st.plaza === m.plaza ? "2px solid var(--azul2)" : "none" }, onclick: () => { st.plaza = st.plaza === m.plaza ? "" : m.plaza; selPlaza.value = st.plaza; cargar(); } }, h("div", { class: "franja" }), h("div", { class: "int" }, h("small", { style: { color: "var(--sec)" } }, m.plaza), h("div", { style: { fontWeight: 700, fontSize: "15px", margin: "4px 0" } }, m.mejor ? "★ " + m.mejor.candidato : "Sin nota todavía"), h("div", { style: { color: "var(--sec)", fontSize: "12.5px" } }, m.mejor ? `${fmtNum(m.mejor.nota)} % · ${m.candidatos} candidato${m.candidatos !== 1 ? "s" : ""}` : `${m.candidatos} candidato${m.candidatos !== 1 ? "s" : ""}`)))));
    tbody.replaceChildren(...r.filas.map((f, i) => h("tr", { class: "fila-nueva", style: { animationDelay: Math.min(i, 12) * 12 + "ms" } },
      h("td", {}, (i === 0 && f.nota !== null ? "★ " : "") + f.posicion), h("td", {}, f.candidato), h("td", {}, f.plaza),
      h("td", {}, f.nota === null ? "" : h("div", { style: { display: "flex", alignItems: "center", gap: "8px" } }, h("div", { class: "pista", style: { width: "70px", height: "8px", background: "var(--hover)", borderRadius: "6px", overflow: "hidden" } }, h("div", { style: { width: f.nota + "%", height: "100%", background: f.nota >= 70 ? "var(--c4)" : f.nota >= 50 ? "var(--c3)" : "var(--c2)", transition: "width .5s" } })), fmtNum(f.nota) + " %")),
      h("td", {}, h("span", { class: "chip" }, f.etapa)), h("td", {}, f.entrevista))));
    if (!r.filas.length) tbody.append(h("tr", {}, h("td", { colSpan: 6, class: "vacio" }, "No hay candidatos con esos filtros.")));
    total.textContent = `${r.filas.length} candidato${r.filas.length !== 1 ? "s" : ""} · ordenados de la mejor a la menor nota`;
  }
  const p = h("div", { class: "pagina" }, cabecera("Ranking de candidatos", "El mejor candidato de cada plaza, según la nota de la prueba de habilidades", selPlaza, selEst, h("button", { class: "btn sec", onclick: () => ctx.ir("configuracion") }, "Plazas"), h("button", { class: "btn sec", onclick: async () => { const r = await intentar(() => llamar("exportar_ranking", st.plaza, st.incluir)); if (r) toast(r.mensaje); } }, "Exportar a Excel")),
    h("div", { class: "scroll", style: { flex: 1, paddingRight: "6px" } }, tarjetas, h("div", { class: "tarjeta" }, h("div", { class: "franja" }), h("div", { class: "barra" }, total), h("table", {}, h("thead", {}, h("tr", {}, ["#", "Candidato", "Plaza", "Nota", "Etapa", "Entrevista"].map((x) => h("th", {}, x)))), tbody))));
  p.refrescar = cargar;
  return p;
}

/* ======= Pendientes ======= */
async function paginaPendientes(ctx) {
  const tbody = h("tbody"), res = h("span", { class: "total" });
  const p = h("div", { class: "pagina" }, cabecera("Pendientes de completar", "Registros a los que les falta subir su PDF o archivo"),
    h("div", { class: "tarjeta", style: { flex: 1, display: "flex", flexDirection: "column", minHeight: 0 } }, h("div", { class: "franja" }), h("div", { class: "barra" }, res),
      h("div", { class: "scroll", style: { flex: 1 } }, h("table", {}, h("thead", {}, h("tr", {}, ["Módulo", "Referencia", "Falta", "Fecha"].map((x) => h("th", {}, x)))), tbody))));
  p.refrescar = async () => {
    const r = await intentar(() => llamar("pendientes")); if (!r) return;
    tbody.replaceChildren(...r.map((x, i) => h("tr", { class: "fila-nueva", style: { animationDelay: Math.min(i, 12) * 12 + "ms" }, onclick: () => ctx.ir(x.tabla, { id: x.id }) }, h("td", {}, h("span", { class: "chip" }, x.modulo)), h("td", {}, x.referencia), h("td", {}, x.falta), h("td", {}, x.fecha))));
    if (!r.length) tbody.append(h("tr", {}, h("td", { colSpan: 4, class: "vacio" }, "Todo al día. 🎉")));
    res.textContent = `${r.length} pendientes · clic para abrir el registro`;
  };
  return p;
}

/* ======= Documentos ======= */
async function paginaDocumentos(ctx) {
  const st = { ruta: null, sucio: false, areas: [] };
  const lista = h("div"), hoja = h("div", { class: "doc-hoja" }), estado = h("span", { class: "chip" }, "Sin cambios");
  const guardarBtn = h("button", { class: "btn pri", onclick: () => guardar() }, "Guardar cambios");
  const ajustar = (t) => { t.style.height = "auto"; t.style.height = t.scrollHeight + "px"; };
  function marcar(s) { st.sucio = s; estado.textContent = s ? "Cambios sin guardar" : "Sin cambios"; estado.className = "chip " + (s ? "av" : ""); }
  async function cargar(ruta) {
    if (st.sucio && !(await confirmar("Tienes cambios sin guardar. ¿Descartarlos?", "Documento", true, "Descartar"))) return;
    st.ruta = ruta; hoja.replaceChildren(esqueleto(8));
    const ps = await intentar(() => llamar("documento_leer", ruta)); if (!ps) return;
    st.areas = ps.map((p) => {
      const t = h("textarea", { rows: 1, value: p.texto, style: { width: "100%", display: "block", fontWeight: p.negrita ? "700" : "400", textDecoration: p.subrayado ? "underline" : "none", textAlign: { centro: "center", derecha: "right", justificado: "justify" }[p.alineacion] || "left", fontSize: (p.tamano ? p.tamano * 1.25 : 14) + "px", color: p.color ? "#" + p.color : "#111", minHeight: p.texto ? "0" : "12px" } });
      t.addEventListener("input", () => { ajustar(t); marcar(true); }); return t;
    });
    hoja.replaceChildren(...st.areas); st.areas.forEach(ajustar); marcar(false);
    $$(".doc-item", lista).forEach((x) => x.classList.toggle("sel", x.dataset.r === ruta));
  }
  async function guardar() {
    if (!st.ruta) return toast("Elige un documento.", "info");
    const r = await intentar(() => llamar("documento_guardar", st.ruta, st.areas.map((t) => t.value))); if (r) { toast(r.mensaje); marcar(false); }
  }
  async function cargarLista(abrir) {
    const docs = await intentar(() => llamar("documentos_listar")) || [];
    lista.replaceChildren(...docs.map((d) => h("div", { class: "item click doc-item", "data-r": d.ruta, onclick: () => cargar(d.ruta) }, h("span", {}, "📄"), h("div", { class: "n" }, d.nombre, h("div", { class: "s" }, d.fecha)))));
    if (!docs.length) lista.append(h("div", { class: "vacio" }, "Aún no hay documentos. Crea una solicitud, constancia o carta desde Vacaciones o Amonestaciones."));
    if (abrir) await cargar(abrir); else if (st.ruta) $$(".doc-item", lista).forEach((x) => x.classList.toggle("sel", x.dataset.r === st.ruta));
  }
  const p = h("div", { class: "pagina" }, cabecera("Vista previa de documentos", "Revisa y corrige el texto antes de imprimir o enviar", estado, h("button", { class: "btn sec", onclick: () => st.ruta && intentar(() => llamar("documento_abrir", st.ruta)) }, "Abrir en Word"), guardarBtn),
    h("div", { class: "cuerpo" }, h("div", { class: "tarjeta", style: { width: "300px", flex: "none", display: "flex", flexDirection: "column" } }, h("div", { class: "franja" }), h("div", { class: "scroll int", style: { flex: 1 } }, lista)), h("div", { class: "scroll", style: { flex: 1, paddingBottom: "20px" } }, hoja)));
  p.refrescar = (op) => cargarLista(op && op.ruta);
  p.puedeSalir = async () => !st.sucio || (await confirmar("Tienes cambios sin guardar en el documento. ¿Salir sin guardar?", "Documento", true, "Salir sin guardar"));
  p.guardar = guardar;
  return p;
}

/* ======= Respaldos ======= */
async function paginaRespaldos(ctx) {
  const estado = h("div"), tbody = h("tbody");
  let datos = null, sel = null;
  const tam = (n) => { for (const u of ["B", "KB", "MB", "GB"]) { if (n < 1024 || u === "GB") return (u === "B" ? n : n.toFixed(1)) + " " + u; n /= 1024; } };
  const act = async (n, ...a) => { const r = await intentar(() => llamar(n, ...a)); if (r && r.mensaje) toast(r.mensaje, r.ok === false ? "error" : "ok"); await cargar(); return r; };
  async function restaurar(ruta) {
    if (!ruta) return toast("Selecciona una copia de la lista.", "info");
    if (!(await confirmar("Se reemplazarán TODOS los datos actuales (registros y archivos adjuntos) por los del respaldo.\nAntes se guarda una copia de seguridad de lo actual.\n\nLa aplicación se cerrará para cargar los datos. ¿Continuar?", "Restaurar respaldo", true, "Restaurar"))) return;
    const r = await intentar(() => llamar("respaldo_restaurar", ruta)); if (!r) return;
    await avisar(r.mensaje + "\nVuelve a abrir la aplicación.", "Restaurar"); intentar(() => llamar("cerrar"), true);
  }
  async function cargar() {
    const d = await intentar(() => llamar("respaldos_estado")); if (!d) return; datos = d;
    const reg = Object.entries(d.tablas).filter(([k]) => k !== "adjuntos").reduce((a, [, v]) => a + v, 0);
    estado.replaceChildren(h("div", { class: "estado-ok" + (d.ok ? "" : " mal") }, h("div", { class: "sello" }, d.ok ? "✓" : "!"),
      h("div", {}, h("h3", {}, d.ok ? "Base de datos en buen estado" : "Se detectaron problemas en la base de datos"),
        h("div", { class: "nota", style: { padding: 0 } }, d.ok ? `${reg} registros, ${d.adjuntos} archivos adjuntos (${tam(d.tamano + d.tamano_adjuntos)} en total). Revisión de integridad y de enlaces: correcta.` : d.error.slice(0, 400) + "  Restaura una copia de la lista."))),
      h("div", { class: "nota", style: { padding: "10px 0 0" } }, "Datos: " + d.carpeta), h("div", { class: "nota", style: { padding: "2px 0 0" } }, "Copia en otra carpeta: " + (d.externa || "no configurada (recomendado: OneDrive, USB o disco de red)")),
      h("div", { style: { display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px" } },
        h("button", { class: "btn sec", onclick: async () => { await cargar(); toast(datos.ok ? "Base de datos verificada: sin errores." : "Se encontraron errores.", datos.ok ? "ok" : "error"); } }, "Verificar base de datos"),
        h("button", { class: "btn sec", onclick: () => act("respaldo_externa", false) }, "Copia en otra carpeta…"), d.externa ? h("button", { class: "btn fan", onclick: () => act("respaldo_externa", true) }, "Dejar de copiar") : null,
        h("button", { class: "btn sec", onclick: () => intentar(() => llamar("abrir_carpeta_respaldos")) }, "Abrir carpeta de respaldos"),
        h("button", { class: "btn sec", onclick: () => act("respaldo_excel") }, "Exportar todo a Excel")));
    tbody.replaceChildren(...d.lista.map((r, i) => h("tr", { class: "fila-nueva" + (sel === r.ruta ? " sel" : ""), style: { animationDelay: Math.min(i, 12) * 12 + "ms" }, onclick: () => { sel = r.ruta; $$("tr", tbody).forEach((t) => t.classList.remove("sel")); event.currentTarget.classList.add("sel"); } }, h("td", {}, r.fecha), h("td", {}, h("span", { class: "chip " + (r.tipo === "Automático" ? "" : r.tipo === "Manual" ? "ok" : "av") }, r.tipo)), h("td", {}, tam(r.tamano)), h("td", {}, r.nombre))));
    if (!d.lista.length) tbody.append(h("tr", {}, h("td", { colSpan: 4, class: "vacio" }, "Todavía no hay copias. Pulsa «Crear respaldo ahora».")));
  }
  const p = h("div", { class: "pagina" }, cabecera("Respaldos", "Verifica la base de datos y guarda copias de todos tus datos", h("button", { class: "btn pri", onclick: () => act("respaldo_crear") }, "Crear respaldo ahora")),
    h("div", { class: "scroll", style: { flex: 1, paddingRight: "6px" } },
      h("div", { class: "tarjeta", style: { marginBottom: "16px" } }, h("div", { class: "franja" }), h("div", { class: "int" }, estado)),
      h("div", { class: "tarjeta c2" }, h("div", { class: "franja" }), h("div", { class: "tit" }, h("h3", {}, "Copias guardadas")), h("div", { class: "nota" }, "Se hace una automática al abrir y otra al cerrar la aplicación."),
        h("table", {}, h("thead", {}, h("tr", {}, ["Fecha", "Tipo", "Tamaño", "Archivo"].map((x) => h("th", {}, x)))), tbody),
        h("div", { class: "acciones" }, h("button", { class: "btn peligro", onclick: () => restaurar(sel) }, "Restaurar la seleccionada"), h("button", { class: "btn sec", onclick: async () => { const r = await intentar(() => llamar("respaldo_elegir_archivo")); if (r) restaurar(r); } }, "Restaurar desde archivo…"), h("button", { class: "btn sec", onclick: () => sel ? act("respaldo_guardar_como", sel) : toast("Selecciona una copia de la lista.", "info") }, "Guardar una copia como…")))));
  p.refrescar = cargar;
  return p;
}

/* ======= Configuración ======= */
async function paginaConfiguracion(ctx) {
  let cfg = null; const renombres = [];
  const cont = h("div", { class: "cfg" });
  const LISTAS = [["plazas", "Plazas disponibles", "Plazas en las que se reciben candidatos."], ["puestos", "Puestos de empleados", "Cargos que se asignan a los empleados."], ["departamentos", "Departamentos", "Departamentos de los empleados."],
    ["temas_memo", "Temas de memorándum", "Políticas que firman los empleados."], ["tipos_ausencia", "Tipos de ausencia", "Clases de ausencia que se pueden registrar."], ["etapas_ausencia", "Etapas de ausencias", "Recorrido de cada ausencia, en orden; la última se considera cerrada."], ["categorias_adjunto", "Tipos de archivo", "Clasificación de los archivos de candidatos (CV, Excel…)."]];
  function editorLista(clave, titulo, ayuda) {
    const caja = h("div", { class: "lista-chips" }), nuevo = h("input", { placeholder: "Agregar…", style: { maxWidth: "240px" } });
    const items = cfg[clave].map((n) => ({ orig: n, nombre: n }));
    const pinta = () => caja.replaceChildren(...items.map((it, i) => { const inp = h("input", { value: it.nombre, oninput: () => { it.nombre = inp.value; } }); return h("span", { class: "chip-edit" }, inp, h("button", { title: "Quitar", onclick: () => { items.splice(i, 1); pinta(); } }, "×")); }));
    const agregar = () => { const v = nuevo.value.trim(); if (v) { items.push({ orig: null, nombre: v }); nuevo.value = ""; pinta(); } };
    nuevo.addEventListener("keydown", (e) => { if (e.key === "Enter") agregar(); });
    pinta();
    const t = tarjeta(titulo, h("div", {}, caja, h("div", { style: { display: "flex", gap: "8px", marginTop: "8px" } }, nuevo, h("button", { class: "btn sec", onclick: agregar }, "Agregar")), h("div", { style: { marginTop: "12px" } }, h("button", { class: "btn pri", onclick: () => guardarLista(clave, items) }, "Guardar"))), { nota: ayuda });
    return t;
  }
  async function guardarLista(clave, items) {
    const lim = items.map((i) => ({ ...i, nombre: i.nombre.trim() })).filter((i) => i.nombre);
    const estado = { ...cfg, [clave]: lim.map((i) => i.nombre) };
    const ren = lim.filter((i) => i.orig && i.orig !== i.nombre).map((i) => ({ lista: clave, viejo: i.orig, nuevo: i.nombre }));
    const r = await intentar(() => llamar("config_guardar", estado, ren)); if (r) { cfg = r; toast("Configuración guardada."); ctx.listas = await llamar("listas"); ctx.refrescarListas(); }
  }
  function editorGrupos() {
    const caja = h("div"); const filas = Object.entries(cfg.grupos).map(([g, a]) => ({ orig: g, nombre: g, autor: a.join(", ") }));
    const pinta = () => caja.replaceChildren(...filas.map((f, i) => h("div", { class: "rejilla", style: { marginBottom: "10px", gridTemplateColumns: "1fr 1fr auto", alignItems: "end" } }, h("label", { class: "campo" }, "Grupo", h("span", { class: "x" }, h("input", { value: f.nombre, oninput: (e) => { f.nombre = e.target.value; } }))), h("label", { class: "campo" }, "Autorizan (separados por coma)", h("span", { class: "x" }, h("input", { value: f.autor, oninput: (e) => { f.autor = e.target.value; } }))), h("button", { class: "btn peligro peq", onclick: () => { filas.splice(i, 1); pinta(); } }, "Quitar"))));
    pinta();
    return tarjeta("Grupos de autorización de vacaciones", h("div", {}, caja, h("div", { style: { display: "flex", gap: "8px" } }, h("button", { class: "btn sec", onclick: () => { filas.push({ orig: null, nombre: "", autor: "" }); pinta(); } }, "+ Grupo"), h("button", { class: "btn pri", onclick: async () => {
      const grupos = {}; filas.filter((f) => f.nombre.trim()).forEach((f) => { grupos[f.nombre.trim()] = f.autor.split(",").map((x) => x.trim()).filter(Boolean); });
      const ren = filas.filter((f) => f.orig && f.orig !== f.nombre.trim() && f.nombre.trim()).map((f) => ({ lista: "grupos", viejo: f.orig, nuevo: f.nombre.trim() }));
      const r = await intentar(() => llamar("config_guardar", { ...cfg, grupos }, ren)); if (r) { cfg = r; toast("Grupos guardados."); ctx.listas = await llamar("listas"); } } }, "Guardar"))), { color: "c3", nota: "Quién autoriza las vacaciones de cada grupo." });
  }
  function editorDatos() {
    const c = { empresa: h("input", { value: cfg.empresa }), area: h("input", { value: cfg.area }), ciudad: h("input", { value: cfg.ciudad }), dias: h("input", { value: cfg.dias_cumpleanos, inputMode: "numeric" }), escala: h("textarea", { value: cfg.escala }) };
    const campo = (t, x) => h("label", { class: "campo", style: { display: "block", marginBottom: "10px" } }, t, h("span", { class: "x" }, x));
    return tarjeta("Documentos y avisos", h("div", {}, campo("Nombre de la empresa (encabezado)", c.empresa), campo("Área o departamento (encabezado)", c.area), campo("Ciudad que aparece en la fecha de los documentos", c.ciudad), campo("Avisar cumpleaños con cuántos días de anticipación", c.dias), campo("Escala de calificación de la ficha (texto de ayuda)", c.escala),
      h("button", { class: "btn pri", onclick: async () => { const r = await intentar(() => llamar("config_guardar", { ...cfg, empresa: c.empresa.value, area: c.area.value, ciudad: c.ciudad.value, dias_cumpleanos: c.dias.value, escala: c.escala.value }, [])); if (r) { cfg = r; toast("Datos guardados."); } } }, "Guardar cambios")), { color: "c2", nota: "Aparecen en el encabezado de los documentos y en el Resumen." });
  }
  function editorFicha() {
    const secs = cfg.secciones.map((s) => ({ nombre: s.nombre, global: s.global || "", texto: s.criterios.map(([c, m]) => `${c} | ${m}`).join("\n") }));
    const caja = h("div"); const pinta = () => caja.replaceChildren(...secs.map((s, i) => h("div", { class: "ficha-sec", style: { padding: "10px 12px" } }, h("div", { style: { display: "flex", gap: "8px", marginBottom: "6px" } }, h("input", { value: s.nombre, oninput: (e) => { s.nombre = e.target.value; } }), h("button", { class: "btn peligro peq", onclick: () => { secs.splice(i, 1); pinta(); } }, "Quitar")), h("input", { value: s.global, placeholder: "Texto del puntaje global (opcional)", style: { marginBottom: "6px" }, oninput: (e) => { s.global = e.target.value; } }), h("textarea", { value: s.texto, placeholder: "Un criterio por línea: texto | máximo", style: { minHeight: "110px" }, oninput: (e) => { s.texto = e.target.value; } }))));
    pinta();
    return tarjeta("Ficha de evaluación (pruebas de habilidades)", h("div", {}, caja, h("div", { style: { display: "flex", gap: "8px" } }, h("button", { class: "btn sec", onclick: () => { secs.push({ nombre: "Nueva sección", global: "", texto: "Criterio | 5" }); pinta(); } }, "+ Sección"), h("button", { class: "btn pri", onclick: async () => {
      const secciones = []; for (const s of secs) { const criterios = s.texto.split("\n").map((l) => l.trim()).filter(Boolean).map((l) => { const i = l.lastIndexOf("|"); return i < 0 ? [l, 5] : [l.slice(0, i).trim(), parseFloat(l.slice(i + 1).replace(",", ".")) || 0]; }); secciones.push({ nombre: s.nombre, global: s.global || null, criterios }); }
      const r = await intentar(() => llamar("config_guardar", { ...cfg, secciones }, [])); if (r) { cfg = r; toast("Ficha guardada."); } } }, "Guardar"))), { color: "c3", nota: "Secciones y criterios con su calificación máxima. Las pruebas ya guardadas conservan sus notas." });
  }
  async function cargar() {
    cfg = await intentar(() => llamar("config_obtener")); if (!cfg) return;
    cont.replaceChildren(...LISTAS.map(([k, t, a]) => editorLista(k, t, a)), editorGrupos(), editorDatos(), editorFicha());
  }
  const p = h("div", { class: "pagina" }, cabecera("Configuración", "Listas, datos de documentos y criterios que puedes editar sin tocar el código", h("button", { class: "btn peligro", onclick: async () => { if (!(await confirmar("¿Volver a los valores originales de todas las listas y datos?\nLos registros ya guardados no se modifican.", "Restablecer", true, "Restablecer"))) return; const r = await intentar(() => llamar("config_restablecer")); if (r) { toast("Valores originales restablecidos."); await cargar(); ctx.listas = await llamar("listas"); ctx.refrescarListas(); } } }, "Restablecer valores originales")),
    h("div", { class: "scroll", style: { flex: 1, paddingRight: "6px" } }, cont));
  p.refrescar = cargar;
  return p;
}
