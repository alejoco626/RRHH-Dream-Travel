import copy
import json

import base_datos as bd
import documentos
import ausencias
import evaluacion
import logica
import ranking
import seleccion as sel

DEPARTAMENTOS = ["Ventas", "Reservas", "Visas", "Asistencia", "Procesos y control de calidad",
                 "Control de Calidad", "Administración", "Recursos humanos", "IT"]
TEMAS_MEMO = ["Paso 1: Creación de chat de discusión y brief sin errores",
              "Paso 2: Idea correcta del paquete"]
GRUPOS = list(logica.GRUPOS_AUTORIZACION)
PARAMETROS = {"dias_cumpleanos": 45}
CLAVE = "configuracion"


def _estado():
    return {
        "plazas": list(ranking.PLAZAS),
        "puestos": list(ranking.PUESTOS),
        "tipos_ausencia": list(ausencias.TIPOS),
        "etapas_ausencia": list(ausencias.ETAPAS),
        "departamentos": list(DEPARTAMENTOS),
        "temas_memo": list(TEMAS_MEMO),
        "categorias_adjunto": list(bd.CATEGORIAS_ADJUNTO),
        "grupos": {k: list(v) for k, v in logica.GRUPOS_AUTORIZACION.items()},
        "empresa": documentos.EMPRESA,
        "area": documentos.AREA,
        "ciudad": documentos.CIUDAD,
        "dias_cumpleanos": PARAMETROS["dias_cumpleanos"],
        "sel_fuentes": list(sel.FUENTES),
        "sel_puestos": list(sel.PUESTOS),
        "sel_responsables": list(sel.RESPONSABLES),
        "umbral_a": sel.UMBRALES["a"], "umbral_b": sel.UMBRALES["b"],
        "reagendas_pruebas": sel.REAGENDAS["pruebas"],
        "reagendas_entrevistas": sel.REAGENDAS["entrevistas"],
        "pruebas_por_hora": sel.CAPACIDAD["pruebas_por_hora"],
        "entrevistas_por_dia": sel.CAPACIDAD["entrevistas_por_dia"],
        "pruebas_horario": sel.CAPACIDAD["pruebas_horario"],
        "entrevistas_horario": sel.CAPACIDAD["entrevistas_horario"],
        "hora_desde": sel.VENTANA_HORAS[0], "hora_hasta": sel.VENTANA_HORAS[1],
        "comparables": list(sel.COMPARABLES),
        "pruebas_ranking": [[k, n] for k, n in sel.PRUEBAS],
        "escala": evaluacion.ESCALA,
        "secciones": [{"nombre": s["nombre"], "global": s["global"],
                       "criterios": [[c, m] for c, m in s["criterios"]]}
                      for s in evaluacion.SECCIONES],
    }


ORIGINAL = copy.deepcopy(_estado())


def _lista(valor):
    if isinstance(valor, list) and valor and all(isinstance(x, str) and x.strip() for x in valor):
        return [x.strip() for x in valor]
    return None


def _secciones(valor):
    if not isinstance(valor, list) or not valor:
        return None
    resultado = []
    for s in valor:
        try:
            criterios = [(str(c).strip(), float(m)) for c, m in s["criterios"]]
            nombre = str(s["nombre"]).strip()
        except (KeyError, TypeError, ValueError):
            return None
        if not nombre or any(not c or m <= 0 for c, m in criterios):
            return None
        criterios = [(c, int(m) if float(m).is_integer() else m) for c, m in criterios]
        resultado.append({"nombre": nombre, "global": (s.get("global") or "").strip() or None,
                          "criterios": criterios})
    return resultado


def _entero(valor, minimo, maximo):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return None
    return n if minimo <= n <= maximo and not isinstance(valor, bool) else None


def _aplicar_seleccion(datos):
    for clave, destino in (("sel_fuentes", sel.FUENTES), ("sel_puestos", sel.PUESTOS),
                           ("sel_responsables", sel.RESPONSABLES)):
        lista = _lista(datos.get(clave))
        if lista:
            destino[:] = lista
    try:
        a, b = float(datos["umbral_a"]), float(datos["umbral_b"])
        if 0 < b < a <= 1:
            sel.UMBRALES["a"], sel.UMBRALES["b"] = a, b
    except (KeyError, TypeError, ValueError):
        pass
    for clave, destino in (("reagendas_pruebas", "pruebas"), ("reagendas_entrevistas", "entrevistas")):
        n = _entero(datos.get(clave), 0, 20)
        if n is not None:
            sel.REAGENDAS[destino] = n
    for clave, tope in (("pruebas_por_hora", 100), ("entrevistas_por_dia", 100)):
        n = _entero(datos.get(clave), 1, tope)
        if n is not None:
            sel.CAPACIDAD[clave] = n
    sel.CAPACIDAD["pruebas_por_dia"] = sel.CAPACIDAD["pruebas_por_hora"] * 7
    for clave in ("pruebas_horario", "entrevistas_horario"):
        if isinstance(datos.get(clave), str) and datos[clave].strip():
            sel.CAPACIDAD[clave] = datos[clave].strip()
    desde, hasta = _entero(datos.get("hora_desde"), 0, 23), _entero(datos.get("hora_hasta"), 1, 24)
    if desde is not None and hasta is not None and desde < hasta:
        sel.VENTANA_HORAS[:] = [desde, hasta]
    claves = [k for k, _ in sel.PRUEBAS]
    comp = datos.get("comparables")
    if isinstance(comp, list) and comp and all(c in claves for c in comp):
        sel.COMPARABLES[:] = [k for k in claves if k in comp]
    nombres = datos.get("pruebas_ranking")
    if isinstance(nombres, list) and len(nombres) == len(sel.PRUEBAS):
        try:
            nuevas = [(k, str(n).strip() or viejo) for (k, viejo), (_, n) in zip(sel.PRUEBAS, nombres)]
            sel.PRUEBAS[:] = nuevas
        except (TypeError, ValueError):
            pass


def aplicar(datos):
    _aplicar_seleccion(datos)
    for clave, destino in (("plazas", ranking.PLAZAS), ("puestos", ranking.PUESTOS), ("tipos_ausencia", ausencias.TIPOS),
                           ("etapas_ausencia", ausencias.ETAPAS),
                           ("departamentos", DEPARTAMENTOS),
                           ("temas_memo", TEMAS_MEMO),
                           ("categorias_adjunto", bd.CATEGORIAS_ADJUNTO)):
        lista = _lista(datos.get(clave))
        if lista:
            destino[:] = lista
    grupos = datos.get("grupos")
    if isinstance(grupos, dict) and grupos and all(
            isinstance(k, str) and k.strip() and isinstance(v, list) for k, v in grupos.items()):
        logica.GRUPOS_AUTORIZACION.clear()
        logica.GRUPOS_AUTORIZACION.update({k.strip(): [str(x).strip() for x in v if str(x).strip()]
                                           for k, v in grupos.items()})
    GRUPOS[:] = list(logica.GRUPOS_AUTORIZACION)
    for clave, nombre in (("empresa", "EMPRESA"), ("area", "AREA"), ("ciudad", "CIUDAD")):
        if isinstance(datos.get(clave), str) and datos[clave].strip():
            setattr(documentos, nombre, datos[clave].strip())
    dias = datos.get("dias_cumpleanos")
    if isinstance(dias, int) and not isinstance(dias, bool) and 1 <= dias <= 365:
        PARAMETROS["dias_cumpleanos"] = dias
    if isinstance(datos.get("escala"), str) and datos["escala"].strip():
        evaluacion.ESCALA = datos["escala"].strip()
    secciones = _secciones(datos.get("secciones"))
    if secciones:
        evaluacion.SECCIONES[:] = secciones


def cargar():
    try:
        datos = json.loads(bd.leer_config(CLAVE) or "{}")
    except ValueError:
        datos = {}
    if isinstance(datos, dict) and datos:
        aplicar(datos)
    else:  # aún no se guarda la configuración: partir de los parámetros del JSON cargado
        try:
            p = json.loads(bd.leer_config("parametros_seleccion") or "{}")
        except ValueError:
            p = {}
        if isinstance(p, dict) and p:
            cap, rea = p.get("capacidad") or {}, p.get("reagendas") or {}
            aplicar({"umbral_a": p.get("umbral_a"), "umbral_b": p.get("umbral_b"),
                     "reagendas_pruebas": rea.get("pruebas"),
                     "reagendas_entrevistas": rea.get("entrevistas"),
                     "pruebas_por_hora": cap.get("pruebas_por_hora"),
                     "entrevistas_por_dia": cap.get("entrevistas_por_dia"),
                     "pruebas_horario": cap.get("pruebas_horario"),
                     "entrevistas_horario": cap.get("entrevistas_horario")})


def guardar():
    GRUPOS[:] = list(logica.GRUPOS_AUTORIZACION)
    bd.guardar_config(CLAVE, json.dumps(_estado(), ensure_ascii=False))


def restablecer():
    aplicar(copy.deepcopy(ORIGINAL))
    guardar()


def renombrar_plaza(viejo, nuevo):
    bd.renombrar_plaza(viejo, nuevo)


def leer_criterios(texto):
    criterios = []
    for n, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea:
            continue
        nombre, _, maximo = linea.rpartition("|") if "|" in linea else (linea, "", "5")
        try:
            valor = float(maximo.strip().replace(",", ".") or "5")
        except ValueError:
            raise ValueError(f"Línea {n}: el máximo debe ser un número.") from None
        if valor <= 0 or not nombre.strip():
            raise ValueError(f"Línea {n}: escribe el criterio y un máximo mayor que 0.")
        criterios.append((nombre.strip(), int(valor) if valor.is_integer() else valor))
    if not criterios:
        raise ValueError("Escribe al menos un criterio.")
    return criterios
