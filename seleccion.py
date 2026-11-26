"""Lógica del proceso de selección: la misma del libro «Planilla de candidatos», en Python.

- Normalización de lo que se escribe a mano (nombres, teléfonos, fechas, horas, asistencia).
- Resultado por prueba, promedio comparable, ranking, grupo A/B/C y lo que falta registrar.
- Clasificación automática del estado del candidato.
- Capacidad de pruebas y entrevistas por día.
Nada de esto toca la base de datos: se puede probar solo.
"""
import json
import re
import unicodedata
from datetime import date, datetime, time

import evaluacion as ev

# ---------------------------------------------------------------- listas del libro
ESTADOS = ["Nuevo", "En evaluación", "Entrevista", "Finalista", "Contratado", "Descartado",
           "Declinó"]
ACTIVOS = ["Nuevo", "En evaluación", "Entrevista", "Finalista"]
CERRADOS = ["Contratado", "Descartado", "Declinó"]
ASISTENCIAS = ["Sin contactar", "Enviar link", "Pendiente de confirmar", "Confirmada",
               "Reagendar", "No respondió", "De baja"]
RONDAS = ["Primera", "Segunda"]
FUENTES = ["WhatsApp", "Referido", "Bolsa de empleo", "Redes sociales", "Otro"]
PUESTOS = ["Diseñador/a de ventas", "Asistente al viajero", "Asistente de visa", "Otro"]
PRUEBAS = [("cv", "Revisión del CV"), ("ventas", "Evaluación de ventas"),
           ("llamada", "Llamada de venta"), ("simulacion", "Simulación de venta"),
           ("bitrix", "Prueba de Bitrix24"), ("excel", "Prueba de Excel")]
COMPARABLES = ["cv", "ventas", "simulacion"]
UMBRALES = {"a": 0.85, "b": 0.70}
GRUPOS = ["A: finalista", "B: con potencial", "C: por debajo", "Pendiente de evaluar"]

# capacidad (hoja de calendario): pruebas 3 por hora de 9 a 17 (sin 12 a 14); entrevistas 3 al día
CAPACIDAD = {"pruebas_por_hora": 3, "pruebas_por_dia": 21, "entrevistas_por_dia": 3,
             "pruebas_horario": "9:00 a. m. a 5:00 p. m. (sin atención de 12:00 a 2:00 p. m.)",
             "entrevistas_horario": "3:00 p. m. a 5:00 p. m."}

# cuántas veces se puede reagendar cada cosa antes de pedir confirmación (se edita en Configuración)
REAGENDAS = {"pruebas": 2, "entrevistas": 1}
# horas del día en que se agendan pruebas y entrevistas (3:00 se entiende como 15:00)
VENTANA_HORAS = [8, 18]

PARTICULAS = {"de", "del", "la", "las", "los", "y", "e"}
ERRATAS = {}  # correcciones fijas de nombres mal escritos: {"nombremalescrito": "Nombre correcto"}


# ---------------------------------------------------------------- normalización
def sin_acentos(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or ""))
                   if unicodedata.category(c) != "Mn")


def limpiar(t):
    return re.sub(r"\s+", " ", str(t or "").replace("\xa0", " ")).strip()


def nombre_normal(t):
    t = limpiar(t).replace(".", " ")
    t = limpiar(t)
    if not t:
        return ""
    palabras = []
    for i, p in enumerate(t.split(" ")):
        b = p.lower()
        b = ERRATAS.get(sin_acentos(b), b)
        for q in b.split(" "):
            palabras.append(q if (q in PARTICULAS and i > 0) else q[:1].upper() + q[1:])
    return " ".join(palabras)


def clave_nombre(t):
    return re.sub(r"[^a-z0-9]", "", sin_acentos(t).lower())


def telefono_normal(t):
    d = re.sub(r"\D", "", str(t or ""))
    if d.startswith("502") and len(d) == 11:
        d = d[3:]
    if len(d) == 8:
        return f"+502 {d[:4]} {d[4:]}"
    return limpiar(t)


def digitos_telefono(t):
    d = re.sub(r"\D", "", str(t or ""))
    return d[-8:] if len(d) >= 8 else ""


def correo_normal(t):
    return limpiar(t).lower().replace(" ", "")


def fecha_normal(v):
    """ISO aaaa-mm-dd o None. Arregla errores de escritura típicos (19/11/82026)."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    t = limpiar(v)
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?", t)
    if m:
        a, b, c = map(int, m.groups())
    else:
        m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{3,5})", t)
        if not m:
            return None
        c, b, a = map(int, m.groups())
        if a > 9999 or a < 1000:  # 82026 -> 2026
            a = int(str(a)[-4:]) if str(a)[-4:].startswith("20") else (2000 + a % 100)
    try:
        return date(a, b, c).isoformat()
    except ValueError:
        return None


def hora_normal(v, ventana=None):
    """'HH:MM' en 24 h o None. Las pruebas y entrevistas son de día: 3:00 se entiende 15:00."""
    ventana = ventana or VENTANA_HORAS
    if v is None or v == "":
        return None
    if isinstance(v, (datetime, time)):
        h, mi = v.hour, v.minute
        explicito = True
    else:
        t = limpiar(v).lower().replace("o", "0").replace(".", ":")
        t = re.sub(r"\s", "", t)
        m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(?::\d{2})?(a:?m:?|p:?m:?|am|pm)?", t.replace(":m", "m"))
        if not m:
            return None
        h, mi, suf = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "")
        explicito = bool(suf)
        if suf.startswith("p") and h < 12:
            h += 12
        elif suf.startswith("a") and h == 12:
            h = 0
    if h > 23 or mi > 59:
        return None
    if not explicito and h < ventana[0]:
        h += 12
    elif isinstance(v, (datetime, time)) and h < ventana[0]:
        h += 12
    return f"{h:02d}:{mi:02d}"


def asistencia_normal(v):
    t = sin_acentos(limpiar(v)).lower()
    if not t:
        return ASISTENCIAS[0]
    if t.startswith("conf"):
        return "Confirmada"
    if "baja" in t:
        return "De baja"
    if "enviar" in t or "link" in t:
        return "Enviar link"
    if "reagend" in t:
        return "Reagendar"
    if t.startswith("pend"):
        return "Pendiente de confirmar"
    if "respond" in t:
        return "No respondió"
    return ASISTENCIAS[0]


def estado_normal(v):
    t = sin_acentos(limpiar(v)).lower()
    for e in ESTADOS:
        if sin_acentos(e).lower() == t:
            return e
    return ""


def texto_oracion(v):
    t = limpiar(v)
    return (t[:1].upper() + t[1:].lower()) if t else ""


def clave_candidato(nombre, telefono="", correo=""):
    d = digitos_telefono(telefono)
    if d:
        return "tel:" + d
    if correo_normal(correo):
        return "mail:" + correo_normal(correo)
    return "nom:" + clave_nombre(nombre)


def motivos_coincidencia(a, b):
    """En qué coinciden dos candidatos: teléfono, correo y/o nombre (vacío = no coinciden)."""
    m = []
    ta, tb = digitos_telefono(a.get("telefono")), digitos_telefono(b.get("telefono"))
    if ta and ta == tb:
        m.append("teléfono")
    ca, cb = correo_normal(a.get("correo")), correo_normal(b.get("correo"))
    if ca and ca == cb:
        m.append("correo")
    na, nb = clave_nombre(a.get("nombre")), clave_nombre(b.get("nombre"))
    if na and na == nb:
        m.append("nombre")
    return m


def texto_duplicado(nombre_otro, motivos):
    return (f"Posible duplicado de «{nombre_otro}»: pueden ser la misma persona porque coinciden en "
            f"{', '.join(motivos)}. Revisa si es una sola.")


# ---------------------------------------------------------------- evaluación
def resumen_evaluacion(texto_o_detalle):
    """{'cv': 0..1|None, ..., 'hechas': n, 'disponible': prom, 'comparable': prom|None}."""
    det = texto_o_detalle if isinstance(texto_o_detalle, dict) else ev.desde_texto(texto_o_detalle)
    secciones = det["secciones"]
    r = {}
    for (clave, _), sec in zip(PRUEBAS, secciones):
        res = ev.resultado(sec)
        r[clave] = None if res is None else res[2]
    valores = [v for v in (r[c] for c, _ in PRUEBAS) if v is not None]
    r["hechas"] = len(valores)
    r["disponible"] = sum(valores) / len(valores) if valores else None
    comp = [r[c] for c in COMPARABLES]
    r["comparable"] = sum(comp) / 3 if all(c is not None for c in comp) else None
    return r


def grupo_de(comparable, umbral_a=None, umbral_b=None):
    ua = UMBRALES["a"] if umbral_a is None else umbral_a
    ub = UMBRALES["b"] if umbral_b is None else umbral_b
    if comparable is None:
        return GRUPOS[3]
    if comparable >= ua:
        return GRUPOS[0]
    if comparable >= ub:
        return GRUPOS[1]
    return GRUPOS[2]


def falta_registrar(r):
    faltan = [nombre for clave, nombre in PRUEBAS if r.get(clave) is None]
    return faltan


RECOMENDACION_AUTO = {GRUPOS[0]: "Avanzar a entrevista", GRUPOS[1]: "Con potencial: decidir tras "
                      "la entrevista", GRUPOS[2]: "No continúa por ahora",
                      GRUPOS[3]: "Completar las evaluaciones"}


def sugerencia_estado(estado, grupo, asistencia=""):
    """Siguiente paso recomendado según el resultado; None si no hay nada que sugerir."""
    if estado in CERRADOS:
        return None
    if estado in ("Nuevo", "En evaluación"):
        if grupo == GRUPOS[0]:
            return "Entrevista"
        if grupo == GRUPOS[2]:
            return "Descartado"
    if estado == "Nuevo" and grupo != GRUPOS[3]:
        return "En evaluación"
    return None


def matriz(candidatos, umbral_a=None, umbral_b=None):
    """Una fila por candidato con resultados, grupo, ranking y lo que falta. Ordenada por ranking."""
    filas = []
    for c in candidatos:
        r = resumen_evaluacion(c.get("evaluacion"))
        g = grupo_de(r["comparable"], umbral_a, umbral_b)
        filas.append({"id": c["id"], "nombre": c["nombre"], "puesto": c.get("puesto") or "",
                      "estado": c.get("estado") or "", "resultados": {k: r[k] for k, _ in PRUEBAS},
                      "hechas": r["hechas"], "disponible": r["disponible"],
                      "comparable": r["comparable"], "grupo": g,
                      "falta": falta_registrar(r),
                      "recomendacion": c.get("recomendacion") or RECOMENDACION_AUTO[g],
                      "lectura": c.get("lectura") or "",
                      "sugerencia": sugerencia_estado(c.get("estado"), g, c.get("asistencia"))})
    con = sorted([f for f in filas if f["comparable"] is not None],
                 key=lambda f: (-f["comparable"], f["nombre"].lower()))
    puesto = {}
    for i, f in enumerate(con):
        # empates comparten posición (igual que RANK de Excel)
        if i and abs(f["comparable"] - con[i - 1]["comparable"]) < 1e-12:
            f["ranking"] = con[i - 1]["ranking"]
        else:
            f["ranking"] = i + 1
        puesto[f["id"]] = f["ranking"]
    sin = sorted([f for f in filas if f["comparable"] is None],
                 key=lambda f: (-(f["disponible"] if f["disponible"] is not None else -1),
                                f["nombre"].lower()))
    for f in sin:
        f["ranking"] = None
    return con + sin


def resumen_proceso(candidatos, filas_matriz):
    """Totales del proceso (hoja Resumen del libro)."""
    def cuenta(clave, valores):
        return [{"etiqueta": v, "valor": sum(1 for c in candidatos if (c.get(clave) or "") == v)}
                for v in valores]
    otros_p = sorted({c.get("puesto") for c in candidatos if c.get("puesto")} - set(PUESTOS))
    otros_f = sorted({c.get("fuente") for c in candidatos if c.get("fuente")} - set(FUENTES))
    promedio = []
    for clave, nombre in PRUEBAS:
        v = [f["resultados"][clave] for f in filas_matriz if f["resultados"][clave] is not None]
        promedio.append({"etiqueta": nombre, "valor": (sum(v) / len(v) * 100) if v else None,
                         "n": len(v)})
    return {
        "total": len(candidatos),
        "con_seis": sum(1 for f in filas_matriz if f["hechas"] == len(PRUEBAS)),
        "con_ranking": sum(1 for f in filas_matriz if f["comparable"] is not None),
        "estados": cuenta("estado", ESTADOS), "puestos": cuenta("puesto", PUESTOS + otros_p),
        "fuentes": cuenta("fuente", FUENTES + otros_f),
        "asistencias": cuenta("asistencia", ASISTENCIAS),
        "grupos": [{"etiqueta": g, "valor": sum(1 for f in filas_matriz if f["grupo"] == g)}
                   for g in GRUPOS],
        "promedio_pruebas": promedio}


# ---------------------------------------------------------------- clasificación del estado
def _t(v):
    return sin_acentos(limpiar(v)).lower()


def clasificar_estado(c, hay_evaluacion=False, resultado_eval=None):
    """(estado, motivo). Aplica las reglas del proceso a lo que dicen los datos.

    Prioridad: 1) quedó contratado / en capacitación, 2) el equipo lo descartó,
    3) declinó o no responde, 4) conserva el estado escrito, 5) lo deduce de lo registrado.
    """
    obs = _t(c.get("observaciones")) + " " + _t(c.get("pendientes"))
    estado = estado_normal(c.get("estado"))
    asist = c.get("asistencia") or ""
    if "capacitacion" in obs or ("ya realizo la entrevista" in obs and estado == "Entrevista"):
        return "Contratado", "En capacitación: ya hizo la entrevista"
    if estado == "Contratado":
        return "Contratado", ""
    descartar = ("no prosigue", "se descarta", "descartad", "no veo que pueda",
                 "dificultades en las pruebas", "no pudo desarrollar")
    if any(p in obs for p in descartar) or str(c.get("fecha_entrevista_texto") or "").lower().replace(
            " ", "").startswith("noprosigue"):
        return "Descartado", "El equipo decidió que no continúa"
    if estado == "Descartado":
        return "Descartado", ""
    declinar = ("no respondi", "no se presento", "ya consiguio trabajo", "aplico a otro trabajo",
                "no se presento a entrevista", "ya consiguio")
    if any(p in obs for p in declinar) and not (asist == "Reagendar" and estado in ACTIVOS):
        return "Declinó", "No continúa por decisión propia o no respondió"
    if asist == "De baja" and estado not in ("Entrevista", "Finalista"):
        return "Declinó", "Se dio de baja"
    if asist == "De baja":
        return "Declinó", "Se dio de baja antes de continuar"
    if estado == "Declinó":
        return "Declinó", ""
    if estado:
        return estado, ""
    if c.get("fecha_entrevista"):
        return "Entrevista", "Tiene entrevista agendada"
    if hay_evaluacion:
        return "En evaluación", "Ya tiene calificaciones"
    return "Nuevo", ""


def ronda_de(c, estado):
    if c.get("ronda") in RONDAS:
        r = c["ronda"]
    else:
        r = "Primera"
    if estado in ("Entrevista", "Finalista", "Contratado") or c.get("fecha_entrevista"):
        return "Segunda"
    return r


# ---------------------------------------------------------------- reagendas
def agenda_prueba(c):
    """(fecha, hora) de la prueba o None. Sin fecha propia, vale el día de aplicación."""
    hora = c.get("horario_prueba") or ""
    fecha = c.get("fecha_prueba") or c.get("fecha_aplicacion") or ""
    return (fecha, hora) if hora else None


def agenda_entrevista(c):
    fecha = c.get("fecha_entrevista") or ""
    return (fecha, c.get("hora_entrevista") or "") if fecha else None


def nivel_reagenda(n, maximo):
    """ninguna / uso (aún hay margen) / limite (ya usó todas) / excedido (se pasó)."""
    if n <= 0:
        return "ninguna"
    if n > maximo:
        return "excedido"
    return "limite" if n == maximo else "uso"


def formato_agenda(a):
    """(fecha ISO, hora) -> '26/11/2026 15:00'."""
    if not a:
        return ""
    f, h = a
    return ((f"{f[8:10]}/{f[5:7]}/{f[:4]}" if f else "sin fecha") + (f" {h}" if h else "")).strip()


NIVELES_REAGENDA = ["ninguna", "uso", "limite", "excedido"]


def resumen_reagendas(n_pruebas, n_entrevistas):
    """Contadores con su máximo, nivel (para el color) y el nivel más alto de los dos."""
    cuentas = {}
    for clave, n in (("pruebas", n_pruebas), ("entrevistas", n_entrevistas)):
        m = int(REAGENDAS[clave])
        cuentas[clave] = {"n": n, "max": m, "nivel": nivel_reagenda(n, m)}
    peor = max((c["nivel"] for c in cuentas.values()), key=NIVELES_REAGENDA.index)
    return {**cuentas, "nivel": peor}


def cambios_de_agenda(antes, ahora):
    """Qué agendas cambian al guardar: lista de (tipo, agenda_anterior, agenda_nueva).
    Solo es reagenda si ya había una fecha/hora y ahora hay otra distinta."""
    res = []
    for tipo, f in (("prueba", agenda_prueba), ("entrevista", agenda_entrevista)):
        a, b = f(antes), f(ahora)
        if a and b and a != b:
            res.append((tipo, a, b))
    return res


# ---------------------------------------------------------------- capacidad por día
def cupo_entrevistas(candidatos, fecha_iso, excluir_id=None):
    """(agendadas, capacidad) de entrevistas ese día; cuentan solo los que siguen en proceso."""
    n = sum(1 for c in candidatos if c.get("fecha_entrevista") == fecha_iso
            and c.get("id") != excluir_id and c.get("estado") in ACTIVOS)
    return n, CAPACIDAD["entrevistas_por_dia"]


def cupo_pruebas(candidatos, fecha_iso, hora, excluir_id=None):
    """Pruebas agendadas en esa hora (3 candidatos por hora)."""
    if not fecha_iso or not hora:
        return 0, CAPACIDAD["pruebas_por_hora"]
    n = sum(1 for c in candidatos if c.get("fecha_prueba") == fecha_iso
            and (c.get("horario_prueba") or "")[:2] == hora[:2]
            and c.get("id") != excluir_id and c.get("estado") in ACTIVOS)
    return n, CAPACIDAD["pruebas_por_hora"]


# ---------------------------------------------------------------- programación (embudo aparte)
FASES = ["Publicidad", "Pruebas de habilidades", "Entrevistas", "Seguimiento de documentación",
         "Firma de documentos", "Capacitación"]
ESTADOS_ACT = ["Sin reporte", "Programada", "En curso", "Completada", "Reprogramada", "Cancelada"]
RESPONSABLES = ["DANIEL", "JACKY", "ADRIANA", "DEBI", "TONY", "ALEJANDRO"]


def fase_de(actividad):
    """Fase del embudo de programación según el texto de la actividad."""
    t = _t(actividad)
    if "publicidad" in t:
        return FASES[0]
    if "capacitacion" in t:
        return FASES[5]
    if "firma" in t:
        return FASES[4]
    if "document" in t or "papeles" in t:
        return FASES[3]
    if "entrevista" in t and "prueba" not in t:
        return FASES[2]
    if "prueba" in t:
        return FASES[1]
    return FASES[0]


def situacion_actividad(a, hoy=None):
    """Hoy / Atrasada (pasó sin reporte) / Próxima / Cerrada, para resaltar lo que pide atención."""
    hoy = (hoy or date.today()).isoformat()
    if a.get("estado") in ("Completada", "Cancelada", "Reprogramada"):
        return "Cerrada"
    ini, fin = a.get("fecha_inicio") or "", a.get("fecha_fin") or a.get("fecha_inicio") or ""
    if fin and fin < hoy:
        return "Atrasada"
    if ini and ini <= hoy <= fin:
        return "Hoy"
    return "Próxima"


def convocatoria_de(fecha_iso, publicidades):
    """Convocatoria (ciclo) a la que pertenece una fecha: la última publicidad anterior."""
    prev = [p for p in publicidades if p <= (fecha_iso or "")]
    if not prev:
        return ""
    m = max(prev)
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{meses[int(m[5:7]) - 1].capitalize()} {m[:4]}"


def a_json(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
