from datetime import date

TIPOS = ["Falta", "Permiso", "Incapacidad médica", "Llegada tarde", "Otro"]
ETAPAS = ["Reportada", "Justificada", "Injustificada", "Documento recibido", "Cerrada"]


def dias_de(inicio, fin):
    if not inicio:
        return None
    if not fin:
        return 1
    a, b = date.fromisoformat(inicio), date.fromisoformat(fin)
    return (b - a).days + 1 if b >= a else None


def embudo(registros):
    cuentas = {e: 0 for e in ETAPAS}
    otras = 0
    for r in registros:
        if r.get("etapa") in cuentas:
            cuentas[r["etapa"]] += 1
        else:
            otras += 1
    total = sum(cuentas.values()) + otras
    return {"etapas": [(e, cuentas[e]) for e in ETAPAS], "total": total,
            "abiertas": total - cuentas.get(ETAPAS[-1], 0)}


def siguiente(etapa):
    if etapa not in ETAPAS:
        return ETAPAS[0]
    i = ETAPAS.index(etapa)
    return ETAPAS[min(i + 1, len(ETAPAS) - 1)]
