import os
import re
import sys

import docx
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

import base_datos as bd
import logica


def _carpeta_plantillas():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "plantillas")


CARPETA_DOCUMENTOS = os.path.join(bd.CARPETA_DATOS, "documentos")


def _nombre_seguro(texto):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_")


def _abrir_plantilla(nombre):
    return docx.Document(os.path.join(_carpeta_plantillas(), nombre))


def _borrar(parrafos):
    for p in parrafos:
        p._element.getparent().remove(p._element)


def _con_sangria_original(original, nuevo):
    espacios = original[: len(original) - len(original.lstrip(" "))]
    return f"{espacios}{nuevo} "


def _folio_en(parrafo, folio):
    parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = parrafo.runs[0]
    run.text = f"Folio No. {folio}"
    run.bold = True
    run.underline = False
    run.font.name = "Century Gothic"
    run.font.size = Pt(12)
    for extra in parrafo.runs[1:]:
        extra.text = ""


AZUL = "003D6B"
CORINTO = "960018"
EMPRESA = "DREAM TRAVEL, S.A."
AREA = "Recursos humanos"
CIUDAD = "Guatemala"


def _sombrear(celda, color):
    propiedades = celda._tc.get_or_add_tcPr()
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), color)
    propiedades.append(sombra)


def _formato_tabla(tabla, sangria_twips):
    propiedades = tabla._tbl.tblPr
    marca = propiedades.find(qn("w:tblLook"))
    sangria = OxmlElement("w:tblInd")
    sangria.set(qn("w:w"), str(-sangria_twips))
    sangria.set(qn("w:type"), "dxa")
    bordes = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{lado}")
        if lado == "bottom":
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "24")
            b.set(qn("w:color"), CORINTO)
        else:
            b.set(qn("w:val"), "nil")
        bordes.append(b)
    esquema = OxmlElement("w:tblLayout")
    esquema.set(qn("w:type"), "fixed")
    for elemento in (sangria, bordes, esquema):
        if marca is not None:
            marca.addprevious(elemento)
        else:
            propiedades.append(elemento)


def _encabezado_oficial(documento, fuente):
    seccion = documento.sections[0]
    seccion.header_distance = 0
    encabezado = seccion.header
    encabezado.is_linked_to_previous = False
    ancho_total = int(seccion.page_width / 635)
    ancho_logo = 3000
    tabla = encabezado.add_table(1, 2, seccion.page_width)
    tabla.autofit = False
    _formato_tabla(tabla, int(seccion.left_margin / 635))
    tabla._tbl.tblGrid.findall(qn("w:gridCol"))[0].set(qn("w:w"), str(ancho_logo))
    tabla._tbl.tblGrid.findall(qn("w:gridCol"))[1].set(qn("w:w"), str(ancho_total - ancho_logo))
    izquierda, derecha = tabla.rows[0].cells
    izquierda.width = docx.shared.Twips(ancho_logo)
    derecha.width = docx.shared.Twips(ancho_total - ancho_logo)
    for celda in (izquierda, derecha):
        _sombrear(celda, AZUL)
        celda.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    p_logo = izquierda.paragraphs[0]
    p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_logo.paragraph_format.space_before = Pt(6)
    p_logo.paragraph_format.space_after = Pt(6)
    p_logo.add_run().add_picture(os.path.join(_carpeta_plantillas(), "logo_blanco.png"),
                                 height=Inches(0.8))

    p_empresa = derecha.paragraphs[0]
    p_empresa.paragraph_format.left_indent = Inches(0.35)
    run = p_empresa.add_run(EMPRESA)
    run.bold, run.font.size, run.font.name = True, Pt(18), fuente
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    p_area = derecha.add_paragraph()
    p_area.paragraph_format.left_indent = Inches(0.35)
    run = p_area.add_run(AREA.upper())
    run.font.size, run.font.name = Pt(10), fuente
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    vacio = encabezado.paragraphs[0]
    tabla._tbl.addnext(vacio._p)
    vacio.paragraph_format.space_before = Pt(0)
    vacio.paragraph_format.space_after = Pt(0)
    vacio.paragraph_format.line_spacing = Pt(1)


def _titulo(parrafo, texto, fuente):
    for r in list(parrafo.runs):
        r._r.getparent().remove(r._r)
    run = parrafo.add_run(texto)
    run.bold, run.underline = True, False
    run.font.size, run.font.name = Pt(18), fuente
    run.font.color.rgb = RGBColor(0x00, 0x3D, 0x6B)
    parrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    parrafo.paragraph_format.space_before = Pt(18)
    parrafo.paragraph_format.space_after = Pt(14)
    borde = OxmlElement("w:pBdr")
    inferior = OxmlElement("w:bottom")
    inferior.set(qn("w:val"), "single")
    inferior.set(qn("w:sz"), "12")
    inferior.set(qn("w:space"), "6")
    inferior.set(qn("w:color"), CORINTO)
    borde.append(inferior)
    parrafo._p.get_or_add_pPr().insert_element_before(
        borde, "w:shd", "w:tabs", "w:suppressAutoHyphens", "w:kinsoku", "w:wordWrap",
        "w:overflowPunct", "w:topLinePunct", "w:autoSpaceDE", "w:autoSpaceDN", "w:bidi",
        "w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
        "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
        "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId", "w:cnfStyle",
        "w:rPr", "w:sectPr", "w:pPrChange")


def _guardar(documento, subcarpeta_nombre):
    os.makedirs(CARPETA_DOCUMENTOS, exist_ok=True)
    ruta = os.path.join(CARPETA_DOCUMENTOS, subcarpeta_nombre)
    documento.save(ruta)
    return ruta


def _datos_vacaciones(vacacion):
    empleado = bd.obtener("empleados", vacacion["empleado_id"])
    if empleado is None:
        raise ValueError("No se encontró el empleado de este registro.")
    periodo = (f"{logica.fecha_larga(vacacion['periodo_desde'])} al "
               f"{logica.fecha_larga(vacacion['periodo_hasta'])}")
    return empleado, periodo


def generar_solicitud_vacaciones(vacacion):
    empleado, periodo = _datos_vacaciones(vacacion)
    d = _abrir_plantilla("plantilla_vacaciones.docx")
    p = d.paragraphs

    _encabezado_oficial(d, "Century Gothic")
    if vacacion.get("folio"):
        _folio_en(p[2], vacacion["folio"])
    _titulo(p[4], "SOLICITUD DE VACACIONES", "Century Gothic")
    _borrar([p[0], p[1], p[3]])

    p[8].runs[0].text = f"{CIUDAD}, {logica.fecha_cabecera(vacacion['fecha_solicitud'])} "

    cantidad = logica.texto_cantidad_dias(vacacion["dias"])
    if vacacion["fecha_inicio"] == vacacion["fecha_fin"]:
        cuando = f"a gozarse en la fecha {logica.fecha_cabecera(vacacion['fecha_inicio'])}"
    else:
        cuando = (f"a gozarse del {logica.fecha_cabecera(vacacion['fecha_inicio'])} "
                  f"al {logica.fecha_cabecera(vacacion['fecha_fin'])},")
    p[17].runs[0].text = (
        f"Atentamente solicito que se me conceda {cantidad} de vacaciones, {cuando} "
        f"el cual corresponde al año laborado correspondiente al periodo vencido "
        f"comprendido entre el ")
    p[17].runs[1].text = f"{periodo} "

    p[23].runs[0].text = _con_sangria_original(
        p[23].runs[0].text, empleado["nombre_completo"].upper())
    if vacacion.get("autoriza"):
        p[33].runs[0].text = f"{vacacion['autoriza'].upper()} "

    _borrar(p[38:])
    nombre = f"Solicitud_vacaciones_{vacacion.get('folio') or vacacion['id']}_" \
             f"{_nombre_seguro(empleado['nombre_completo'])}.docx"
    return _guardar(d, nombre)


def generar_constancia_vacaciones(vacacion):
    empleado, periodo = _datos_vacaciones(vacacion)
    d = _abrir_plantilla("plantilla_vacaciones.docx")
    p = d.paragraphs

    fecha_constancia = vacacion.get("fecha_constancia")
    if not fecha_constancia:
        from datetime import timedelta
        fecha_constancia = (logica.parsear_fecha(vacacion["fecha_fin"])
                            + timedelta(days=1)).isoformat()

    _encabezado_oficial(d, "Century Gothic")
    if vacacion.get("folio"):
        _folio_en(p[40], vacacion["folio"])
    _titulo(p[42], "CONSTANCIA DE GOCE DE VACACIONES", "Century Gothic")
    _borrar([p[38], p[39], p[41], p[43]])

    p[46].runs[0].text = f"{CIUDAD}, {logica.fecha_cabecera(fecha_constancia)} "

    cantidad = logica.texto_cantidad_dias(vacacion["dias"])
    if vacacion["fecha_inicio"] == vacacion["fecha_fin"]:
        gozado = f"El día {logica.fecha_larga(vacacion['fecha_inicio'])} he gozado"
    else:
        gozado = (f"Del {logica.fecha_larga(vacacion['fecha_inicio'])} al "
                  f"{logica.fecha_larga(vacacion['fecha_fin'])} he gozado")
    cuerpo = p[55].runs
    cuerpo[2].text = (f"\n{gozado} {cantidad} de mis vacaciones correspondientes "
                      f"al periodo comprendido ")
    cuerpo[3].text = f"{periodo}. "
    cuerpo[4].text = ""

    p[65].runs[0].text = _con_sangria_original(
        p[65].runs[0].text, empleado["nombre_completo"].upper())

    _borrar(p[:38])
    nombre = f"Constancia_goce_vacaciones_{vacacion.get('folio') or vacacion['id']}_" \
             f"{_nombre_seguro(empleado['nombre_completo'])}.docx"
    return _guardar(d, nombre)


def generar_amonestacion(amonestacion):
    empleado = bd.obtener("empleados", amonestacion["empleado_id"])
    if empleado is None:
        raise ValueError("No se encontró el empleado de este registro.")
    d = _abrir_plantilla("plantilla_amonestacion.docx")
    p = d.paragraphs

    _encabezado_oficial(d, "Arial")
    _titulo(p[0], "AMONESTACIÓN ESCRITA", "Arial")
    p[1].runs[0].text = f"{CIUDAD}, {logica.fecha_amonestacion(amonestacion['fecha'])} "
    p[1].runs[1].text = ""

    p[3].runs[0].text = "Estimado(a)"
    p[3].runs[2].text = empleado["nombre_completo"]

    veces = int(amonestacion["numero_vez"])
    cuerpo = p[6].runs
    cuerpo[2].text = f" por {logica.ordinal_vez(veces)} vez"
    cuerpo[3].text = f" ({veces})"
    cuerpo[5].text = "Dicha falta consiste: "
    cuerpo[6].text = amonestacion["falta"]

    p[8].runs[0].text = f"{amonestacion.get('detalle') or ''} "

    aspecto = amonestacion.get("aspecto") or amonestacion["falta"]
    p[12].runs[2].text = aspecto

    p[20].runs[0].text = amonestacion.get("firmante") or ""
    p[20].runs[1].text = ""
    p[21].runs[0].text = amonestacion.get("cargo_firmante") or ""
    p[21].runs[1].text = ""
    p[21].runs[2].text = ""

    p[27].runs[2].text = f"\n{empleado['nombre_completo']}"
    p[27].runs[3].text = f"\n{empleado['puesto']}"

    _borrar([p[5], p[18], p[26]])
    for parrafo in d.paragraphs:
        if parrafo.text.startswith("A lo que el trabajador"):
            parrafo.alignment = WD_ALIGN_PARAGRAPH.LEFT

    nombre = f"Amonestacion_{amonestacion['id']}_" \
             f"{_nombre_seguro(empleado['nombre_completo'])}.docx"
    return _guardar(d, nombre)


def listar_documentos():
    if not os.path.isdir(CARPETA_DOCUMENTOS):
        return []
    salida = []
    for nombre in os.listdir(CARPETA_DOCUMENTOS):
        if nombre.lower().endswith(".docx") and not nombre.startswith("~$"):
            ruta = os.path.join(CARPETA_DOCUMENTOS, nombre)
            salida.append((ruta, os.path.getmtime(ruta)))
    return sorted(salida, key=lambda x: x[1], reverse=True)


def leer_para_editar(ruta):
    d = docx.Document(ruta)
    parrafos = []
    for p in d.paragraphs:
        corrida = next((r for r in p.runs if r.text.strip()), None)
        color = None
        if corrida is not None and corrida.font.color is not None \
                and corrida.font.color.rgb is not None:
            color = str(corrida.font.color.rgb)
        alineacion = {1: "centro", 2: "derecha", 3: "justificado"}.get(
            int(p.alignment) if p.alignment is not None else 0)
        parrafos.append({
            "texto": p.text,
            "negrita": bool(corrida is not None and corrida.bold),
            "subrayado": bool(corrida is not None and corrida.underline),
            "tamano": corrida.font.size.pt if corrida is not None and corrida.font.size else None,
            "color": color,
            "alineacion": alineacion,
        })
    return parrafos


def _poner_texto(parrafo, texto):
    corridas = [r for r in parrafo.runs if not r._r.xpath(".//w:drawing")]
    if not corridas:
        parrafo.add_run(texto)
        return
    corridas[0].text = texto
    for extra in corridas[1:]:
        extra.text = ""


def guardar_edicion(ruta, textos):
    d = docx.Document(ruta)
    for parrafo, texto in zip(d.paragraphs, textos):
        if texto != parrafo.text:
            _poner_texto(parrafo, texto)
    d.save(ruta)
