"""Carga y exporta los datos del proceso de selección en un archivo JSON.

- Carga automática: al abrir la app se revisan las carpetas de importación; cada archivo se
  carga una sola vez (se recuerda su huella) y nunca pisa lo que ya se editó en la app.
- Cargar de nuevo el mismo archivo no duplica nada (se reconoce a cada persona por su teléfono,
  correo o nombre).
- Antes de cambiar la base se crea un respaldo.
"""
import glob
import hashlib
import json
import os
from datetime import datetime

import base_datos as bd
import respaldos
import seleccion as sel

FORMATO = "rrhh-datos/1"
CLAVE_HECHOS = "json_cargados"
NOMBRES = ("datos_iniciales*.json", "rrhh_datos*.json")


def carpetas_importacion():
    casa = os.path.expanduser("~")
    return [os.path.join(bd.CARPETA_DATOS, "importar"),
            os.path.join(bd._carpeta_base(), "importar"), bd._carpeta_base(),
            os.path.join(casa, "Downloads"), os.path.join(casa, "Descargas"),
            os.path.join(casa, "Desktop"), os.path.join(casa, "Escritorio")]


def archivos_pendientes():
    vistos, res = set(), []
    for carpeta in carpetas_importacion():
        for patron in NOMBRES:
            for ruta in sorted(glob.glob(os.path.join(carpeta, patron))):
                real = os.path.realpath(ruta)
                if real not in vistos:
                    vistos.add(real)
                    res.append(ruta)
    return res


def _huella(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _cargados():
    try:
        return json.loads(bd.leer_config(CLAVE_HECHOS, "[]") or "[]")
    except ValueError:
        return []


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ValueError("El archivo no es un JSON de datos de esta aplicación.")
    if not isinstance(datos.get("candidatos", []), list) or \
            not isinstance(datos.get("programacion", []), list):
        raise ValueError("El archivo está incompleto: faltan candidatos o programación.")
    return datos


def _texto(v):
    return "" if v is None else str(v)


def _limpio_candidato(c):
    nombre = sel.nombre_normal(c.get("nombre"))
    if not nombre:
        raise ValueError("Hay un candidato sin nombre.")
    d = {k: c.get(k) for k in bd.COLUMNAS["candidatos"]}
    d["nombre"] = nombre
    d["telefono"] = sel.telefono_normal(d.get("telefono"))
    d["correo"] = sel.correo_normal(d.get("correo"))
    d["asistencia"] = sel.asistencia_normal(d.get("asistencia"))
    d["estado"] = sel.estado_normal(d.get("estado")) or "Nuevo"
    d["ronda"] = d.get("ronda") if d.get("ronda") in sel.RONDAS else "Primera"
    for k in ("fecha_aplicacion", "fecha_prueba", "fecha_entrevista"):
        d[k] = sel.fecha_normal(d.get(k))
    for k in ("horario_prueba", "hora_entrevista"):
        d[k] = sel.hora_normal(d.get(k)) or ""
    d["_historial"] = _historial_limpio(c.get("historial"))
    return d


def _historial_limpio(lista):
    res = []
    for h in lista if isinstance(lista, list) else []:
        if not isinstance(h, dict) or h.get("tipo") not in bd.TIPOS_HISTORIAL:
            continue
        res.append({"tipo": h["tipo"], "fecha": sel.fecha_normal(h.get("fecha")) or "",
                    "hora": sel.hora_normal(h.get("hora")) or "",
                    "detalle": _texto(h.get("detalle")).strip()})
    return res


def _clave_hist(h):
    return (h["tipo"], h["fecha"], h["hora"], h["detalle"])


def importar(ruta, respaldar=True, actualizar=False, simular=False):
    """Carga el archivo. Con actualizar=True también corrige a los que ya existen con lo que diga
    el archivo (solo campos con valor); con simular=True no cambia nada y solo cuenta. Devuelve {'candidatos': n, 'programacion': n, 'omitidos': n, ...}."""
    datos = leer(ruta)
    cands = [_limpio_candidato(c) for c in datos.get("candidatos", [])]
    prog = datos.get("programacion", [])
    existentes = {}
    for c in bd.listar("candidatos"):
        existentes[sel.clave_candidato(c["nombre"], c["telefono"], c["correo"])] = c
        existentes.setdefault("nom:" + sel.clave_nombre(c["nombre"]), c)
    por_ver = {(p["fecha_inicio"], sel.clave_nombre(p["actividad"])) for p in bd.listar("programacion")}
    nuevos_c, cambios_c, hist_previos = [], [], []
    for c in cands:  # también evita repetidos dentro del mismo archivo
        k, kn = sel.clave_candidato(c["nombre"], c["telefono"], c["correo"]), "nom:" + sel.clave_nombre(c["nombre"])
        previo = existentes.get(k) or existentes.get(kn)
        if previo is not None:
            if previo.get("id") is not None and not previo.get("_visto"):
                dif = {f: c[f] for f in bd.COLUMNAS["candidatos"]
                       if f != "nombre" and c.get(f) not in (None, "")
                       and (previo.get(f) or "") != c[f]}
                previo["_visto"] = True
                if c["_historial"]:
                    hist_previos.append((previo["id"], c["_historial"]))
                if dif:
                    cambios_c.append((previo["id"], dif))
            continue
        existentes[k] = existentes[kn] = c
        nuevos_c.append(c)
    nuevos_p = []
    for p in prog:
        ini = sel.fecha_normal(p.get("fecha_inicio"))
        if not ini or not _texto(p.get("actividad")).strip():
            continue
        if (ini, sel.clave_nombre(p["actividad"])) in por_ver:
            continue
        por_ver.add((ini, sel.clave_nombre(p["actividad"])))
        nuevos_p.append({"fecha_inicio": ini,
                         "fecha_fin": sel.fecha_normal(p.get("fecha_fin")) or ini,
                         "actividad": sel.limpiar(p["actividad"]),
                         "fase": p.get("fase") or sel.fase_de(p["actividad"]),
                         "responsable": _texto(p.get("responsable")).upper(),
                         "estado": p.get("estado") if p.get("estado") in sel.ESTADOS_ACT
                         else "Sin reporte", "reporte": _texto(p.get("reporte")),
                         "notas": _texto(p.get("notas")),
                         "convocatoria": _texto(p.get("convocatoria"))})
    # historial que falta (siempre se suma; nunca se borra nada)
    hist_nuevos = []
    for id_c, lista in hist_previos:
        ya = {_clave_hist(h) for h in bd.historial_de(id_c)}
        hist_nuevos += [(id_c, h) for h in lista if _clave_hist(h) not in ya]
    n_hist = len(hist_nuevos) + sum(len(c["_historial"]) for c in nuevos_c)
    antes = bd.leer_config("parametros_seleccion")
    parametros = datos.get("parametros") or {}
    if simular:
        return {"candidatos": len(nuevos_c), "programacion": len(nuevos_p),
                "cambian": len(cambios_c), "historial": n_hist}
    if (nuevos_c or nuevos_p or hist_nuevos or (actualizar and cambios_c) or (parametros and not antes)
            or datos.get("calendario")) and respaldar:
        ruta_zip = os.path.join(respaldos.carpeta_respaldos(),
                                respaldos.nombre_nuevo("RRHH_antes_de_cargar_"))
        respaldos.crear_respaldo(ruta_zip)
    if actualizar:
        for id_c, dif in cambios_c:
            bd.guardar("candidatos", dif, id_c)
    for c in nuevos_c:
        id_nuevo = bd.guardar("candidatos", c)
        for h in c["_historial"]:
            bd.agregar_historial(id_nuevo, h["tipo"], h["fecha"], h["hora"], h["detalle"])
    for id_c, h in hist_nuevos:
        bd.agregar_historial(id_c, h["tipo"], h["fecha"], h["hora"], h["detalle"])
    bd.insertar_varios("programacion", nuevos_p)
    if parametros and not antes:
        bd.guardar_config("parametros_seleccion", json.dumps(
            {"umbral_a": parametros.get("umbral_a", sel.UMBRALES["a"]),
             "umbral_b": parametros.get("umbral_b", sel.UMBRALES["b"]),
             "reagendas": parametros.get("reagendas") or {},
             "capacidad": parametros.get("capacidad") or {}}))
        if not bd.leer_config("configuracion"):  # primera vez: la configuración parte del JSON
            import configuracion
            configuracion.cargar()
            configuracion.guardar()
    if datos.get("calendario"):
        previo = json.loads(bd.leer_config("calendario_notas", "{}") or "{}")
        for m in datos["calendario"]:
            previo.setdefault(m["mes"], {"notas": m.get("notas", []),
                                         "etiquetas": m.get("etiquetas", {})})
        bd.guardar_config("calendario_notas", json.dumps(previo, ensure_ascii=False))
    return {"candidatos": len(nuevos_c), "programacion": len(nuevos_p),
            "actualizados": len(cambios_c) if actualizar else 0, "cambian": len(cambios_c),
            "omitidos": (len(cands) - len(nuevos_c)) + (len(prog) - len(nuevos_p)),
            "historial": n_hist}


def cargar_automaticamente():
    """Carga los archivos nuevos de las carpetas de importación. Nunca lanza error."""
    resultado = []
    try:
        hechos = _cargados()
        for ruta in archivos_pendientes():
            try:
                h = _huella(ruta)
            except OSError:
                continue
            if h in hechos:
                continue
            try:
                r = importar(ruta)
            except (ValueError, OSError, json.JSONDecodeError) as e:
                resultado.append({"archivo": os.path.basename(ruta), "error": str(e)})
                continue
            hechos.append(h)
            bd.guardar_config(CLAVE_HECHOS, json.dumps(hechos))
            resultado.append({"archivo": os.path.basename(ruta), **r})
    except Exception as e:  # el arranque no debe fallar por esto
        resultado.append({"archivo": "", "error": f"{type(e).__name__}: {e}"})
    return resultado


def exportar(ruta):
    cands = []
    for c in bd.listar("candidatos"):
        d = {k: c.get(k) for k in bd.COLUMNAS["candidatos"]}
        d["historial"] = [{k: h[k] for k in ("tipo", "fecha", "hora", "detalle")}
                          for h in bd.historial_de(c["id"])]
        cands.append(d)
    cands.reverse()
    prog = [{k: p.get(k) for k in bd.COLUMNAS["programacion"]} for p in bd.listar("programacion")]
    prog.sort(key=lambda p: (p["fecha_inicio"], p["actividad"]))
    cal = json.loads(bd.leer_config("calendario_notas", "{}") or "{}")
    datos = {"formato": FORMATO, "generado": datetime.now().isoformat(timespec="seconds"),
             "origen": "Exportado desde la aplicación",
             "parametros": {"umbral_a": sel.UMBRALES["a"], "umbral_b": sel.UMBRALES["b"],
                            "capacidad": sel.CAPACIDAD, "reagendas": sel.REAGENDAS},
             "candidatos": cands, "programacion": prog,
             "calendario": [{"mes": k, **v} for k, v in sorted(cal.items())]}
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    return {"candidatos": len(cands), "programacion": len(prog)}
