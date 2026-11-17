import json
import os
import re
import sys
from datetime import date, datetime

import openpyxl

IGNORAR = {"instrucciones", "candidatos", "criterios", "evaluaciones", "ficha", "matriz",
           "ranking", "resumen", "seguimiento"}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _es_hoja_de_persona(hoja):
    if hoja.title.strip().lower() in IGNORAR or re.match(r"^[A-Za-z]{3} \d{4}$", hoja.title):
        return False
    a4, b4 = hoja["A4"].value, hoja["B4"].value
    return bool(a4 and str(a4).startswith("Candidato") and b4 and "ejemplo" not in str(b4).lower())


def _fecha_de_aplicacion(libro, nombre):
    if "Candidatos" in libro.sheetnames:
        for fila in libro["Candidatos"].iter_rows(min_row=6, values_only=True):
            if fila[1] and str(fila[1]).strip().lower() == nombre.strip().lower():
                f = fila[3]
                if isinstance(f, (datetime, date)):
                    return f.strftime("%d/%m/%Y")
    return date.today().strftime("%d/%m/%Y")


def leer_hoja(libro, hoja):
    nombre = str(hoja["B4"].value).strip()
    puesto = str(hoja["B5"].value or "").strip() or None
    fecha = _fecha_de_aplicacion(libro, nombre)
    etapas, actual, texto_sig = [], None, None
    observaciones, pendientes = None, None
    for fila in hoja.iter_rows(min_row=6, values_only=True):
        a, b, c = (fila + (None, None, None))[:3]
        a = str(a).strip() if a is not None else ""
        if texto_sig:
            valor = a or None
            if texto_sig == "obs":
                observaciones = valor
            else:
                pendientes = valor
            texto_sig = None
            continue
        if a == "Observaciones":
            texto_sig = "obs"
            continue
        if a == "Pendientes por confirmar":
            texto_sig = "pend"
            continue
        m = re.match(r"^(\d+)\.\s*(.+)$", a)
        if m and b is None and c is None:
            actual = {"tipo": m.group(2).strip(), "criterios": [], "total": None, "global": None}
            etapas.append(actual)
            continue
        if actual is None or not a or a == "Criterio":
            continue
        if a.startswith("Puntaje / Porcentaje"):
            if _num(b) and _num(c):
                actual["total"] = (b, c)
        elif a.startswith("Puntaje global"):
            if _num(b):
                actual["global"] = b
        elif _num(b) and _num(c):
            actual["criterios"].append(f"{a}: {_fmt(b)}/{_fmt(c)}")
            actual.setdefault("detalle", []).append(
                {"criterio": a, "calificacion": b, "maximo": c})

    evaluacion = {"candidato": nombre, "puesto": puesto, "fecha_aplicacion": fecha,
                  "prueba": "Prueba de habilidades", "secciones": [], "observaciones": None, "pendientes": pendientes}
    for e in etapas:
        if e["total"] and e["criterios"]:
            evaluacion["secciones"].append({
                "seccion": e["tipo"], "criterios": e.get("detalle", []),
                "puntaje": e["total"][0], "maximo": e["total"][1],
                "porcentaje": round(e["total"][0] / e["total"][1], 4) if e["total"][1] else None})
        elif e["global"] is not None:
            evaluacion["secciones"].append({
                "seccion": e["tipo"], "criterios": [], "puntaje": e["global"], "maximo": 10,
                "porcentaje": round(e["global"] / 10, 4)})
    secciones = []
    for e in evaluacion["secciones"]:
        secciones.append(f"{e['seccion']}: {_fmt(e['puntaje'])}/{_fmt(e['maximo'])} "
                         f"({e['porcentaje'] * 100:.0f} %)")
    notas = []
    if observaciones:
        partes = [p for p in observaciones.split("\n\n")
                  if not p.strip().lower().startswith("si lo necesitas")]
        notas.append("Observaciones generales: " + "\n\n".join(partes).strip())
    if pendientes:
        notas.append(f"Pendiente por confirmar: {pendientes}")
    evaluacion["observaciones"] = notas[0] if observaciones else None
    pruebas = []
    if secciones:
        porcentajes = [e["porcentaje"] for e in evaluacion["secciones"]]
        promedio = sum(porcentajes) / len(porcentajes)
        evaluacion["promedio"] = round(promedio, 4)
        pruebas.append({
            "candidato": nombre, "puesto": puesto, "fecha": fecha,
            "tipo_prueba": "Prueba de habilidades", "puntaje": f"{promedio * 100:.1f} %",
            "observaciones": "\n".join(secciones + [""] * bool(notas) + notas) or None})
    return pruebas, evaluacion


def _valor(v):
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    if hasattr(v, "hour") and not isinstance(v, datetime):
        return v.strftime("%H:%M")
    if isinstance(v, str):
        v = v.replace("\xa0", " ").strip()
        return None if v in ("", "–") else v
    return v


def leer_instrucciones(libro):
    if "Instrucciones" not in libro.sheetnames:
        return None
    filas = [[_valor(c) for c in f] for f in libro["Instrucciones"].iter_rows(values_only=True)]
    filas = [f for f in filas if any(x is not None for x in f)]
    sal = {"titulo": filas[0][0], "descripcion": filas[1][0], "pasos": [], "hojas": [],
           "umbrales": {}, "notas": []}
    modo = None
    for f in filas[2:]:
        a, b = f[0], f[1]
        if a == "Cómo usarlo":
            modo = "pasos"
        elif a == "Hojas del libro":
            modo = "hojas"
        elif a in ("Leyenda de colores", "Criterios del grupo (editables)"):
            modo = "umbral" if a.startswith("Criterios") else "otro"
        elif modo == "pasos" and b:
            sal["pasos"].append(b)
        elif modo == "hojas" and b:
            sal["hojas"].append({"hoja": a, "descripcion": b})
        elif modo == "umbral" and _num(b):
            sal["umbrales"][a] = b
        elif modo == "umbral" and a and a.startswith("Supuesto"):
            sal["notas"].append(a)
    return sal


def leer_candidatos(libro):
    campos = ["no", "candidato", "puesto", "fecha_aplicacion", "telefono", "asistencia",
              "correo", "fuente", "ronda", "estado", "horario", "entrevista"]
    salida, vistos = [], {}
    for fila in libro["Candidatos"].iter_rows(min_row=6, max_col=12, values_only=True):
        d = dict(zip(campos, (_valor(c) for c in fila)))
        if not d["candidato"]:
            continue
        clave = d["candidato"].lower()
        d["repetido"] = clave in vistos
        vistos[clave] = True
        salida.append(d)
    return salida


def leer_criterios(libro):
    pruebas, actual = [], None
    for fila in libro["Criterios"].iter_rows(min_row=5, max_col=5, values_only=True):
        prueba, no, criterio, maximo, observa = (_valor(c) for c in fila)
        if prueba and not re.match(r"^\d+\. ", prueba):
            continue
        if prueba:
            actual = {"seccion": prueba, "se_observa": observa, "criterios": []}
            pruebas.append(actual)
        if actual and criterio and _num(maximo):
            actual["criterios"].append({"no": no, "criterio": criterio, "maximo": maximo})
    return pruebas


def leer_escala(libro):
    for fila in libro["Criterios"].iter_rows(min_row=5, max_col=1, values_only=True):
        if fila[0] and str(fila[0]).startswith("Escala de"):
            return _valor(fila[0])
    return None


def leer_ficha(libro):
    secciones, actual, campos = [], None, []
    for fila in libro["Ficha"].iter_rows(min_row=4, max_col=3, values_only=True):
        a = _valor(fila[0])
        if not a:
            continue
        if re.match(r"^\d+\. ", a):
            actual = {"seccion": a, "criterios": []}
            secciones.append(actual)
        elif a in ("Criterio", "Puntaje / Porcentaje"):
            continue
        elif a in ("Observaciones", "Pendientes por confirmar"):
            actual = None
            campos.append(a)
        elif actual is not None:
            actual["criterios"].append(a)
        elif a.startswith("Candidato") or a == "Puesto":
            campos.append(a.split(" (")[0])
    return {"campos": campos, "secciones": secciones,
            "nota": "La ficha se llena sola con la evaluación de cada candidato "
                    "(ver 'evaluaciones'); el ejemplo del libro se omite."}


def leer_matriz(libro):
    claves = ["no", "candidato", "puesto", "cv", "evaluacion_ventas", "llamada", "simulacion",
              "bitrix24", "excel", "evaluaciones_hechas", "promedio_disponible",
              "promedio_comparable", "ranking", "falta_registrar", "grupo", "recomendacion",
              "lectura"]
    salida = []
    for fila in libro["Matriz"].iter_rows(min_row=6, max_col=17, values_only=True):
        d = dict(zip(claves, (_valor(c) for c in fila)))
        if not d["candidato"]:
            continue
        if d["lectura"] and str(d["lectura"]).lower().startswith("ejemplo ficticio"):
            d["lectura"] = None
        salida.append(d)
    return salida


def main(ruta, salida):
    libro = openpyxl.load_workbook(ruta, data_only=True)
    todas, evaluaciones = [], []
    for hoja in libro.worksheets:
        if _es_hoja_de_persona(hoja):
            p, e = leer_hoja(libro, hoja)
            todas.extend(p)
            evaluaciones.append(e)
    contenido = {
        "origen": os.path.basename(ruta),
        "pruebas": todas,
        "candidatos": leer_candidatos(libro),
        "prueba_de_habilidades": {
            "descripcion": "Prueba única de habilidades; sus secciones son las de 'criterios'. "
                           "El flujo del proceso es: prueba de habilidades, pruebas "
                           "psicométricas y entrevista.",
            "secciones": [c["seccion"] for c in leer_criterios(libro)]},
        "criterios": leer_criterios(libro),
        "escala_calificacion": leer_escala(libro),
        "evaluaciones": evaluaciones,
        "ficha": leer_ficha(libro),
        "matriz": leer_matriz(libro),
        "instrucciones": leer_instrucciones(libro),
    }
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(contenido, f, ensure_ascii=False, indent=2)
    print(f"{len(todas)} pruebas, {len(contenido['candidatos'])} candidatos, "
          f"{len(contenido['criterios'])} secciones con criterios, "
          f"{len(evaluaciones)} evaluaciones, {len(contenido['matriz'])} filas de matriz "
          f"-> {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
