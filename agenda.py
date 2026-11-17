from datetime import date, timedelta

import logica

ASISTENCIAS = ["Pendiente", "Asistió", "No asistió"]


def tipo(etapa):
    return "Entrevista" if etapa == "Entrevista" else "Prueba"


def _fecha(registro):
    return logica.parsear_fecha(registro.get("fecha")) if registro.get("fecha") else None


def esta_atrasado(registro, hoy):
    f = _fecha(registro)
    return bool(f and f < hoy and registro.get("asistencia") != "Asistió")


def situacion(registro, hoy):
    if registro.get("asistencia") == "Asistió":
        return "Asistió"
    f = _fecha(registro)
    if not f:
        return "Sin fecha"
    if f < hoy:
        return "Atrasado"
    if f == hoy:
        return "Hoy"
    if f == hoy + timedelta(days=1):
        return "Mañana"
    return "Próximo"


def dias_atraso(registro, hoy):
    f = _fecha(registro)
    return (hoy - f).days if f and f < hoy else 0


def texto_dias(n):
    return f"{n} día" if n == 1 else f"{n} días"


def situacion_prueba(registro, hoy):
    if registro.get("fecha_prueba"):
        return "Realizada"
    f = _fecha(registro)
    if not f:
        return "Sin agendar"
    dif = (f - hoy).days
    if dif < 0:
        return f"Atrasada {texto_dias(-dif)}"
    if dif == 0:
        return "Hoy"
    if dif == 1:
        return "Mañana"
    return f"En {dif} días"


def elementos(embudo, pruebas):
    agendadas = {}
    for p in sorted(pruebas, key=lambda p: p["id"]):
        if not p.get("fecha_prueba") and p.get("tipo_prueba") in (None, "", "Prueba de habilidades"):
            agendadas[p["candidato"].strip().lower()] = p
    activos = []
    for r in embudo:
        if r["estado"] != "Activo":
            continue
        p = agendadas.get(r["nombre_completo"].strip().lower())
        if p and tipo(r["etapa"]) == "Prueba":
            r = dict(r, fecha=p["fecha"], asistencia="Pendiente")
        activos.append(r)
    en_embudo = {a["nombre_completo"].strip().lower() for a in activos
                 if tipo(a["etapa"]) == "Prueba"}
    telefonos = {}
    for r in embudo:
        if r.get("telefono"):
            telefonos.setdefault(r["nombre_completo"].strip().lower(), r["telefono"])
    for p in pruebas:
        nombre = p["candidato"].strip().lower()
        if p.get("fecha_prueba") or p.get("tipo_prueba") not in (None, "", "Prueba de habilidades") \
                or nombre in en_embudo:
            continue
        activos.append({"id": p["id"], "origen": "pruebas", "nombre_completo": p["candidato"],
                        "etapa": "Prueba de habilidades", "fecha": p["fecha"], "hora": None,
                        "telefono": telefonos.get(nombre), "asistencia": "Pendiente"})
    return activos


def _conteo(registros):
    return {"Prueba": sum(1 for r in registros if tipo(r["etapa"]) == "Prueba"),
            "Entrevista": sum(1 for r in registros if tipo(r["etapa"]) == "Entrevista")}


def resumen(activos, hoy=None):
    hoy = hoy or date.today()
    manana = hoy + timedelta(days=1)
    por_dia = {"hoy": [], "manana": []}
    por_venir, atrasados = [], []
    for r in activos:
        f = _fecha(r)
        if f == hoy:
            por_dia["hoy"].append(r)
        elif f == manana:
            por_dia["manana"].append(r)
        if esta_atrasado(r, hoy):
            atrasados.append(r)
        elif f and f >= hoy and r.get("asistencia") != "Asistió":
            por_venir.append(r)
    por_hora = lambda r: (r.get("hora") or "99:99", r["nombre_completo"])
    for lista in (por_dia["hoy"], por_dia["manana"]):
        lista.sort(key=por_hora)
    atrasados.sort(key=lambda r: (r["fecha"], por_hora(r)))
    return {"hoy": por_dia["hoy"], "manana": por_dia["manana"],
            "conteo_hoy": _conteo(por_dia["hoy"]), "conteo_manana": _conteo(por_dia["manana"]),
            "por_venir": _conteo(por_venir), "total_por_venir": len(por_venir),
            "atrasados": atrasados, "conteo_atrasados": _conteo(atrasados),
            "total_activos": len(activos)}
