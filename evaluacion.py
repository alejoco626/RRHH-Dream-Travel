import json

ESCALA = "0 = no cumple o no se observó · 1 = muy bajo · 2 = bajo · 3 = aceptable · " \
         "4 = bueno · 5 = excelente"

SECCIONES = [
    {"nombre": "1. Revisión del CV", "global": None, "criterios": [
        ("Experiencia laboral relacionada con ventas", 5),
        ("Experiencia en atención y servicio al cliente", 5),
        ("Experiencia en turismo, agencias de viajes, hoteles o áreas relacionadas", 5),
        ("Permanencia y estabilidad en empleos anteriores", 5),
        ("Formación académica", 5),
        ("Presentación, orden y claridad del CV", 5)]},
    {"nombre": "2. Evaluación de ventas", "global": None, "criterios": [
        ("Identifica las necesidades del cliente", 5),
        ("Realiza preguntas adecuadas", 5),
        ("Escucha y comprende al cliente", 5),
        ("Maneja correctamente las objeciones", 5),
        ("Presenta argumentos y beneficios", 5),
        ("Mantiene seguridad y control de la negociación", 5),
        ("Busca concretar el cierre de la venta", 5)]},
    {"nombre": "3. Llamada de venta",
     "global": "Puntaje global de la llamada (sobre 10) – cuando no hay detalle por criterio",
     "criterios": [
        ("Saludo y presentación profesional", 5),
        ("Genera confianza con el cliente", 5),
        ("Conoce y explica correctamente el paquete", 5),
        ("Explica beneficios de manera atractiva", 5),
        ("Comunicación, tono de voz y fluidez", 5),
        ("Manejo de preguntas y objeciones", 5),
        ("Capacidad para incentivar el cierre", 5)]},
    {"nombre": "4. Simulación de venta de viaje",
     "global": "Puntaje global de la simulación / video (sobre 10) – cuando no hay detalle "
               "por criterio",
     "criterios": [
        ("Identifica las necesidades y preferencias del cliente", 5),
        ("Realiza preguntas estratégicas para conocer lo que busca el cliente", 5),
        ("Presenta una propuesta de viaje acorde con las necesidades identificadas", 5),
        ("Argumenta el precio y explica la relación entre costo y beneficios", 5),
        ("Utiliza técnicas de persuasión para despertar el interés del cliente", 5),
        ("Responde con seguridad ante dudas, objeciones o solicitudes de información", 5),
        ("Propone un siguiente paso concreto para avanzar con la venta", 5)]},
    {"nombre": "5. Prueba de Bitrix24", "global": None, "criterios": [
        ("Crea la negociación (deal) correctamente, con su nombre y el teléfono "
         "proporcionado", 5),
        ("Sabe ubicar y utilizar la función de llamada de Bitrix para llamar al cliente", 5),
        ("Realiza la llamada al cliente con seguridad y de forma profesional", 5),
        ("Sigue las indicaciones que se le dan durante la prueba, sin necesidad de "
         "repetirlas", 5),
        ("Maneja la plataforma con fluidez (se desenvuelve sin ayuda constante)", 5)]},
    {"nombre": "6. Prueba de Excel", "global": None, "criterios": [
        ("Resultado de la prueba de Excel (sobre 10)", 10)]},
]


def vacio():
    return {"secciones": [
        {"nombre": s["nombre"], "global": None,
         "criterios": [{"criterio": c, "calificacion": None, "maximo": m}
                       for c, m in s["criterios"]]} for s in SECCIONES],
        "pendientes": ""}


def desde_texto(texto):
    base = vacio()
    try:
        guardada = json.loads(texto) if texto else {}
    except (TypeError, ValueError):
        guardada = {}
    previas = {s.get("nombre"): s for s in guardada.get("secciones", [])}
    for sec in base["secciones"]:
        previa = previas.get(sec["nombre"], {})
        sec["global"] = previa.get("global")
        notas = {c.get("criterio"): c.get("calificacion") for c in previa.get("criterios", [])}
        for c in sec["criterios"]:
            c["calificacion"] = notas.get(c["criterio"])
    base["pendientes"] = guardada.get("pendientes", "") or ""
    return base


def a_texto(detalle):
    return json.dumps(detalle, ensure_ascii=False)


def leer_nota(texto, maximo):
    t = (texto or "").strip().replace(",", ".")
    if not t:
        return None
    try:
        n = float(t)
    except ValueError:
        raise ValueError(f"«{texto}» no es un número.") from None
    if n < 0 or n > maximo:
        raise ValueError(f"La nota debe estar entre 0 y {maximo:g}.")
    return int(n) if n.is_integer() else n


def resultado(seccion):
    hechas = [c for c in seccion["criterios"] if c["calificacion"] is not None]
    if hechas:
        puntos = sum(c["calificacion"] for c in hechas)
        maximo = sum(c["maximo"] for c in hechas)
        return puntos, maximo, puntos / maximo
    if seccion.get("global") is not None:
        return seccion["global"], 10, seccion["global"] / 10
    return None


def promedio(detalle):
    fracciones = [r[2] for r in map(resultado, detalle["secciones"]) if r]
    return sum(fracciones) / len(fracciones) if fracciones else None


def texto_puntaje(detalle):
    p = promedio(detalle)
    return None if p is None else f"{p * 100:.1f} %"
