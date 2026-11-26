"""Convierte el libro «Planilla de candidatos» al JSON que la app carga sola.

Uso:  python convertir_libro.py libro.xlsx [salida.json] [informe.md]
Clasifica todo de una vez: limpia, une duplicados, deduce estados y deja un informe de cambios.
"""
import json
import re
import sys
from datetime import datetime

import openpyxl

import evaluacion as ev
import seleccion as sel

FORMATO = "rrhh-datos/1"


def _txt(v):
    return sel.limpiar(v) if v is not None else ""


def _leer_candidatos(wb, informe):
    ws = wb["Candidatos"]
    cab = {sel.clave_nombre(ws.cell(4, c).value): c for c in range(1, ws.max_column + 1)
           if ws.cell(4, c).value}
    col = lambda *n: next((cab[k] for k in n if k in cab), None)
    c_nom, c_pue, c_fap, c_tel = col("candidato"), col("puesto"), col("fechadeaplicacion"), \
        col("telefonowhatsapp")
    c_asi, c_cor, c_fue, c_ron = col("asistencia"), col("correo"), col("fuente"), col("ronda")
    c_est, c_hor, c_ent, c_hen, c_obs = col("estado"), col("horario"), col("entrevista"), \
        col("horaio", "horario2"), col("observaciones")
    filas = []
    for r in range(5, ws.max_row + 1):
        g = lambda c: ws.cell(r, c).value if c else None
        if not _txt(g(c_nom)):
            continue
        filas.append({
            "fila": r, "nombre_original": _txt(g(c_nom)), "puesto": _txt(g(c_pue)),
            "fecha_aplicacion_crudo": g(c_fap), "telefono": _txt(g(c_tel)),
            "asistencia": _txt(g(c_asi)), "correo": _txt(g(c_cor)), "fuente": _txt(g(c_fue)),
            "ronda": _txt(g(c_ron)), "estado": _txt(g(c_est)), "horario_crudo": g(c_hor),
            "entrevista_crudo": g(c_ent), "hora_entrevista_crudo": g(c_hen),
            "observaciones": _txt(g(c_obs))})
    return filas


def _evaluaciones_hoja(wb):
    """{clave_nombre: texto_json} de la hoja Evaluaciones (una fila por candidato)."""
    ws = wb["Evaluaciones"]
    # columnas de criterios en el orden de evaluacion.SECCIONES (se saltan las de % y notas)
    cols = {}
    c = 3
    for i, sec in enumerate(ev.SECCIONES):
        n = len(sec["criterios"])
        cols[i] = list(range(c, c + n))
        c += n
        if sec["global"]:
            cols[i].append(c)
            c += 1
        c += 1  # columna de %
    c_obs, c_pen = c, c + 1
    res = {}
    for r in range(6, ws.max_row + 1):
        nombre = _txt(ws.cell(r, 2).value)
        if not nombre:
            continue
        det = ev.vacio()
        for i, sec in enumerate(det["secciones"]):
            vals = [ws.cell(r, k).value for k in cols[i]]
            k = len(sec["criterios"])
            for cr, v in zip(sec["criterios"], vals[:k]):
                cr["calificacion"] = v if isinstance(v, (int, float)) else None
            if ev.SECCIONES[i]["global"]:
                v = vals[k]
                sec["global"] = v if isinstance(v, (int, float)) else None
        det["pendientes"] = _txt(ws.cell(r, c_pen).value)
        res[sel.clave_nombre(nombre)] = {"detalle": det, "observaciones": _txt(ws.cell(r, c_obs).value)}
    return res


def _fichas(wb, informe):
    """Las hojas por candidato (escritas a mano) mandan sobre la hoja Evaluaciones."""
    res = {}
    inicio = 5
    fin = next((i for i, n in enumerate(wb.sheetnames) if n.startswith("Hoja") or n in (
        "Matriz", "Ranking", "Resumen")), len(wb.sheetnames))
    for n in wb.sheetnames[inicio:fin]:
        ws = wb[n]
        nombre = _txt(ws["B4"].value)
        if not nombre or nombre.lower().startswith("ejemplo"):
            continue
        det = ev.vacio()
        fila = 9
        # las secciones están una debajo de otra; se localizan por su título en la columna A
        pos = {}
        for r in range(1, ws.max_row + 1):
            t = _txt(ws.cell(r, 1).value)
            for s in ev.SECCIONES:
                if t == s["nombre"]:
                    pos[s["nombre"]] = r
        for sec in det["secciones"]:
            r0 = pos.get(sec["nombre"])
            if not r0:
                continue
            for k, cr in enumerate(sec["criterios"]):
                v = ws.cell(r0 + 2 + k, 2).value
                cr["calificacion"] = v if isinstance(v, (int, float)) else None
            g = [ev_s for ev_s in ev.SECCIONES if ev_s["nombre"] == sec["nombre"]][0]["global"]
            if g:
                v = ws.cell(r0 + 2 + len(sec["criterios"]) + 1, 2).value
                sec["global"] = v if isinstance(v, (int, float)) else None
        obs = pen = ""
        for r in range(1, ws.max_row + 1):
            t = _txt(ws.cell(r, 1).value)
            if t == "Observaciones":
                obs = _txt(ws.cell(r + 1, 1).value)
            if t == "Pendientes por confirmar":
                pen = _txt(ws.cell(r + 1, 1).value)
        det["pendientes"] = pen
        res[sel.clave_nombre(nombre)] = {"detalle": det, "observaciones": obs, "hoja": n}
    return res


def _sin_notas(det):
    return all(c["calificacion"] is None for s in det["secciones"] for c in s["criterios"]) and \
        all(s["global"] is None for s in det["secciones"])


def _todo_cero(det):
    notas = [c["calificacion"] for s in det["secciones"] for c in s["criterios"]
             if c["calificacion"] is not None]
    notas += [s["global"] for s in det["secciones"] if s["global"] is not None]
    return bool(notas) and all(n == 0 for n in notas)


def _programacion(wb):
    ws = wb["Seguimiento"]
    cab = None
    for r in range(1, 12):
        if _txt(ws.cell(r, 1).value).lower().startswith("fecha"):
            cab = r
            break
    cab = cab or 4
    filas = []
    for r in range(cab + 1, ws.max_row + 1):
        ini = sel.fecha_normal(ws.cell(r, 1).value)
        act = _txt(ws.cell(r, 3).value)
        if not ini or not act:
            continue
        fin = sel.fecha_normal(ws.cell(r, 2).value) or ini
        resp = _txt(ws.cell(r, 4).value).upper()
        est = _txt(ws.cell(r, 6).value) or "Sin reporte"
        est = "Sin reporte" if est.lower().startswith("sin") else est
        filas.append({"fecha_inicio": ini, "fecha_fin": fin, "actividad": act,
                      "fase": sel.fase_de(act), "responsable": resp,
                      "estado": est if est in sel.ESTADOS_ACT else "Sin reporte",
                      "reporte": _txt(ws.cell(r, 7).value), "notas": _txt(ws.cell(r, 8).value)})
    return filas


def _calendario(wb):
    """Notas de cada mes: encargada de entrevistas, avisos, feriados."""
    meses = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8,
             "sep": 9, "oct": 10, "nov": 11, "dic": 12}
    res = []
    for n in wb.sheetnames:
        m = re.fullmatch(r"([A-Za-z]{3}) (\d{4})", n.strip())
        if not m or m.group(1).lower() not in meses:
            continue
        ws = wb[n]
        textos = []
        for r in range(8, ws.max_row + 1):
            t = ws.cell(r, 1).value
            crudo = str(t) if t else ""
            if _txt(t) and _txt(t) not in ("HORARIOS", "TOME NOTA") \
                    and not crudo.startswith(("Pruebas de habilidades", "Entrevistas")):
                textos.append(re.sub(r"\s+", " ", str(t)).strip())
        etiquetas = {}
        for row in ws.iter_rows(min_row=6, min_col=4, max_col=10):
            for c in row:
                if isinstance(c.value, str) and c.value.strip():
                    etiquetas[c.coordinate] = re.sub(r"\s+", " ", c.value).strip()
        res.append({"mes": f"{m.group(2)}-{meses[m.group(1).lower()]:02d}",
                    "notas": textos, "etiquetas": etiquetas})
    return res


def _agenda_de_fila(x):
    """(fecha, hora) de la prueba y de la entrevista de una fila cruda del libro."""
    f_ap = sel.fecha_normal(x["fecha_aplicacion_crudo"]) or ""
    hora = sel.hora_normal(x.get("horario_crudo")) or ""
    f_en = sel.fecha_normal(x.get("entrevista_crudo")) or ""
    h_en = sel.hora_normal(x.get("hora_entrevista_crudo")) or "" if f_en else ""
    return ((f_ap, hora) if hora else None), ((f_en, h_en) if f_en else None)


def _fmt(f, h):
    return (f"{f[8:10]}/{f[5:7]}/{f[:4]}" if f else "sin fecha") + (f" {h}" if h else "")


def _historial(c):
    """Todo lo anterior de una persona repetida: cada postulación previa y cada agenda que se
    cambió (esas cuentan como reagendas)."""
    todas = c.get("_todas") or []
    if len(todas) < 2:
        return []
    res = []
    for x in c["_previas"]:
        prueba, entrevista = _agenda_de_fila(x)
        partes = [f"Estado: {sel.estado_normal(x['estado']) or 'sin estado'}"]
        for rot, v in (("Asistencia", sel.asistencia_normal(x["asistencia"])), ("Ronda", x["ronda"]),
                       ("Obs.", x["observaciones"])):
            if v:
                partes.append(f"{rot}: {v}")
        crudos = [("Nombre", x["nombre_original"]), ("Teléfono", x["telefono_original"]),
                  ("Correo", x["correo_original"]), ("Puesto", x["puesto"]), ("Fuente", x["fuente"])]
        partes += [f"{k}: {v}" for k, v in crudos if v]
        res.append({"tipo": "postulacion", "fecha": sel.fecha_normal(x["fecha_aplicacion_crudo"]) or "",
                    "hora": prueba[1] if prueba else "",
                    "detalle": f"Postulación previa tal como está en el libro (fila {x['fila']}). " + " · ".join(partes)})
    for clave, tipo in ((0, "prueba"), (1, "entrevista")):
        agendas = []
        for x in todas:  # las agendas distintas, en orden; la última es la vigente
            a = _agenda_de_fila(x)[clave]
            if a and a not in agendas:
                agendas.append(a)
        for a in agendas[:-1]:
            res.append({"tipo": tipo, "fecha": a[0], "hora": a[1],
                        "detalle": f"{'Prueba' if tipo == 'prueba' else 'Entrevista'} agendada "
                                   f"para {_fmt(*a)}; se reagendó"})
    res.append(_aviso_duplicado(todas))
    return res


def _aviso_duplicado(todas):
    """Texto de «Posible duplicado»: en qué coinciden las filas y qué datos cambian entre ellas."""
    def repetido(clave):
        vistos = [clave(x) for x in todas if clave(x)]
        return len(vistos) != len(set(vistos))
    coinciden = [n for n, c in (("teléfono", lambda x: sel.digitos_telefono(x["telefono"])),
                                ("correo", lambda x: x["correo"]),
                                ("nombre", lambda x: sel.clave_nombre(x["nombre"]))) if repetido(c)]
    cambian = []
    for n, k in (("teléfono", "telefono_original"), ("correo", "correo_original"),
                 ("nombre", "nombre_original")):
        vals = list(dict.fromkeys(x[k] for x in todas if x[k]))
        if len(vals) > 1:
            cambian.append(f"{n}: " + " / ".join(vals))
    filas = ", ".join(str(x["fila"]) for x in todas)
    texto = (f"Posible duplicado: las {len(todas)} filas {filas} del libro pueden ser la misma persona "
             f"porque coinciden en {', '.join(coinciden) or 'sus datos'}. ")
    if cambian:
        texto += "Datos distintos entre ellas: " + "; ".join(cambian) + ". "
    return {"tipo": "duplicado", "fecha": "", "hora": "",
            "detalle": texto + "Se unieron en un solo candidato; revisa si es correcto."}


def convertir(ruta_xlsx, ruta_json, ruta_informe):
    wb = openpyxl.load_workbook(ruta_xlsx, data_only=True)
    informe = {"cambios": [], "conflictos": [], "revisar": []}
    crudos = _leer_candidatos(wb, informe)
    de_hoja = _evaluaciones_hoja(wb)
    fichas = _fichas(wb, informe)

    # --- unir duplicados (mismo teléfono o correo o nombre)
    grupos = {}
    for c in crudos:
        c["telefono_original"], c["correo_original"] = c["telefono"], c["correo"]
        c["nombre"] = sel.nombre_normal(c["nombre_original"])
        if c["nombre"] != c["nombre_original"]:
            informe["cambios"].append(f"Nombre fila {c['fila']}: «{c['nombre_original']}» → "
                                      f"«{c['nombre']}»")
        c["telefono"] = sel.telefono_normal(c["telefono"])
        c["correo"] = sel.correo_normal(c["correo"])
        # misma persona si coincide el teléfono, el correo o el nombre (une las claves)
        claves = [x for x in ("tel:" + sel.digitos_telefono(c["telefono"]) if sel.digitos_telefono(c["telefono"]) else "",
                              "mail:" + c["correo"] if c["correo"] else "",
                              "nom:" + sel.clave_nombre(c["nombre"])) if x]
        destino = next((grupos[x] for x in claves if x in grupos), None)
        if destino is None:
            destino = []
        destino.append(c)
        for x in claves:
            grupos[x] = destino
    unidos, vistos = [], set()
    for lst in grupos.values():
        if id(lst) in vistos:
            continue
        vistos.add(id(lst))
        # orden cronológico: por fecha de aplicación y, si empatan, por fila del libro
        lst.sort(key=lambda x: (sel.fecha_normal(x["fecha_aplicacion_crudo"]) or "", x["fila"]))
        base = lst[-1]  # la fila más reciente manda
        base["_previas"] = lst[:-1]
        base["_todas"] = lst
        if len(lst) > 1:
            informe["cambios"].append(
                f"Repetido unido: {base['nombre']} (filas {', '.join(str(x['fila']) for x in lst)}); "
                "las filas anteriores quedan en su historial")
            for x in reversed(lst[:-1]):  # lo más reciente primero: completa lo que falte
                for campo in ("observaciones", "correo", "telefono", "fuente", "puesto",
                              "horario_crudo", "entrevista_crudo",
                              "hora_entrevista_crudo"):
                    if not base.get(campo) and x.get(campo) not in (None, ""):
                        base[campo] = x[campo]
                if x["observaciones"] and x["observaciones"] != base["observaciones"]:
                    base["observaciones"] = (x["observaciones"] + " | " + base["observaciones"]).strip(" |")
        unidos.append(base)

    candidatos = []
    for c in unidos:
        kn = sel.clave_nombre(c["nombre"])
        ficha = fichas.get(kn)
        hoja = de_hoja.get(kn)
        if ficha is None:  # a veces el nombre de la ficha trae apellido distinto: primer nombre
            primero = kn[:6]
            cand = [k for k in fichas if k.startswith(primero)]
            if len(cand) == 1 and len([x for x in unidos if sel.clave_nombre(x["nombre"]).startswith(primero)]) == 1:
                ficha = fichas[cand[0]]
        if hoja is None:
            primero = kn[:6]
            cand = [k for k in de_hoja if k.startswith(primero)]
            if len(cand) == 1 and len([x for x in unidos if sel.clave_nombre(x["nombre"]).startswith(primero)]) == 1:
                hoja = de_hoja[cand[0]]
        det, obs_eval, origen = None, "", ""
        if ficha and not _sin_notas(ficha["detalle"]):
            det, obs_eval, origen = ficha["detalle"], ficha["observaciones"], "ficha " + ficha["hoja"]
            if hoja and not _sin_notas(hoja["detalle"]) and hoja["detalle"] != ficha["detalle"]:
                informe["conflictos"].append(
                    f"{c['nombre']}: la ficha «{ficha['hoja']}» y la hoja Evaluaciones tienen notas "
                    f"distintas; se usó la ficha (escrita a mano).")
        elif hoja and not _sin_notas(hoja["detalle"]):
            det, obs_eval, origen = hoja["detalle"], hoja["observaciones"], "hoja Evaluaciones"
        if det is not None and _todo_cero(det):
            informe["cambios"].append(f"{c['nombre']}: evaluación toda en 0 (no se presentó); "
                                      "se conserva tal como está en el libro.")
        c["_det"], c["_origen"] = det, origen
        if obs_eval and obs_eval != c["observaciones"]:
            c["observaciones"] = (c["observaciones"] + " | " if c["observaciones"] else "") + obs_eval
        pen = det["pendientes"] if det else ""
        c["pendientes"] = pen
        candidatos.append(c)

    salida = []
    for c in candidatos:
        f_ap = sel.fecha_normal(c["fecha_aplicacion_crudo"])
        if c["fecha_aplicacion_crudo"] not in (None, "") and not f_ap:
            informe["revisar"].append(f"{c['nombre']}: fecha de aplicación ilegible "
                                      f"(«{c['fecha_aplicacion_crudo']}»)")
        elif isinstance(c["fecha_aplicacion_crudo"], str) and f_ap:
            informe["cambios"].append(f"{c['nombre']}: fecha «{c['fecha_aplicacion_crudo']}» → {f_ap}")
        c["fecha_aplicacion"] = f_ap
        ent = c["entrevista_crudo"]
        c["fecha_entrevista"] = sel.fecha_normal(ent)
        texto_ent = _txt(ent) if ent and not c["fecha_entrevista"] else ""
        c["fecha_entrevista_texto"] = texto_ent
        c["hora_entrevista"] = sel.hora_normal(c["hora_entrevista_crudo"]) or ""
        hp = sel.hora_normal(c["horario_crudo"])
        c["horario_prueba"] = hp or ""
        if c["horario_crudo"] and not hp:
            informe["revisar"].append(f"{c['nombre']}: horario de prueba ilegible («{c['horario_crudo']}»)")
        c["asistencia"] = sel.asistencia_normal(c["asistencia"])
        c["puesto"] = c["puesto"] or "Otro"
        c["fuente"] = c["fuente"] or "Otro"
        c["observaciones"] = c["observaciones"]
        # horario de la prueba: el libro solo guarda la hora; la fecha de prueba = día de aplicación
        c["fecha_prueba"] = f_ap if c["horario_prueba"] else None
        estado_orig = sel.estado_normal(c["estado"])
        estado, motivo = sel.clasificar_estado(c, hay_evaluacion=c["_det"] is not None)
        if estado != estado_orig:
            informe["cambios"].append(
                f"Estado de {c['nombre']}: «{c['estado'] or '(vacío)'}» → «{estado}»"
                + (f" ({motivo})" if motivo else ""))
        c["estado"] = estado
        c["ronda"] = sel.ronda_de(c, estado)
        c["motivo"] = motivo if estado in sel.CERRADOS else ""
        r = sel.resumen_evaluacion(c["_det"] if c["_det"] else None)
        g = sel.grupo_de(r["comparable"])
        c["recomendacion"] = ""
        c["lectura"] = ""
        if estado in sel.ACTIVOS and r["hechas"] and r["comparable"] is None:
            informe["revisar"].append(f"{c['nombre']}: faltan {', '.join(sel.falta_registrar(r)).lower()}")
        salida.append({
            "nombre": c["nombre"], "puesto": c["puesto"], "fecha_aplicacion": f_ap,
            "telefono": c["telefono"], "asistencia": c["asistencia"], "correo": c["correo"],
            "fuente": c["fuente"], "ronda": c["ronda"], "estado": estado,
            "fecha_prueba": c["fecha_prueba"], "horario_prueba": c["horario_prueba"],
            "fecha_entrevista": c["fecha_entrevista"], "hora_entrevista": c["hora_entrevista"],
            "observaciones": c["observaciones"] + (f" | Entrevista: {texto_ent}" if texto_ent else ""),
            "pendientes": c["pendientes"],
            "evaluacion": ev_json(c["_det"]) if c["_det"] else "",
            "recomendacion": "", "lectura": "", "motivo": c["motivo"],
            "historial": _historial(c),
            "_grupo": g, "_origen": c["_origen"]})

    prog = _programacion(wb)
    pubs = [p["fecha_inicio"] for p in prog if p["fase"] == sel.FASES[0]]
    for p in prog:
        p["convocatoria"] = sel.convocatoria_de(p["fecha_inicio"], pubs)
    for c in salida:
        c["convocatoria"] = sel.convocatoria_de(c["fecha_aplicacion"], pubs) or "Nov 2026"

    datos = {"formato": FORMATO, "generado": datetime.now().isoformat(timespec="seconds"),
             "origen": ruta_xlsx.replace("\\", "/").split("/")[-1],
             "parametros": {"umbral_a": sel.UMBRALES["a"], "umbral_b": sel.UMBRALES["b"],
                            "capacidad": sel.CAPACIDAD, "reagendas": sel.REAGENDAS},
             "criterios": [{"nombre": s["nombre"], "global": s["global"],
                            "criterios": [{"criterio": c, "maximo": m} for c, m in s["criterios"]]}
                           for s in ev.SECCIONES],
             "candidatos": [{k: v for k, v in c.items() if not k.startswith("_")} for c in salida],
             "programacion": prog, "calendario": _calendario(wb)}
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)

    # --- informe
    m = sel.matriz([{"id": i, **c, "id": i} for i, c in enumerate(datos["candidatos"])])
    por_estado = {}
    for c in datos["candidatos"]:
        por_estado[c["estado"]] = por_estado.get(c["estado"], 0) + 1
    por_grupo = {}
    for f in m:
        por_grupo[f["grupo"]] = por_grupo.get(f["grupo"], 0) + 1
    L = ["# Informe de clasificación del libro", "",
         f"Origen: {datos['origen']}", "",
         f"- Candidatos únicos: **{len(datos['candidatos'])}** (filas leídas: {len(crudos)})",
         f"- Actividades de programación: **{len(prog)}**",
         f"- Meses de calendario: **{len(datos['calendario'])}**",
         "- Por estado: " + ", ".join(f"{k} {v}" for k, v in por_estado.items()),
         "- Por grupo: " + ", ".join(f"{k} {v}" for k, v in por_grupo.items()), ""]
    for t, k in (("Cambios aplicados", "cambios"), ("Conflictos resueltos", "conflictos"),
                 ("Para revisar a mano", "revisar")):
        L += [f"## {t} ({len(informe[k])})", ""] + [f"- {x}" for x in informe[k]] + [""]
    with open(ruta_informe, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return datos, informe


def ev_json(det):
    return json.dumps(det, ensure_ascii=False)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    d, i = convertir(a[0], a[1] if len(a) > 1 else "datos_iniciales.json",
                     a[2] if len(a) > 2 else "informe_clasificacion.md")
    print(len(d["candidatos"]), "candidatos;", len(d["programacion"]), "actividades;",
          {k: len(v) for k, v in i.items()})
