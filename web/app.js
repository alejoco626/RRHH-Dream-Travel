"use strict";
const ctx = { listas: null, modulos: [], paginas: {}, actual: null, ir: null, insignias: null, refrescarListas: null };
const ICONOS = { resumen: "▦", embudo: "⏷", pruebas: "✎", entrevistas: "☏", ranking: "★", no_aprobados: "⊘", empleados: "☺", amonestaciones: "⚠", vacaciones: "☀", memos: "✉", ausencias: "◔", documentos: "▤", pendientes: "◷", respaldos: "⛁", configuracion: "⚙" };

async function arrancar() {
  await esperarPuente();
  const ini = await intentar(() => llamar("inicio"));
  if (!ini) { $("#contenido").append(h("div", { class: "vacio" }, "No se pudo iniciar la aplicación.")); return; }
  if (ini.alerta_base) { await alertaBase(ini.alerta_base); return; }
  ctx.modulos = ini.modulos;
  ctx.listas = await llamar("listas");
  document.body.append(h("datalist", { id: "dl-candidatos" }));
  const modo = await intentar(() => llamar("modo"), true);
  aplicarModo(modo || "claro");
  construirNav(ini);
  ctx.refrescarListas = () => { $("#dl-candidatos").replaceChildren(...ctx.listas.candidatos.map((c) => h("option", { value: c }))); };
  ctx.refrescarListas();
  ctx.ir = ir; ctx.insignias = insignias;
  $("#btn-modo").onclick = async () => { const nuevo = document.body.classList.contains("oscuro") ? "claro" : "oscuro"; aplicarModo(nuevo); intentar(() => llamar("modo", nuevo), true); };
  $("#btn-act").onclick = () => buscarActualizacion(ini);
  document.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); const p = ctx.paginas[ctx.actual]; if (p && p.guardar) p.guardar(); } });
  await ir("resumen");
  insignias();
  intentar(() => llamar("listo"), true);
  if (ini.novedades) setTimeout(() => mostrarNovedades(ini.novedades), 500);
  if (ini.puede_actualizar) setTimeout(() => buscarActualizacion(ini, true), 2500);
}

async function alertaBase(a) {
  document.body.append(h("div", { class: "vacio" }, esqueleto(2)));
  const botones = [{ texto: "Cerrar la aplicación", valor: "cerrar" }, { texto: "Elegir un archivo…", valor: "archivo" }];
  if (a.hay_copias) botones.push({ texto: "Restaurar el último respaldo", tipo: "pri", valor: "ultimo" });
  for (;;) {
    const r = await modal("Base de datos dañada", `Se detectó un problema en la base de datos:\n${a.error}\n\nPuedes restaurar una copia. La base actual se conserva como copia de seguridad.`, botones, { fijo: true });
    let res;
    if (r === "ultimo") res = await intentar(() => llamar("respaldo_restaurar_ultimo"));
    else if (r === "archivo") { const f = await intentar(() => llamar("respaldo_elegir_archivo")); if (f) res = await intentar(() => llamar("respaldo_restaurar", f)); else continue; }
    else { await intentar(() => llamar("cerrar"), true); return; }
    if (res) { await avisar(res.mensaje + "\nVuelve a abrir la aplicación.", "Restaurar"); await intentar(() => llamar("cerrar"), true); return; }
  }
}

function aplicarModo(m) {
  document.body.classList.toggle("oscuro", m === "oscuro");
  $("#ico-modo").textContent = m === "oscuro" ? "☀" : "☾";
  $("#btn-modo span:last-child").textContent = m === "oscuro" ? "Modo claro" : "Modo oscuro";
}

function construirNav(ini) {
  const nav = $("#nav"); let grupo = null;
  ctx.modulos.forEach((m) => {
    if (m.grupo && m.grupo !== grupo) { grupo = m.grupo; nav.append(h("div", { class: "grupo" }, grupo)); }
    nav.append(h("button", { class: "nav-item", "data-k": m.clave, onclick: () => ir(m.clave) }, h("span", { class: "ico" }, ICONOS[m.clave] || "•"), h("span", {}, m.titulo), h("span", { class: "insignia", id: "ins-" + m.clave, style: { display: "none" } })));
  });
  $("#txt-act").textContent = "Buscar actualizaciones · v" + ini.version;
}

async function crearPagina(m) {
  switch (m.tipo) {
    case "resumen": return paginaResumen(ctx);
    case "ranking": return paginaRanking(ctx);
    case "documentos": return paginaDocumentos(ctx);
    case "pendientes": return paginaPendientes(ctx);
    case "respaldos": return paginaRespaldos(ctx);
    case "configuracion": return paginaConfiguracion(ctx);
    default: return paginaCrud(m, ctx);
  }
}

let navegando = false;
async function ir(clave, opciones = {}) {
  if (navegando) return;
  navegando = true;
  try {
    const previa = ctx.paginas[ctx.actual];
    if (previa && ctx.actual !== clave && previa.puedeSalir && !(await previa.puedeSalir())) return;
    const m = ctx.modulos.find((x) => x.clave === clave);
    if (!m) return;
    if (!ctx.paginas[clave]) ctx.paginas[clave] = await crearPagina(m);
    const pagina = ctx.paginas[clave];
    if (ctx.actual !== clave) { $("#contenido").replaceChildren(pagina); pagina.style.animation = "none"; void pagina.offsetWidth; pagina.style.animation = ""; }
    ctx.actual = clave;
    $$(".nav-item[data-k]").forEach((b) => b.classList.toggle("activo", b.dataset.k === clave));
    ctx.listas = await llamar("listas"); ctx.refrescarListas();
    await pagina.refrescar(opciones);
    if (opciones.id && pagina.abrirRegistro) await pagina.abrirRegistro(opciones.id);
    if (opciones.valores && pagina.nuevoCon) await pagina.nuevoCon(opciones.valores, opciones.heredar);
  } finally { navegando = false; }
}

async function insignias() {
  const r = await intentar(() => llamar("insignias"), true); if (!r) return;
  const poner = (k, n) => { const e = $("#ins-" + k); if (e) { e.textContent = n; e.style.display = n ? "" : "none"; } };
  poner("resumen", r.atrasados); poner("pendientes", r.pendientes);
}

function mostrarNovedades(n) {
  const cont = h("div", { class: "novedades" });
  n.secciones.forEach((sec) => {
    cont.append(h("h3", {}, sec.titulo));
    cont.append(h("ul", {}, sec.elementos.map((t) => h("li", {}, h("span", { class: "vineta" }, sec.vineta), h("span", {}, t)))));
  });
  modal("¡Actualización v" + n.version + "!", cont, [{ texto: "Entendido", tipo: "pri", valor: true }]);
}

async function buscarActualizacion(ini, silencio) {
  const r = await intentar(() => llamar("buscar_actualizacion", !silencio), silencio);
  if (r === undefined) return;
  if (!r) { if (!silencio) toast("Ya tienes la última versión (v" + ini.version + ").", "info"); return; }
  if (!ini.puede_actualizar) { await avisar(`Hay una versión nueva (${r.version}).\nTu versión es la ${r.actual}.\n\nDescarga el instalador desde GitHub: la actualización automática solo funciona en la versión instalada.`, "Actualización disponible"); return; }
  if (await confirmar(`Hay una versión nueva (${r.version}).\nTu versión es la ${r.actual}.\n\n¿Quieres actualizar ahora?`, "Actualización disponible", false, "Actualizar")) descargarActualizacion(r);
}

function descargarActualizacion(info) {
  const relleno = h("div", { class: "relleno" });
  const pct = h("div", { class: "porcentaje" }, "0 %");
  const cont = h("div", {}, h("div", { class: "progreso" }, relleno), pct);
  modal("Descargando la versión " + info.version + "…", cont, [], { fijo: true });
  const velo = () => { const v = document.querySelectorAll("#modales .velo"); return v[v.length - 1]; };
  const fallo = async (mensaje) => { const v = velo(); if (v) v.cerrar(); await avisar(mensaje, "Actualización"); };
  async function seguir(e) {
    if (!e || e.estado === "error") { fallo((e && e.mensaje) || "No se pudo descargar la actualización."); return; }
    const avance = Math.round((e.progreso || 0) * 100);
    relleno.style.width = avance + "%"; pct.textContent = avance + " %";
    if (e.estado === "listo") {
      pct.textContent = "Instalando…";
      const r = await intentar(() => llamar("instalar_actualizacion"), true);
      if (!r || !r.ok) fallo((r && r.mensaje) || "No se pudo instalar la actualización.");
      return;
    }
    setTimeout(async () => seguir(await intentar(() => llamar("estado_descarga"), true)), 300);
  }
  intentar(() => llamar("descargar_actualizacion"), true).then(seguir);
}

arrancar();
