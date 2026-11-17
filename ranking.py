import re

PLAZAS = ["Asistencia al viajero", "Diseñador de viajes", "Reservas", "Recursos Humanos",
          "Control de Calidad"]
PUESTOS = ["Asesor de ventas", "Agente de reservas", "Gestor de visas",
           "Asistente al viajero", "Analista de calidad", "Reclutador"]
SIN_PLAZA = "Sin plaza"


def nota(texto):
    m = re.search(r"\d+(?:[.,]\d+)?", str(texto or ""))
    return float(m.group().replace(",", ".")) if m else None


def _clave(nombre):
    return (nombre or "").strip().lower()


def clasificar(embudo, pruebas, entrevistas, plaza=None, incluir_descartados=False):
    gente = {}

    def ficha(nombre):
        return gente.setdefault(_clave(nombre), {
            "candidato": (nombre or "").strip(), "plaza": "", "nota": None, "etapa": "",
            "entrevista": "", "descartado": False, "_id_nota": -1})

    for r in sorted(embudo, key=lambda r: (r["estado"] != "Activo", -r["id"])):
        f = ficha(r["nombre_completo"])
        if f["etapa"]:
            continue
        f["etapa"] = "No aprobado" if r["estado"] == "No aprobado" else r["etapa"]
        f["descartado"] = r["estado"] == "No aprobado"
        f["plaza"] = r.get("plaza") or ""
    for p in sorted(pruebas, key=lambda p: p["id"]):
        f = ficha(p["candidato"])
        if p.get("puesto") and not f["plaza"]:
            f["plaza"] = p["puesto"]
        if p.get("tipo_prueba") in (None, "", "Prueba de habilidades") and p.get("fecha_prueba"):
            valor = nota(p.get("puntaje"))
            if valor is not None and p["id"] > f["_id_nota"]:
                f["nota"], f["_id_nota"] = valor, p["id"]
            if not f["etapa"]:
                f["etapa"] = "Prueba realizada"
    for e in sorted(entrevistas, key=lambda e: e["id"]):
        f = ficha(e["candidato"])
        if e.get("puesto") and not f["plaza"]:
            f["plaza"] = e["puesto"]
        if e.get("resultado"):
            f["entrevista"] = e["resultado"]
        if not f["etapa"]:
            f["etapa"] = "Entrevista realizada"
    filas = []
    for f in gente.values():
        f["plaza"] = f["plaza"] or SIN_PLAZA
        if f["descartado"] and not incluir_descartados:
            continue
        if plaza and f["plaza"] != plaza:
            continue
        filas.append(f)
    filas.sort(key=lambda f: (f["nota"] is None, -(f["nota"] or 0), f["candidato"].lower()))
    for i, f in enumerate(filas, start=1):
        f["posicion"] = i
    return filas


def mejores_por_plaza(embudo, pruebas, entrevistas):
    filas = clasificar(embudo, pruebas, entrevistas)
    resultado = {}
    for plaza in PLAZAS:
        de_plaza = [f for f in filas if f["plaza"] == plaza]
        con_nota = [f for f in de_plaza if f["nota"] is not None]
        resultado[plaza] = {"mejor": con_nota[0] if con_nota else None,
                            "candidatos": len(de_plaza)}
    return resultado
