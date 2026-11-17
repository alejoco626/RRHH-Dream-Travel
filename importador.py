import csv
import io
import json
import os
import unicodedata
from datetime import date, timedelta

import base_datos as bd
import logica

OBLIGATORIOS = ("candidato", "fecha")

SINONIMOS = {
    "candidato": ["candidato", "nombre", "nombre completo", "nombre del candidato",
                  "aspirante", "persona"],
    "puesto": ["puesto", "cargo", "plaza", "vacante"],
    "fecha": ["fecha", "fecha de la prueba", "fecha prueba", "fecha de aplicacion"],
    "tipo_prueba": ["tipo de prueba", "tipo prueba", "tipo", "prueba"],
    "puntaje": ["puntaje", "nota", "calificacion", "punteo", "resultado", "score"],
    "observaciones": ["observaciones", "observacion", "comentarios", "comentario", "notas"],
}

EJEMPLOS = [
    {"candidato": "Nombre y apellido", "puesto": "Puesto", "fecha": "16/11/2026",
     "tipo_prueba": "Prueba de habilidades", "puntaje": "85", "observaciones": "Comentario opcional"},
    {"candidato": "Otro nombre y apellido", "puesto": "Puesto", "fecha": "17/11/2026",
     "tipo_prueba": "Pruebas psicométricas", "puntaje": "90", "observaciones": ""},
]
ENCABEZADOS_PLANTILLA = ["Candidato", "Puesto", "Fecha", "Tipo de prueba", "Puntaje",
                         "Observaciones"]


def _norm(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace("_", " ").replace("-", " ").split())


_ALIAS = {_norm(a): campo for campo, lista in SINONIMOS.items() for a in lista + [campo]}


def leer_filas(ruta):
    extension = os.path.splitext(ruta)[1].lower()
    if extension == ".json":
        return _leer_json(ruta)
    if extension in (".xlsx", ".xlsm"):
        return _leer_excel(ruta)
    if extension == ".csv":
        return _leer_csv(ruta)
    raise ValueError("Formato no admitido. Usa un archivo .xlsx, .json o .csv.")


def _leer_json(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        try:
            datos = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"El JSON no es válido: {e}") from e
    if isinstance(datos, dict):
        lista = None
        for clave in ("pruebas", "datos", "data", "registros"):
            if isinstance(datos.get(clave), list):
                lista = datos[clave]
                break
        if lista is None:
            lista = next((v for v in datos.values() if isinstance(v, list)), None)
        if lista is None:
            raise ValueError("No encontré una lista de pruebas dentro del JSON.")
        datos = lista
    if not isinstance(datos, list):
        raise ValueError("El JSON debe ser una lista de pruebas.")
    return [(i, item if isinstance(item, dict) else None)
            for i, item in enumerate(datos, start=1)]


def _leer_excel(ruta):
    try:
        import openpyxl
    except ImportError as e:
        raise ValueError("Para leer Excel falta instalar openpyxl:  pip install openpyxl") from e
    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"No se pudo abrir el Excel: {e}") from e
    filas, encabezados = [], None
    try:
        for numero, fila in enumerate(libro.worksheets[0].iter_rows(values_only=True), start=1):
            if all(c is None or str(c).strip() == "" for c in fila):
                continue
            if encabezados is None:
                encabezados = ["" if c is None else str(c) for c in fila]
                continue
            filas.append((numero, {h: v for h, v in zip(encabezados, fila) if h}))
    finally:
        libro.close()
    return filas


def _leer_csv(ruta):
    texto = None
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, encoding=codificacion, newline="") as f:
                texto = f.read()
            break
        except UnicodeDecodeError:
            continue
    try:
        dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=",;\t")
    except csv.Error:
        dialecto = csv.excel
    lector = csv.DictReader(io.StringIO(texto), dialect=dialecto)
    return [(i, dict(f)) for i, f in enumerate(lector, start=2)
            if any(str(v or "").strip() for v in f.values())]


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return str(valor).strip()


def _fecha(valor):
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and 20000 < valor < 80000:
        return (date(1899, 12, 30) + timedelta(days=int(valor))).isoformat()
    return logica.a_iso(valor)


def _normalizar(d):
    candidato = _texto(d.get("candidato"))
    if not candidato:
        raise ValueError("Falta el candidato.")
    bruto = d.get("fecha")
    if _texto(bruto) == "":
        raise ValueError("Falta la fecha.")
    fecha = _fecha(bruto)
    if not fecha:
        raise ValueError(f"Fecha no válida: «{_texto(bruto)}». Usa dd/mm/aaaa.")
    return {
        "candidato": candidato,
        "puesto": _texto(d.get("puesto")) or None,
        "fecha": fecha,
        "tipo_prueba": _texto(d.get("tipo_prueba")) or None,
        "puntaje": _texto(d.get("puntaje")) or None,
        "observaciones": _texto(d.get("observaciones")) or None,
    }


def validar(filas):
    if not filas:
        raise ValueError("El archivo no tiene filas con datos.")
    encabezados = dict.fromkeys(h for _, f in filas if f for h in f)
    mapa = {h: _ALIAS[_norm(h)] for h in encabezados if _norm(h) in _ALIAS}
    faltan = [c for c in OBLIGATORIOS if c not in mapa.values()]
    if faltan:
        raise ValueError(
            "Faltan columnas obligatorias: " + ", ".join(faltan) + ".\n"
            "Encabezados reconocidos: candidato (o nombre), puesto (o cargo), fecha, "
            "tipo de prueba, puntaje (o nota), observaciones.")
    validas, errores = [], []
    for numero, fila in filas:
        if fila is None:
            errores.append((numero, "La fila no es un registro (se esperaba un objeto)."))
            continue
        datos = {}
        for h, valor in fila.items():
            campo = mapa.get(h)
            if campo and _texto(datos.get(campo)) == "":
                datos[campo] = valor
        try:
            validas.append(_normalizar(datos))
        except ValueError as e:
            errores.append((numero, str(e)))
    return validas, errores


def cargar_archivo(ruta):
    return validar(leer_filas(ruta))


def _clave(d):
    return ((d.get("candidato") or "").strip().lower(), d.get("fecha"),
            (d.get("tipo_prueba") or "").strip().lower())


def separar_repetidas(validas):
    vistos = {_clave(f) for f in bd.listar("pruebas")}
    nuevas, repetidas = [], []
    for d in validas:
        clave = _clave(d)
        if clave in vistos:
            repetidas.append(d)
        else:
            vistos.add(clave)
            nuevas.append(d)
    return nuevas, repetidas


def guardar_pruebas(nuevas):
    return bd.insertar_varios("pruebas", nuevas)


def crear_plantilla(ruta):
    extension = os.path.splitext(ruta)[1].lower()
    if extension == ".json":
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"pruebas": EJEMPLOS}, f, ensure_ascii=False, indent=2)
        return
    if extension != ".xlsx":
        raise ValueError("La plantilla puede ser .xlsx o .json.")
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError as e:
        raise ValueError("Para crear la plantilla de Excel falta openpyxl:  "
                         "pip install openpyxl") from e
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Pruebas"
    hoja.append(ENCABEZADOS_PLANTILLA)
    for ejemplo in EJEMPLOS:
        dia, mes, anio = (int(x) for x in ejemplo["fecha"].split("/"))
        hoja.append([ejemplo["candidato"], ejemplo["puesto"], date(anio, mes, dia),
                     ejemplo["tipo_prueba"], ejemplo["puntaje"], ejemplo["observaciones"]])
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="003D6B")
        celda.alignment = Alignment(vertical="center")
    for columna, ancho in zip("ABCDEF", (28, 22, 14, 18, 10, 36)):
        hoja.column_dimensions[columna].width = ancho
    for fila in hoja.iter_rows(min_row=2, min_col=3, max_col=3):
        fila[0].number_format = "DD/MM/YYYY"
    hoja.freeze_panes = "A2"
    ayuda = libro.create_sheet("Instrucciones")
    for linea in ("Columnas obligatorias: Candidato y Fecha.",
                  "Fecha en formato dd/mm/aaaa (o una fecha de Excel).",
                  "Borra las filas de ejemplo antes de importar.",
                  "Las pruebas que ya existan (mismo candidato, fecha y tipo) se omiten."):
        ayuda.append([linea])
    ayuda.column_dimensions["A"].width = 80
    libro.save(ruta)
