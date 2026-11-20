"use strict";
/* ======= formulario genérico a partir del esquema ======= */
function crearForm(mod, ctx) {
  const entradas = {}, archivos = {};
  let adjuntos = [];
  let guia = "fecha_fin";
  const raiz = h("div", { class: "rejilla" });
  const L = ctx.listas;
  const opcionesDe = (c) => (L.campos[mod.clave] || L.campos[mod.tabla] || {})[c.clave] || c.opciones || [];

  function rellenarSelect(sel, lista, valor) {
    const v = valor ?? sel.value;
    sel.replaceChildren(h("option", { value: "" }, ""), ...lista.map((o) => h("option", { value: o }, o)));
    if (v && !lista.includes(v)) sel.append(h("option", { value: v }, v));
    sel.value = v || "";
  }
  function rellenarEmpleados(sel, valor) {
    const v = valor ?? sel.value;
    sel.replaceChildren(h("option", { value: "" }, "— elige —"), ...L.empleados.map((e) => h("option", { value: String(e.id) }, e.nombre)));
    sel.value = v || "";
  }
  function pintarAdjuntos(caja) {
    caja.replaceChildren(...adjuntos.map((a, i) => h("div", { class: "adj" },
      h("span", { class: "n", title: a.nombre }, "📎 " + a.nombre),
      h("select", { onchange: (e) => { a.categoria = e.target.value; } }, L.categorias.map((c) => h("option", { value: c, selected: c === a.categoria }, c))),
      h("button", { class: "btn sec peq", type: "button", onclick: () => intentar(() => llamar("abrir_archivo", a.archivo, a.origen)) }, "Ver"),
      h("button", { class: "btn peligro peq", type: "button", onclick: () => { adjuntos.splice(i, 1); pintarAdjuntos(caja); } }, "Quitar"))));
    if (!adjuntos.length) caja.append(h("div", { class: "nota", style: { padding: 0 } }, "Sin archivos"));
  }

  mod.campos.forEach((c) => {
    let ent, extra;
    const ancho = c.completo || c.tipo === "largo" || c.tipo === "archivo" || c.tipo === "adjuntos";
    if (c.tipo === "largo") ent = h("textarea", {});
    else if (c.tipo === "empleado") { ent = h("select", {}); rellenarEmpleados(ent); }
    else if (c.tipo === "opcion" && c.clave === "candidato") ent = h("input", { list: "dl-candidatos", autocomplete: "off" });
    else if (c.tipo === "opcion") { ent = h("select", {}); rellenarSelect(ent, opcionesDe(c)); }
    else if (c.tipo === "fecha") { ent = h("input", {}); mascaraFecha(ent); }
    else if (c.tipo === "archivo") {
      archivos[c.clave] = { actual: "", origen: null, nombre: "" };
      const etiqueta = h("span", { class: "n" }, "Sin archivo");
      const pinta = () => { const a = archivos[c.clave]; etiqueta.textContent = a.nombre || "Sin archivo"; etiqueta.parentNode.style.opacity = a.nombre ? 1 : .7; };
      extra = h("div", { class: "adj" }, etiqueta,
        h("button", { class: "btn sec peq", type: "button", onclick: async () => { const r = await intentar(() => llamar("elegir_archivos", !!c.pdf, false)); if (r && r.length) { Object.assign(archivos[c.clave], { origen: r[0].ruta, nombre: r[0].nombre }); pinta(); } } }, "Elegir…"),
        h("button", { class: "btn sec peq", type: "button", onclick: () => { const a = archivos[c.clave]; if (a.nombre) intentar(() => llamar("abrir_archivo", a.actual || null, a.origen)); } }, "Ver"),
        h("button", { class: "btn peligro peq", type: "button", onclick: () => { Object.assign(archivos[c.clave], { actual: "", origen: null, nombre: "" }); pinta(); } }, "Quitar"));
      extra.pinta = pinta;
    } else if (c.tipo === "adjuntos") {
      const caja = h("div", {}); extra = h("div", {}, caja, h("button", { class: "btn sec peq", type: "button", style: { marginTop: "8px" }, onclick: async () => {
        const r = await intentar(() => llamar("elegir_archivos", false, true));
        (r || []).forEach((f) => adjuntos.push({ id: null, archivo: null, origen: f.ruta, nombre: f.nombre, categoria: L.categorias[L.categorias.length - 1] || "Otro" }));
        pintarAdjuntos(caja);
      } }, "+ Agregar archivos"));
      extra.caja = caja; extra.pinta = () => pintarAdjuntos(caja);
      pintarAdjuntos(caja);
    } else ent = h("input", { autocomplete: "off" });
    if (ent) entradas[c.clave] = ent;
    const cuerpo = ent || extra;
    raiz.append(h("label", { class: "campo" + (ancho ? " completo" : ""), "data-k": c.clave }, h("span", { class: c.req ? "req" : "" }, c.etiqueta), h("span", { class: "x" }, cuerpo)));
    if (extra) archivos["__" + c.clave] = extra;
  });

  /* comportamientos propios de cada módulo */
  const pon = (k, v) => { if (entradas[k]) entradas[k].value = v; };
  const val = (k) => (entradas[k] ? entradas[k].value : "");
  if (mod.tabla === "vacaciones") {
    const goce = debounce(async (origen) => {
      if (origen === "fecha_inicio") origen = guia; else guia = origen;
      const r = await intentar(() => llamar("calcular_goce", origen, { fecha_inicio: val("fecha_inicio"), dias: val("dias"), fecha_fin: val("fecha_fin"), fecha_regreso: val("fecha_regreso") }), true);
      if (r) Object.entries(r).forEach(([k, v]) => pon(k, v));
    }, 260);
    ["fecha_inicio", "dias", "fecha_fin", "fecha_regreso"].forEach((k) => entradas[k].addEventListener("input", () => goce(k)));
    entradas.empleado_id.addEventListener("change", async () => {
      const id = val("empleado_id"); if (!id) return;
      const aut = await intentar(() => llamar("autorizadores", id), true);
      if (aut) { rellenarSelect(entradas.autoriza, aut, aut[0] || ""); }
      const p = await intentar(() => llamar("sugerir_periodo", id, val("fecha_inicio"), val("fecha_solicitud"), false), true);
      if (p) Object.entries(p).forEach(([k, v]) => pon(k, v));
    });
    entradas.fecha_inicio.addEventListener("change", async () => {
      const p = await intentar(() => llamar("sugerir_periodo", val("empleado_id"), val("fecha_inicio"), val("fecha_solicitud"), false), true);
      if (p && !val("periodo_desde")) Object.entries(p).forEach(([k, v]) => pon(k, v));
    });
  }
  if (entradas.candidato && entradas.telefono) {
    entradas.candidato.addEventListener("change", async () => {
      if (val("telefono")) return;
      const t = await intentar(() => llamar("candidato_telefono", val("candidato")), true);
      if (t) pon("telefono", t);
    });
  }

  function poner(valores, adj) {
    mod.campos.forEach((c) => {
      const v = valores[c.clave];
      if (c.tipo === "archivo") { Object.assign(archivos[c.clave], v || { actual: "", origen: null, nombre: "" }); archivos["__" + c.clave].pinta(); }
      else if (c.tipo === "adjuntos") return;
      else if (entradas[c.clave].tagName === "SELECT" && c.tipo === "opcion") rellenarSelect(entradas[c.clave], opcionesDe(c), v ?? "");
      else entradas[c.clave].value = v ?? "";
    });
    if (adj !== undefined && adj !== null) { adjuntos = adj.map((a) => ({ ...a })); const e = archivos["__adjuntos"]; if (e) e.pinta(); }
    guia = "fecha_fin";
  }
  function leer() {
    const v = {};
    mod.campos.forEach((c) => { if (c.tipo === "archivo") v[c.clave] = { ...archivos[c.clave] }; else if (c.tipo !== "adjuntos") v[c.clave] = entradas[c.clave].value; });
    return { valores: v, adjuntos: mod.campos.some((c) => c.tipo === "adjuntos") ? adjuntos.map((a) => ({ ...a })) : null };
  }
  function refrescarListas() {
    mod.campos.forEach((c) => {
      if (c.tipo === "empleado") rellenarEmpleados(entradas[c.clave]);
      else if (c.tipo === "opcion" && entradas[c.clave].tagName === "SELECT") rellenarSelect(entradas[c.clave], opcionesDe(c));
    });
  }
  enterSiguiente(raiz);
  return { el: raiz, poner, leer, refrescarListas, entradas };
}

/* ======= página CRUD ======= */
async function paginaCrud(mod, ctx, opciones = {}) {
  const sinForm = mod.formulario === false;
  const st = { id: null, busca: "", persona: null, etapa: null, filas: [] };
  const form = sinForm ? null : crearForm(mod, ctx);
  const titulo = h("h3", {}, "Nuevo registro");
  const tbody = h("tbody"), total = h("span", { class: "total" });
  const buscador = h("input", { placeholder: "Buscar…", oninput: debounce(() => { st.busca = buscador.value; cargarLista(); }, 200) });
  const franja = mod.tabla === "ausencias" ? h("div", { class: "franja-etapas" }) : null;
  const personaSel = mod.persona ? h("select", { style: { width: "220px" }, onchange: () => { st.persona = personaSel.value ? Number(personaSel.value) : null; informeBtn.style.display = st.persona ? "" : "none"; cargarLista(); } }) : null;
  const informeBtn = h("button", { class: "btn sec", style: { display: "none" }, onclick: () => abrirInforme(mod, st.persona) }, "Ver informes");

  const btn = (a, ejecutar, peq) => h("button", { class: (peq ? "peq " : "") + "btn " + (a.tipo === "pri" ? "pri" : a.tipo === "peligro" ? "peligro" : a.tipo === "fan" ? "fan" : "sec"), onclick: () => ejecutar(a) }, a.texto);
  const NECESITA_ID = ["marcar_recibido", "reactivar", "descartar", "descartar_registro", "abrir_prueba", "pasar_entrevista", "eliminar", "avanzar_ausencia"];
  const GUARDAR_ANTES = ["mover_etapa", "registrar_resultado", "crear_solicitud", "crear_constancia", "crear_carta", "avanzar_ausencia"];

  async function cargarLista(seleccionar) {
    const r = await intentar(() => llamar("listar", mod.clave, st.busca, st.persona, st.etapa));
    if (!r) return;
    st.filas = r.filas;
    tbody.replaceChildren(...r.filas.map((f, i) => {
      const tr = h("tr", { class: "fila-nueva" + (f.atrasado ? " atrasado" : "") + (f.id === st.id ? " sel" : ""), style: { animationDelay: Math.min(i, 12) * 12 + "ms" }, "data-id": f.id, onclick: () => abrir(f.id) },
        f.celdas.map((c, k) => h("td", { title: c }, celda(mod.columnas[k].clave, c))));
      return tr;
    }));
    if (!r.filas.length) tbody.append(h("tr", {}, h("td", { colSpan: mod.columnas.length, class: "vacio" }, "No hay registros que mostrar.")));
    total.textContent = r.por_etapa ? `${r.total} en el embudo · ` + Object.entries(r.por_etapa).map(([e, n]) => `${n} ${e.replace("Prueba de ", "").replace("Pruebas ", "").toLowerCase()}`).join(" · ")
      : `${r.total} registro${r.total !== 1 ? "s" : ""}` + (st.etapa ? ` · filtrado: ${st.etapa}` : "");
    if (franja && r.franja) pintarFranja(r.franja);
    if (seleccionar) abrir(seleccionar, true);
  }
  function celda(k, v) {
    if (!v) return (k === "adjuntos" || k.startsWith("archivo")) ? h("span", { class: "chip av" }, "Pendiente") : "";
    if (k === "adjuntos" || k.startsWith("archivo")) return h("span", { class: "chip ok" }, "✓ " + v);
    if (k === "situacion") return h("span", { class: "chip " + (v.startsWith("Atras") ? "mal" : v === "Hoy" ? "av" : v === "Asistió" || v === "Realizada" ? "ok" : "") }, v);
    if (k === "etapa" || k === "resultado") return h("span", { class: "chip" }, v);
    return v;
  }
  function pintarFranja(f) {
    const max = Math.max(1, f.total);
    franja.replaceChildren(...f.etapas.map(([e, n]) => h("div", { class: "etapa" + (st.etapa === e ? " sel" : ""), onclick: () => { st.etapa = st.etapa === e ? null : e; cargarLista(); } },
      h("b", {}, n), h("small", {}, e), h("div", { class: "bar", style: { width: (n / max * 100) + "%" } }))));
  }

  async function abrir(id, sinMarcar) {
    st.id = id;
    $$("tbody tr", tbody).forEach((tr) => tr.classList.toggle("sel", Number(tr.dataset.id) === id));
    if (sinForm) return;
    const r = await intentar(() => llamar("obtener", mod.clave, id));
    if (!r) return;
    titulo.textContent = "Editando registro";
    form.poner(r.valores, r.adjuntos);
  }
  async function nuevo(valores, heredar) {
    st.id = null;
    $$("tbody tr", tbody).forEach((tr) => tr.classList.remove("sel"));
    if (sinForm) return;
    const r = await intentar(() => llamar("nuevo", mod.clave));
    if (!r) return;
    titulo.textContent = "Nuevo registro";
    form.poner({ ...r.valores, ...(valores || {}) }, heredar || r.adjuntos);
    const p = $("input,select,textarea", form.el); if (p) p.focus();
  }
  async function guardar(silencio) {
    const { valores, adjuntos } = form.leer();
    const r = await intentar(() => llamar("guardar", mod.clave, st.id, valores, adjuntos));
    if (!r) return null;
    st.id = r.id; titulo.textContent = "Editando registro";
    form.poner(r.valores, r.adjuntos);
    if (!silencio) toast("Guardado.");
    await cargarLista(); ctx.insignias();
    return r.id;
  }
  async function procesar(res) {
    if (!res) return;
    if (res.mensaje) toast(res.mensaje, "info");
    if (res.limpiar) { await nuevo(); await cargarLista(); }
    if (res.recargar) await cargarLista(res.recargar);
    if (res.documento) ctx.ir("documentos", { ruta: res.documento });
    if (res.navegar) await navegar(res.navegar);
    ctx.insignias();
  }
  async function navegar(n) {
    if (n.ficha) return abrirFicha(ctx, null, n.ficha, n.heredar, () => { ctx.ir("pruebas"); });
    if (n.psicometrica) return psicometrica(ctx, null, n.psicometrica, () => ctx.ir("pruebas"));
    ctx.ir(n.modulo, { id: n.id, valores: n.valores, heredar: n.heredar });
  }
  async function ejecutar(a) {
    const id = a.id;
    if (a.id === "nueva_habilidades") return abrirFicha(ctx, null, {}, [], () => cargarLista());
    if (a.id === "nueva_psicometrica") return psicometrica(ctx, null, {}, () => cargarLista());
    if (a.id === "plantilla") { const r = await intentar(() => llamar("plantilla_importacion")); if (r) toast(r.mensaje); return; }
    if (a.id === "importar") return importarPruebas(ctx, () => cargarLista());
    if (NECESITA_ID.includes(id) && st.id === null && !(GUARDAR_ANTES.includes(id) && !sinForm)) { toast("Selecciona primero un registro de la lista.", "info"); return; }
    if (GUARDAR_ANTES.includes(id)) { const g = await guardar(true); if (!g) return; }
    if (id === "abrir_prueba") {
      const fila = st.filas.find((f) => f.id === st.id);
      const tipo = fila ? fila.celdas[1] : "";
      return tipo === "Pruebas psicométricas" ? psicometrica(ctx, st.id, {}, () => cargarLista()) : abrirFicha(ctx, st.id, {}, null, () => cargarLista());
    }
    if (id === "eliminar") {
      if (!(await confirmar("¿Eliminar este registro?", "Eliminar", true, "Eliminar"))) return;
      const r = await intentar(() => llamar("eliminar", mod.clave, st.id)); if (!r) return;
      toast("Registro eliminado."); await nuevo(); await cargarLista(); ctx.insignias(); return;
    }
    let extra = {};
    if (["descartar", "descartar_registro"].includes(id)) {
      const m = await preguntar("Descartar candidato", "Motivo por el que no continúa (opcional).\nPasará a la sección No aprobados:", "", true);
      if (m === null) return; extra = { motivo: m };
    }
    await procesar(await intentar(() => llamar("accion", mod.clave, id, st.id, extra)));
  }

  const barraAcc = h("div", { class: "acciones" }, (mod.acciones || []).map((a) => btn(a, ejecutar)));
  const cab = h("div", { class: "cab" }, h("div", {}, h("h1", {}, mod.titulo), h("p", {}, mod.sub)),
    h("div", { class: "acc" }, personaSel, informeBtn, (mod.cabecera || []).map((a) => btn(a, ejecutar)), sinForm ? null : h("button", { class: "btn pri", onclick: () => { nuevo(); toast("Formulario nuevo: completa los datos y pulsa Guardar.", "info"); } }, "+ Nuevo")));
  const lista = h("div", { class: "tarjeta lista" }, h("div", { class: "franja" }),
    h("div", { class: "barra" }, buscador, total),
    h("div", { class: "scroll", style: { flex: 1 } }, h("table", {}, h("thead", {}, h("tr", {}, mod.columnas.map((c) => h("th", {}, c.titulo)))), tbody)),
    sinForm ? barraAcc : null);
  const panel = sinForm ? null : h("div", { class: "tarjeta form c2" }, h("div", { class: "franja" }),
    h("div", { class: "tit" }, titulo), h("div", { class: "scroll int", style: { flex: 1 } }, form.el),
    h("div", { class: "acciones" }, h("button", { class: "btn pri", onclick: () => guardar() }, "Guardar"), h("button", { class: "btn sec", onclick: () => nuevo() }, "Limpiar"),
      st.id === null ? null : null, h("button", { class: "btn peligro", onclick: () => ejecutar({ id: "eliminar" }) }, "Eliminar"), ...(mod.acciones || []).map((a) => btn(a, ejecutar, true))));
  const pagina = h("div", { class: "pagina" }, cab, franja, h("div", { class: "cuerpo" }, lista, panel));
  pagina.refrescar = async () => {
    ctx.listas = await llamar("listas"); if (form) { form.refrescarListas(); }
    if (personaSel) {
      const ps = await llamar("personas");
      const v = personaSel.value;
      personaSel.replaceChildren(h("option", { value: "" }, "Todas las personas"), ...ps.map((p) => h("option", { value: p.id }, p.nombre)));
      personaSel.value = ps.some((p) => String(p.id) === v) ? v : "";
      st.persona = personaSel.value ? Number(personaSel.value) : null; informeBtn.style.display = st.persona ? "" : "none";
    }
    await cargarLista();
    if (!sinForm && st.id === null) await nuevo();
  };
  pagina.guardar = () => (form ? guardar() : null);
  pagina.abrirRegistro = async (id) => { await cargarLista(); await abrir(id); const tr = $(`tr[data-id="${id}"]`, tbody); if (tr) tr.scrollIntoView({ block: "center" }); };
  pagina.nuevoCon = async (valores, heredar) => { await cargarLista(); await nuevo(valores, heredar); };
  pagina.cargarLista = cargarLista;
  return pagina;
}

/* ======= ficha de evaluación ======= */
async function abrirFicha(ctx, id, prefijo, heredar, alGuardar) {
  const f = await intentar(() => llamar("ficha", id, prefijo));
  if (!f) return;
  let adj = id ? f.adjuntos : (heredar || []).map((a) => ({ ...a }));
  const detalle = f.detalle;
  const v = { candidato: h("input", { value: f.candidato, list: "dl-candidatos" }), puesto: h("input", { value: f.puesto }), fecha: h("input", { value: f.fecha }), hecha: h("input", { value: f.fecha_prueba }),
    obs: h("textarea", { value: f.observaciones }), pend: h("textarea", { value: detalle.pendientes || "" }) };
  mascaraFecha(v.fecha); mascaraFecha(v.hecha);
  const prom = h("span", { class: "prom" }, "—");
  const cajas = [];
  const ent = (s, c) => { const i = h("input", { inputMode: "decimal", value: c.calificacion ?? "", placeholder: "/" + c.maximo, "data-max": c.maximo }); i.addEventListener("input", recalcular); return i; };
  const numero = (t) => { const n = parseFloat(String(t).replace(",", ".")); return String(t).trim() === "" || isNaN(n) ? null : n; };
  function recalcular() {
    const fr = [];
    detalle.secciones.forEach((sec, si) => {
      const c = cajas[si]; let puntos = 0, max = 0, hubo = false;
      c.crit.forEach((i, ci) => { const n = numero(i.value), mx = sec.criterios[ci].maximo; i.classList.toggle("mal", n !== null && (n < 0 || n > mx)); if (n !== null && n >= 0 && n <= mx) { puntos += n; max += mx; hubo = true; } });
      let txt = "—";
      if (hubo) { fr.push(puntos / max); txt = `${fmtNum(puntos)} / ${fmtNum(max)} · ${Math.round(puntos / max * 100)} %`; }
      else if (c.glob) { const g = numero(c.glob.value); c.glob.classList.toggle("mal", g !== null && (g < 0 || g > 10)); if (g !== null && g >= 0 && g <= 10) { fr.push(g / 10); txt = `${fmtNum(g)} / 10 · ${Math.round(g * 10)} %`; } }
      c.res.textContent = txt;
    });
    prom.textContent = fr.length ? (fr.reduce((a, b) => a + b, 0) / fr.length * 100).toFixed(1) + " %" : "—";
  }
  const secciones = detalle.secciones.map((sec) => {
    const c = { crit: [], glob: null, res: h("span", {}, "—") };
    if (sec.global !== undefined && sec.criterios) { /* el texto del global viene de la configuración */ }
    const filas = sec.criterios.map((cr) => { const i = ent(sec, cr); c.crit.push(i); return h("div", { class: "crit" }, h("span", {}, cr.criterio), i); });
    cajas.push(c);
    const g = f.globales && f.globales[sec.nombre];
    if (g) { c.glob = h("input", { inputMode: "decimal", value: sec.global ?? "", placeholder: "/10" }); c.glob.addEventListener("input", recalcular); filas.push(h("div", { class: "crit" }, h("span", { style: { color: "var(--sec)" } }, g), c.glob)); }
    return h("div", { class: "ficha-sec" }, h("h4", {}, h("span", {}, sec.nombre), c.res), filas);
  });
  const adjCaja = h("div");
  const pintaAdj = () => { adjCaja.replaceChildren(...adj.map((a, i) => h("div", { class: "adj" }, h("span", { class: "n" }, "📎 " + a.nombre), h("button", { class: "btn sec peq", onclick: () => intentar(() => llamar("abrir_archivo", a.archivo, a.origen)) }, "Ver"), h("button", { class: "btn peligro peq", onclick: () => { adj.splice(i, 1); pintaAdj(); } }, "Quitar")))); };
  pintaAdj();
  const cont = h("div", { style: { width: "min(860px,88vw)" } },
    h("div", { class: "nota", style: { padding: 0, marginBottom: "10px" } }, f.escala),
    h("div", { class: "rejilla", style: { marginBottom: "14px" } },
      h("label", { class: "campo completo" }, h("span", { class: "req" }, "Candidato"), h("span", { class: "x" }, v.candidato)),
      h("label", { class: "campo" }, "Puesto", h("span", { class: "x" }, v.puesto)), h("span", {}),
      h("label", { class: "campo" }, h("span", { class: "req" }, "Fecha de evaluación"), h("span", { class: "x" }, v.fecha)),
      h("label", { class: "campo" }, "Fecha en que hizo la prueba (vacía = agendada)", h("span", { class: "x" }, v.hecha))),
    secciones,
    h("div", { style: { display: "flex", alignItems: "baseline", gap: "12px", margin: "6px 0 14px" } }, h("b", {}, "Nota final (promedio):"), prom),
    h("div", { class: "rejilla" },
      h("label", { class: "campo" }, "Observaciones", h("span", { class: "x" }, v.obs)),
      h("label", { class: "campo" }, "Pendientes o aspectos a reforzar", h("span", { class: "x" }, v.pend))),
    h("div", { style: { marginTop: "12px" } }, h("b", {}, "CV y archivos"), adjCaja,
      h("button", { class: "btn sec peq", style: { marginTop: "8px" }, onclick: async () => { const r = await intentar(() => llamar("elegir_archivos", false, true)); (r || []).forEach((x) => adj.push({ id: null, archivo: null, origen: x.ruta, nombre: x.nombre, categoria: "CV" })); pintaAdj(); } }, "+ Agregar archivos")));
  const allInputs = () => [v.candidato, v.puesto, v.fecha, v.hecha, ...cajas.flatMap((c) => [...c.crit, c.glob].filter(Boolean)), v.obs];
  cont.addEventListener("keydown", (e) => { if (e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); const l = allInputs(), i = l.indexOf(e.target); if (i >= 0 && l[i + 1]) l[i + 1].focus(); } });
  recalcular();
  const recoger = () => ({ id, candidato: v.candidato.value, puesto: v.puesto.value, fecha: v.fecha.value, fecha_prueba: v.hecha.value, observaciones: v.obs.value, adjuntos: adj,
    detalle: { pendientes: v.pend.value, secciones: detalle.secciones.map((sec, si) => ({ nombre: sec.nombre, global: cajas[si].glob ? cajas[si].glob.value : null, criterios: sec.criterios.map((cr, ci) => ({ criterio: cr.criterio, calificacion: cajas[si].crit[ci].value })) })) } });
  await modal(id ? "Ficha de evaluación" : "Nueva prueba de habilidades", cont, [{ texto: "Cancelar", valor: false }, { texto: "Guardar", tipo: "pri", valor: true, antes: async () => {
    const forzar = [];
    for (;;) {
      const r = await intentar(() => llamar("ficha_guardar", recoger(), forzar));
      if (!r) return false;
      if (r.pregunta) { if (!(await confirmar(r.pregunta, "Confirmar"))) return false; forzar.push(r.clave); continue; }
      toast("Prueba guardada."); ctx.insignias(); if (alGuardar) alGuardar(r.guardado); return true;
    }
  } }], { fijo: true });
}

async function psicometrica(ctx, id, prefijo, alGuardar) {
  let datos = { candidato: prefijo.candidato || "", puntaje: "", fecha: prefijo.fecha || null };
  if (id) datos = await intentar(() => llamar("psicometrica", id)) || datos;
  const c = h("input", { value: datos.candidato, list: "dl-candidatos" }), p = h("input", { value: datos.puntaje, placeholder: "ej. 78 o 78 %" });
  const r = await modal("Pruebas psicométricas", h("div", { class: "rejilla", style: { gridTemplateColumns: "1fr" } },
    h("label", { class: "campo" }, "Candidato", h("span", { class: "x" }, c)), h("label", { class: "campo" }, "Puntaje o resultado", h("span", { class: "x" }, p))),
    [{ texto: "Cancelar", valor: false }, { texto: "Guardar", tipo: "pri", valor: true, antes: async () => {
      const x = await intentar(() => llamar("guardar_psicometrica", c.value, p.value, id, datos.fecha)); if (!x) return false; toast(x.mensaje); return true; } }]);
  if (r) { ctx.insignias(); if (alGuardar) alGuardar(); }
}

async function importarPruebas(ctx, alTerminar) {
  const r = await intentar(() => llamar("importar_previa"));
  if (!r) return;
  const cuerpo = h("div", { style: { width: "min(820px,88vw)" } },
    h("p", {}, h("b", {}, r.archivo), ` · ${r.nuevas.length} nuevas · ${r.repetidas} ya existentes (se omiten) · ${r.errores.length} con errores`),
    r.errores.length ? h("div", { class: "nota", style: { padding: 0, color: "var(--mal)", marginBottom: "8px" } }, r.errores.slice(0, 8).map(([n, e]) => h("div", {}, `Fila ${n}: ${e}`))) : null,
    h("div", { class: "scroll", style: { maxHeight: "40vh" } }, h("table", {}, h("thead", {}, h("tr", {}, ["Candidato", "Puesto", "Fecha", "Tipo", "Nota"].map((t) => h("th", {}, t)))),
      h("tbody", {}, r.nuevas.slice(0, 200).map((d) => h("tr", {}, [d.candidato, d.puesto, d.fecha, d.tipo, d.puntaje].map((x) => h("td", {}, x))))))));
  const ok = await modal("Importar pruebas", cuerpo, [{ texto: "Cancelar", valor: false }, { texto: `Importar ${r.nuevas.length}`, tipo: "pri", valor: true }]);
  if (ok && r.nuevas.length) { const g = await intentar(() => llamar("importar_confirmar")); if (g) { toast(g.mensaje); ctx.insignias(); alTerminar(); } }
}

/* ======= informes por persona ======= */
async function abrirInforme(mod, personaInicial) {
  const personas = await llamar("personas");
  const sel = h("select", { style: { width: "220px" } }, h("option", { value: "" }, "Todas las personas"), personas.map((p) => h("option", { value: p.id, selected: p.id === personaInicial }, p.nombre)));
  const desde = h("input", { style: { width: "130px" } }), hasta = h("input", { style: { width: "130px" } });
  mascaraFecha(desde); mascaraFecha(hasta);
  const tabla = h("div", { class: "scroll", style: { maxHeight: "52vh", border: "1px solid var(--borde)", borderRadius: "10px" } });
  const sub = h("div", { class: "nota", style: { padding: "8px 0" } });
  const args = () => [mod.tabla, sel.value ? Number(sel.value) : null, desde.value, hasta.value];
  const actualizar = async () => {
    tabla.replaceChildren(esqueleto(4));
    const r = await intentar(() => llamar("informe", ...args()));
    if (!r) { tabla.replaceChildren(); return; }
    sub.textContent = r.subtitulo;
    tabla.replaceChildren(h("table", {}, h("thead", {}, h("tr", {}, r.columnas.map((c) => h("th", {}, c)))), h("tbody", {}, r.filas.map((f) => h("tr", {}, f.map((c) => h("td", { title: c }, c))))), r.filas.length ? null : h("tbody", {}, h("tr", {}, h("td", { colSpan: r.columnas.length, class: "vacio" }, "Sin registros con esos filtros")))));
  };
  [sel, desde, hasta].forEach((x) => x.addEventListener("change", actualizar));
  const acc = async (n, extra) => { const r = await intentar(() => llamar(n, ...args(), ...(extra || []))); if (r) toast(r.mensaje); };
  const cont = h("div", { style: { width: "min(980px,92vw)" } }, h("div", { style: { display: "flex", gap: "10px", alignItems: "flex-end", flexWrap: "wrap" } },
    h("label", { class: "campo" }, "Persona", h("span", { class: "x" }, sel)), h("label", { class: "campo" }, "Desde", h("span", { class: "x" }, desde)), h("label", { class: "campo" }, "Hasta", h("span", { class: "x" }, hasta))), sub, tabla);
  actualizar();
  await modal("Informes · " + mod.titulo, cont, [
    { texto: "Exportar a Excel", valor: null, antes: async () => { await acc("informe_excel"); return false; } },
    { texto: "Copiar imagen", valor: null, antes: async () => { await acc("informe_imagen", ["copiar"]); return false; } },
    { texto: "Guardar imagen", valor: null, antes: async () => { await acc("informe_imagen", ["guardar"]); return false; } },
    { texto: "Cerrar", tipo: "pri", valor: true }], { fijo: true });
}
