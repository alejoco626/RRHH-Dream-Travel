"use strict";
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

function h(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e && k !== "list" && k !== "type") e[k] = v;
    else e.setAttribute(k, v === true ? "" : v);
  }
  const poner = (c) => {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) c.forEach(poner);
    else e.append(c.nodeType ? c : document.createTextNode(String(c)));
  };
  kids.forEach(poner);
  return e;
}

let puente = null;
async function esperarPuente() {
  if (window.pywebview && window.pywebview.api) { puente = "py"; return; }
  await new Promise((ok) => {
    const t = setTimeout(ok, 2500);
    window.addEventListener("pywebviewready", () => { clearTimeout(t); ok(); }, { once: true });
  });
  puente = window.pywebview && window.pywebview.api ? "py" : "http";
}
async function llamar(nombre, ...args) {
  let r;
  if (puente === "py") r = await window.pywebview.api[nombre](...args);
  else r = await (await fetch("/api/" + nombre, { method: "POST", body: JSON.stringify(args) })).json();
  if (!r.ok) throw new Error(r.error);
  return r.datos;
}
async function intentar(f, silencio) {
  try { return await f(); }
  catch (e) { if (!silencio) toast(e.message || String(e), "error"); return undefined; }
}

function toast(texto, tipo = "ok") {
  const t = h("div", { class: "toast " + (tipo === "ok" ? "" : tipo) }, texto);
  $("#toasts").append(t);
  setTimeout(() => { t.style.transition = "opacity .25s, transform .25s"; t.style.opacity = 0; t.style.transform = "translateX(20px)"; setTimeout(() => t.remove(), 260); }, tipo === "error" ? 5200 : 2600);
}

function modal(titulo, contenido, botones, opciones = {}) {
  return new Promise((resolver) => {
    const cerrar = (v) => { velo.style.opacity = 0; velo.style.transition = "opacity .12s"; setTimeout(() => velo.remove(), 120); document.removeEventListener("keydown", tecla, true); resolver(v); };
    const tecla = (e) => { if (e.key === "Escape") { e.stopPropagation(); cerrar(undefined); } };
    const pie = h("footer", {}, botones.map((b) => h("button", { class: "btn " + (b.tipo || "sec"), onclick: async () => {
      if (b.antes && (await b.antes()) === false) return;
      cerrar(b.valor);
    } }, b.texto)));
    const m = h("div", { class: "modal", style: opciones.ancho ? { width: opciones.ancho } : {} },
      h("header", {}, titulo), h("div", { class: "mc" }, contenido), pie);
    const velo = h("div", { class: "velo", onmousedown: (e) => { if (e.target === velo && !opciones.fijo) cerrar(undefined); } }, m);
    $("#modales").append(velo);
    document.addEventListener("keydown", tecla, true);
    const primero = $("input,textarea,select", m) || $(".btn.pri", m);
    if (primero) setTimeout(() => primero.focus(), 30);
    velo.cerrar = cerrar;
  });
}
async function confirmar(texto, titulo = "Confirmar", peligro = false, si = "Aceptar") {
  return (await modal(titulo, texto, [{ texto: "Cancelar", valor: false }, { texto: si, tipo: peligro ? "peligro" : "pri", valor: true }])) === true;
}
async function avisar(texto, titulo = "Aviso") { await modal(titulo, texto, [{ texto: "Aceptar", tipo: "pri", valor: true }]); }
async function preguntar(titulo, etiqueta, inicial = "", largo = false) {
  const campo = largo ? h("textarea", { value: inicial }) : h("input", { value: inicial });
  if (!largo) campo.addEventListener("keydown", (e) => { if (e.key === "Enter") $(".modal .btn.pri").click(); });
  const r = await modal(titulo, h("div", {}, h("div", { style: { marginBottom: "8px" } }, etiqueta), campo),
    [{ texto: "Cancelar", valor: null }, { texto: "Aceptar", tipo: "pri", valor: true }]);
  return r === true ? campo.value : null;
}

function esqueleto(filas = 5) {
  return h("div", { style: { padding: "16px" } }, Array.from({ length: filas }, () => h("div", { class: "sk", style: { height: "16px", margin: "12px 0", width: (60 + Math.random() * 38) + "%" } })));
}

function mascaraFecha(inp) {
  inp.placeholder = "dd/mm/aaaa"; inp.inputMode = "numeric"; inp.maxLength = 10;
  inp.addEventListener("input", (e) => {
    if (e.inputType && e.inputType.startsWith("delete")) return;
    let d = inp.value.replace(/\D/g, "").slice(0, 8), s = d;
    if (d.length > 4) s = d.slice(0, 2) + "/" + d.slice(2, 4) + "/" + d.slice(4);
    else if (d.length > 2) s = d.slice(0, 2) + "/" + d.slice(2);
    inp.value = s;
  });
}
function debounce(f, ms = 220) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => f(...a), ms); }; }
function enterSiguiente(contenedor, final) {
  contenedor.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" || e.target.tagName === "TEXTAREA" || e.target.tagName === "BUTTON") return;
    const cs = $$("input:not([type=hidden]),select,textarea", contenedor).filter((x) => !x.disabled && x.offsetParent);
    const i = cs.indexOf(e.target);
    if (i >= 0) { e.preventDefault(); const n = cs[i + 1]; if (n) n.focus(); else if (final) final(); }
  });
}
const PALETA = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)"];
const fmtNum = (n) => (Math.round(n * 10) / 10).toLocaleString("es");

/* ---------- gráficas SVG ---------- */
function tip() { let t = $(".tip"); if (!t) { t = h("div", { class: "tip" }); document.body.append(t); } return t; }
function conTip(el, texto) {
  el.addEventListener("mousemove", (e) => { const t = tip(); t.textContent = texto; t.style.opacity = 1; t.style.left = e.clientX + 12 + "px"; t.style.top = e.clientY + 12 + "px"; });
  el.addEventListener("mouseleave", () => { tip().style.opacity = 0; });
}
const NS = "http://www.w3.org/2000/svg";
function s(tag, attrs, ...kids) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
  kids.forEach((c) => c && e.append(c.nodeType ? c : document.createTextNode(c)));
  return e;
}

function barrasH(datos, { color, formato = fmtNum, max } = {}) {
  const m = max || Math.max(1, ...datos.map((d) => d.valor || 0));
  const cont = h("div");
  datos.forEach((d, i) => {
    const rel = h("div", { class: "rel", style: { background: color || PALETA[i % PALETA.length] } });
    cont.append(h("div", { class: "barra-h" }, h("div", { class: "e", title: d.etiqueta }, d.etiqueta), h("div", { class: "pista" }, rel), h("div", { class: "v" }, formato(d.valor || 0))));
    requestAnimationFrame(() => requestAnimationFrame(() => { rel.style.width = ((d.valor || 0) / m * 100) + "%"; }));
  });
  if (!datos.length) cont.append(h("div", { class: "vacio" }, "Sin datos todavía"));
  return cont;
}

function columnas(datos, { series, alto = 190, formato = fmtNum } = {}) {
  // datos: [{etiqueta, valores:[...] }]; series: [{nombre,color}]
  const W = 640, H = alto, ml = 28, mb = 22, mt = 8;
  const total = (d) => d.valores.reduce((a, b) => a + b, 0);
  const m = Math.max(1, ...datos.map(total)); const mm = m <= 4 ? Math.ceil(m) : m;
  const paso = (W - ml) / Math.max(1, datos.length), ancho = Math.min(34, paso * 0.62);
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "grafica" });
  const niveles = mm <= 4 ? mm : 4;
  for (let i = 0; i <= niveles; i++) {
    const y = mt + (H - mt - mb) * (1 - i / niveles);
    svg.append(s("line", { x1: ml, x2: W, y1: y, y2: y, stroke: "var(--borde)", "stroke-width": 1 }), s("text", { x: ml - 6, y: y + 4, "text-anchor": "end" }, fmtNum(mm * i / niveles)));
  }
  datos.forEach((d, i) => {
    const x = ml + paso * i + (paso - ancho) / 2;
    let acum = 0;
    const g = s("g", {});
    d.valores.forEach((v, k) => {
      if (!v) return;
      const alt = (H - mt - mb) * v / mm, y = H - mb - acum - alt; acum += alt;
      const r = s("rect", { x, y, width: ancho, height: alt, rx: 4, fill: series[k].color, class: "col", style: `animation-delay:${i * 18}ms` });
      conTip(r, `${d.etiqueta} · ${series[k].nombre}: ${formato(v)}`);
      g.append(r);
    });
    svg.append(g, s("text", { x: x + ancho / 2, y: H - 6, "text-anchor": "middle" }, d.etiqueta));
  });
  const cont = h("div", {}, svg);
  if (series.length > 1) cont.append(h("div", { class: "leyenda" }, series.map((x) => h("span", {}, h("i", { style: { background: x.color } }), x.nombre))));
  return cont;
}

function dona(datos, { centro } = {}) {
  const total = datos.reduce((a, d) => a + d.valor, 0);
  const R = 62, r = 40, cx = 80, cy = 80;
  const svg = s("svg", { viewBox: "0 0 160 160", style: "width:160px;height:160px;flex:none" });
  if (!total) svg.append(s("circle", { cx, cy, r: (R + r) / 2, fill: "none", stroke: "var(--hover)", "stroke-width": R - r }));
  let a0 = -Math.PI / 2;
  datos.forEach((d, i) => {
    if (!d.valor) return;
    const a1 = a0 + (d.valor / total) * Math.PI * 2 - (datos.filter((x) => x.valor).length > 1 ? 0.03 : 0);
    const gran = a1 - a0 > Math.PI ? 1 : 0;
    const p = (rad, a) => `${cx + rad * Math.cos(a)} ${cy + rad * Math.sin(a)}`;
    const path = s("path", { d: `M ${p(R, a0)} A ${R} ${R} 0 ${gran} 1 ${p(R, a1)} L ${p(r, a1)} A ${r} ${r} 0 ${gran} 0 ${p(r, a0)} Z`, fill: PALETA[i % PALETA.length], style: "transform-origin:80px 80px;animation:apar .5s both;transition:transform .15s" });
    path.addEventListener("mouseenter", () => { path.style.transform = "scale(1.04)"; });
    path.addEventListener("mouseleave", () => { path.style.transform = ""; });
    conTip(path, `${d.etiqueta}: ${d.valor}`);
    svg.append(path); a0 = a1 + 0.03;
  });
  svg.append(s("text", { x: cx, y: cy + 2, "text-anchor": "middle", style: "font-size:24px;font-weight:700;fill:var(--texto)" }, centro ?? total), s("text", { x: cx, y: cy + 18, "text-anchor": "middle" }, "en total"));
  return h("div", { style: { display: "flex", alignItems: "center", gap: "18px", flexWrap: "wrap" } }, svg,
    h("div", { class: "leyenda", style: { flexDirection: "column", gap: "7px" } }, datos.map((d, i) => h("span", {}, h("i", { style: { background: PALETA[i % PALETA.length] } }), `${d.etiqueta} · `, h("b", {}, d.valor)))));
}

/* Evita que un null/undefined/false (o una lista) se pinte como texto: «null» */
(() => {
  const limpiar = (k) => k.flat(Infinity).filter((x) => x !== null && x !== undefined && x !== false);
  for (const nombre of ["replaceChildren", "append"]) {
    const original = Element.prototype[nombre];
    Element.prototype[nombre] = function (...k) { return original.apply(this, limpiar(k)); };
  }
})();
