import copy
import json

import base_datos as bd
import documentos
import ausencias
import evaluacion
import logica
import ranking

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


def aplicar(datos):
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
    if isinstance(datos, dict):
        aplicar(datos)


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
