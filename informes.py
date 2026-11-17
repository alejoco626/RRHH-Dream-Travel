import io
import os
import sys
from datetime import date

import base_datos as bd
import logica

AZUL = (0, 61, 107)
CORINTO = (150, 0, 24)
TODAS = "Todas las personas"


def _f(valor):
    return logica.formatear(valor) if valor else ""


def _si(valor, si, no):
    return si if valor else no


def _d(valor):
    return "" if valor is None else logica.texto_dias(valor)


ESPECIFICACIONES = {
    "vacaciones": {
        "titulo": "Informe de vacaciones", "fecha": "fecha_inicio",
        "columnas": [("Folio", lambda r: r.get("folio") or ""),
                     ("Empleado", lambda r: r.get("empleado") or ""),
                     ("Desde", lambda r: _f(r["fecha_inicio"])),
                     ("Hasta", lambda r: _f(r["fecha_fin"])),
                     ("Días", lambda r: _d(r["dias"])),
                     ("Periodo", lambda r: f"{_f(r['periodo_desde'])} – {_f(r['periodo_hasta'])}"),
                     ("Autoriza", lambda r: r.get("autoriza") or ""),
                     ("Solicitud", lambda r: _si(r.get("archivo_solicitud"), "Firmada", "Falta")),
                     ("Constancia", lambda r: _si(r.get("archivo_constancia"), "Firmada", "Falta"))],
    },
    "amonestaciones": {
        "titulo": "Informe de amonestaciones", "fecha": "fecha",
        "columnas": [("Empleado", lambda r: r.get("empleado") or ""),
                     ("Fecha", lambda r: _f(r["fecha"])),
                     ("Vez", lambda r: str(r.get("numero_vez") or "")),
                     ("Falta", lambda r: r.get("falta") or ""),
                     ("Aspecto", lambda r: r.get("aspecto") or ""),
                     ("Firmante", lambda r: r.get("firmante") or ""),
                     ("Comprobante", lambda r: _si(r.get("archivo"), "Firmada", "Falta"))],
    },
    "memos": {
        "titulo": "Informe de memorándums", "fecha": "fecha",
        "columnas": [("Empleado", lambda r: r.get("empleado") or ""),
                     ("Fecha", lambda r: _f(r["fecha"])),
                     ("Tema", lambda r: r.get("tema") or ""),
                     ("De", lambda r: r.get("emisor") or ""),
                     ("Comprobante", lambda r: _si(r.get("archivo"), "Firmado", "Falta"))],
    },
    "ausencias": {
        "titulo": "Informe de ausencias", "fecha": "fecha",
        "columnas": [("Empleado", lambda r: r.get("empleado") or ""),
                     ("Tipo", lambda r: r.get("tipo") or ""),
                     ("Desde", lambda r: _f(r["fecha"])),
                     ("Hasta", lambda r: _f(r.get("fecha_fin"))),
                     ("Días", lambda r: _d(r.get("dias"))),
                     ("Etapa", lambda r: r.get("etapa") or ""),
                     ("Cierre", lambda r: _f(r.get("fecha_cierre"))),
                     ("Justificante", lambda r: _si(r.get("archivo"), "Sí", "No"))],
    },
}

RESUMEN = (
    ("vacaciones", "Vacaciones", "fecha_inicio",
     lambda r: f"{_d(r['dias'])} días del {_f(r['fecha_inicio'])} al {_f(r['fecha_fin'])}"
               + (f" · folio {r['folio']}" if r.get("folio") else ""),
     lambda r: _si(r.get("archivo_constancia"), "Con constancia", "Sin constancia")),
    ("amonestaciones", "Amonestación", "fecha",
     lambda r: f"Vez {r.get('numero_vez') or 1}: {r.get('falta') or ''}",
     lambda r: _si(r.get("archivo"), "Firmada", "Sin firma")),
    ("memos", "Memorándum", "fecha", lambda r: r.get("tema") or "",
     lambda r: _si(r.get("archivo"), "Firmado", "Sin firma")),
    ("ausencias", "Ausencia", "fecha",
     lambda r: f"{r.get('tipo') or ''} · {_d(r.get('dias'))} día(s)",
     lambda r: r.get("etapa") or ""),
)

ESPECIFICACIONES["empleados"] = {
    "titulo": "Informe de personal", "fecha": "fecha", "columnas": [
        ("Tipo", lambda r: r["_tipo"]), ("Empleado", lambda r: r["empleado"]),
        ("Fecha", lambda r: _f(r["fecha"])), ("Detalle", lambda r: r["_detalle"]),
        ("Estado", lambda r: r["_estado"])]}


def _registros_combinados():
    filas = []
    for tabla, tipo, campo_fecha, detalle, estado in RESUMEN:
        for r in bd.listar(tabla):
            filas.append({"empleado_id": r["empleado_id"], "empleado": r.get("empleado") or "",
                          "fecha": r.get(campo_fecha) or "", "_tipo": tipo,
                          "_detalle": detalle(r), "_estado": estado(r)})
    return filas


def construir(tabla, persona_id=None, desde=None, hasta=None):
    espec = ESPECIFICACIONES[tabla]
    if tabla == "empleados":
        registros = _registros_combinados()
    else:
        registros = bd.listar(tabla)
        for r in registros:
            r["fecha"] = r.get(espec["fecha"]) or ""
    if persona_id is not None:
        registros = [r for r in registros if r.get("empleado_id") == persona_id]
    if desde:
        registros = [r for r in registros if r["fecha"] and r["fecha"] >= desde]
    if hasta:
        registros = [r for r in registros if r["fecha"] and r["fecha"] <= hasta]
    registros.sort(key=lambda r: (r["fecha"] or "", r.get("empleado") or ""), reverse=True)
    columnas = [c[0] for c in espec["columnas"]]
    filas = [[c[1](r) for c in espec["columnas"]] for r in registros]
    return espec["titulo"], columnas, filas


def subtitulo(persona, desde, hasta, total):
    partes = [persona or TODAS]
    if desde or hasta:
        partes.append(f"del {_f(desde) or 'inicio'} al {_f(hasta) or 'hoy'}")
    partes.append(f"{total} registro{'s' if total != 1 else ''}")
    return "  ·  ".join(partes)


def exportar_xlsx(ruta, titulo, columnas, filas):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo[:31]
    hoja.append(columnas)
    for fila in filas:
        hoja.append(fila)
    relleno = PatternFill("solid", start_color="003D6B")
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(vertical="center")
    for i, columna in enumerate(columnas, start=1):
        ancho = max([len(str(columna))] + [len(str(f[i - 1])) for f in filas]) + 3
        hoja.column_dimensions[hoja.cell(row=1, column=i).column_letter].width = min(ancho, 60)
    hoja.freeze_panes = "A2"
    libro.save(ruta)


_FUENTES = {
    "normal": ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    "negrita": ("C:/Windows/Fonts/segoeuib.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
}


def _fuente(estilo, tamano):
    from PIL import ImageFont
    for ruta in _FUENTES[estilo]:
        try:
            return ImageFont.truetype(ruta, tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def imagen_tabla(titulo, sub, columnas, filas, escala=2):
    from PIL import Image, ImageDraw
    e = escala
    letra, negrita = _fuente("normal", 14 * e), _fuente("negrita", 14 * e)
    grande, chica = _fuente("negrita", 22 * e), _fuente("normal", 12 * e)
    medidor = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def ancho(texto, fuente):
        return int(medidor.textlength(str(texto), font=fuente))

    margen, relleno = 24 * e, 12 * e
    anchos = [max([ancho(c, negrita)] + [ancho(f[i], letra) for f in filas] or [0]) + 2 * relleno
              for i, c in enumerate(columnas)]
    total = sum(anchos)
    alto_cab, alto_fila, alto_titulo = 38 * e, 32 * e, 76 * e
    ancho_img = max(total + 2 * margen, ancho(titulo, grande) + 2 * margen,
                    ancho(sub, chica) + 2 * margen)
    alto_img = alto_titulo + alto_cab + max(len(filas), 1) * alto_fila + 40 * e
    img = Image.new("RGB", (ancho_img, alto_img), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, ancho_img, 6 * e], fill=CORINTO)
    d.text((margen, 18 * e), titulo, font=grande, fill=AZUL)
    d.text((margen, 50 * e), sub, font=chica, fill=(100, 116, 139))
    y = alto_titulo
    d.rectangle([margen, y, margen + total, y + alto_cab], fill=AZUL)
    x = margen
    for c, a in zip(columnas, anchos):
        d.text((x + relleno, y + (alto_cab - 14 * e) // 2 - 2 * e), str(c), font=negrita,
               fill="white")
        x += a
    y += alto_cab
    if not filas:
        d.text((margen + relleno, y + 6 * e), "Sin registros para este filtro.", font=letra,
               fill=(100, 116, 139))
    for n, fila in enumerate(filas):
        if n % 2 == 0:
            d.rectangle([margen, y, margen + total, y + alto_fila], fill=(243, 246, 250))
        x = margen
        for valor, a in zip(fila, anchos):
            d.text((x + relleno, y + (alto_fila - 14 * e) // 2 - 2 * e), str(valor), font=letra,
                   fill=(15, 23, 42))
            x += a
        y += alto_fila
    d.line([margen, y, margen + total, y], fill=(203, 213, 225), width=e)
    d.text((margen, y + 10 * e),
           f"Generado el {date.today().strftime('%d/%m/%Y')}  ·  Dream & Travel · Recursos Humanos",
           font=chica, fill=(100, 116, 139))
    return img


def copiar_imagen(img):
    if sys.platform != "win32":
        raise OSError("Copiar al portapapeles solo está disponible en Windows.")
    import ctypes
    from ctypes import wintypes
    salida = io.BytesIO()
    img.convert("RGB").save(salida, "BMP")
    datos = salida.getvalue()[14:]
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    k.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    k.GlobalAlloc.restype = wintypes.HGLOBAL
    k.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k.GlobalLock.restype = wintypes.LPVOID
    k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    u.OpenClipboard.argtypes = [wintypes.HWND]
    u.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    u.SetClipboardData.restype = wintypes.HANDLE
    memoria = k.GlobalAlloc(0x0002, len(datos))
    if not memoria:
        raise OSError("No hay memoria para copiar la imagen.")
    puntero = k.GlobalLock(memoria)
    ctypes.memmove(puntero, datos, len(datos))
    k.GlobalUnlock(memoria)
    if not u.OpenClipboard(None):
        raise OSError("No se pudo abrir el portapapeles.")
    try:
        u.EmptyClipboard()
        if not u.SetClipboardData(8, memoria):
            raise OSError("No se pudo copiar la imagen.")
    finally:
        u.CloseClipboard()
