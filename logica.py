import re
from datetime import date, datetime, timedelta

FORMATOS_ENTRADA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def parsear_fecha(texto):
    if isinstance(texto, datetime):
        return texto.date()
    if isinstance(texto, date):
        return texto
    texto = ("" if texto is None else str(texto)).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}[T ]", texto):
        texto = texto[:10]
    for formato in FORMATOS_ENTRADA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def a_iso(texto):
    d = parsear_fecha(texto)
    return d.isoformat() if d else None


def formatear(iso):
    d = parsear_fecha(iso)
    return d.strftime("%d/%m/%Y") if d else (iso or "")


def peso_dia(dia):
    semana = dia.weekday()
    return 1.0 if semana <= 4 else 0.5 if semana == 5 else 0.0


def dias_vacaciones(inicio, fin):
    inicio, fin = parsear_fecha(inicio), parsear_fecha(fin)
    if inicio is None or fin is None or fin < inicio:
        raise ValueError("Rango de fechas no válido")
    total = 0.0
    dia = inicio
    while dia <= fin:
        total += peso_dia(dia)
        dia += timedelta(days=1)
    return total


def leer_dias(texto):
    try:
        dias = float(str(texto).strip().replace(",", "."))
    except ValueError:
        raise ValueError("Escribe los días de vacaciones como número, por ejemplo 10.5.") from None
    if dias <= 0 or dias > 60 or (dias * 2) % 1:
        raise ValueError("Los días deben ser enteros o medios días (por ejemplo 10 o 10.5).")
    return dias


def fecha_fin_por_dias(inicio, dias):
    dia = parsear_fecha(inicio)
    if dia is None:
        raise ValueError("Fecha de inicio no válida")
    acumulado = 0.0
    for _ in range(400):
        acumulado += peso_dia(dia)
        if acumulado >= dias - 1e-9:
            return dia
        dia += timedelta(days=1)
    raise ValueError("No se pudo calcular la fecha final")


def fecha_regreso(fin):
    dia = parsear_fecha(fin)
    if dia is None:
        raise ValueError("Fecha no válida")
    dia += timedelta(days=1)
    while peso_dia(dia) == 0:
        dia += timedelta(days=1)
    return dia


def ultimo_dia_antes_de(regreso, inicio):
    dia, inicio = parsear_fecha(regreso), parsear_fecha(inicio)
    if dia is None or inicio is None:
        raise ValueError("Fecha no válida")
    dia -= timedelta(days=1)
    while dia >= inicio and peso_dia(dia) == 0:
        dia -= timedelta(days=1)
    if dia < inicio:
        raise ValueError("La fecha de regreso debe ser posterior al inicio")
    return dia


def texto_dias(dias):
    return f"{float(dias):g}"


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_cabecera(f):
    f = parsear_fecha(f)
    return f"{f.day:02d} de {MESES[f.month - 1]} {f.year}"


def fecha_larga(f):
    f = parsear_fecha(f)
    return f"{f.day} de {MESES[f.month - 1]} de {f.year}"


def fecha_amonestacion(f):
    f = parsear_fecha(f)
    return f"{f.day} {MESES[f.month - 1].capitalize()} {f.year}"


def texto_cantidad_dias(dias):
    return "1 día" if float(dias) == 1 else f"{texto_dias(dias)} días"


ORDINALES = {1: "primera", 2: "segunda", 3: "tercera", 4: "cuarta", 5: "quinta"}


def ordinal_vez(n):
    n = int(n)
    return ORDINALES.get(n, f"{n}.ª")


def _aniversario(ingreso, anio):
    try:
        return date(anio, ingreso.month, ingreso.day)
    except ValueError:
        return date(anio, 2, 28)


def periodo_vencido(ingreso, referencia):
    ingreso, referencia = parsear_fecha(ingreso), parsear_fecha(referencia)
    if ingreso is None or referencia is None:
        return None
    aniversario = _aniversario(ingreso, referencia.year)
    if aniversario > referencia:
        aniversario = _aniversario(ingreso, referencia.year - 1)
    inicio = _aniversario(ingreso, aniversario.year - 1)
    if inicio < ingreso:
        return None
    return inicio, aniversario - timedelta(days=1)


GRUPOS_AUTORIZACION = {
    "Supervisiones": ["JACKELINE ACEYTUNO", "MAGDALENA"],
    "Personal administrativo": ["JACKELINE ACEYTUNO", "MAGDALENA"],
    "Ventas – Senior": ["DEBI"],
    "Ventas – Junior": ["JACKELINE ACEYTUNO"],
    "Reservas": ["KARLA BETANCOURTH"],
    "Asistencia al viajero y visas": ["MELANIE"],
    "Procesos y control de calidad": ["JACKELINE ACEYTUNO"],
    "Recursos humanos": ["JACKELINE ACEYTUNO"],
}


def autorizadores(grupo):
    return GRUPOS_AUTORIZACION.get(grupo, [])


def proximo_cumpleanos(nacimiento, hoy=None):
    nacimiento = parsear_fecha(nacimiento)
    if nacimiento is None:
        return None
    hoy = hoy or date.today()
    proximo = _aniversario(nacimiento, hoy.year)
    if proximo < hoy:
        proximo = _aniversario(nacimiento, hoy.year + 1)
    return proximo, (proximo - hoy).days


def parsear_hora(texto):
    if texto is None:
        return None
    if hasattr(texto, "hour"):
        return f"{texto.hour:02d}:{texto.minute:02d}"
    t = re.sub(r"[.\s]", "", str(texto).lower())
    m = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?(?::\d{2})?(am|pm|a|p)?", t)
    if not m:
        return None
    hora, minuto, sufijo = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if sufijo and sufijo[0] == "p" and hora < 12:
        hora += 12
    elif sufijo and sufijo[0] == "a" and hora == 12:
        hora = 0
    if hora > 23 or minuto > 59:
        return None
    return f"{hora:02d}:{minuto:02d}"


def formatear_hora(valor):
    h = parsear_hora(valor)
    if not h:
        return ""
    hora, minuto = int(h[:2]), h[3:]
    return f"{(hora % 12) or 12}:{minuto} {'AM' if hora < 12 else 'PM'}"


def formatear_fecha_escrita(texto, cursor, tecleado=""):
    digitos = "".join(c for c in texto if c.isdigit())[:8]
    antes = min(sum(c.isdigit() for c in texto[:cursor]), len(digitos))
    al_final = cursor >= len(texto.rstrip("/")) and antes == len(digitos)
    if tecleado == "/" and al_final and len(digitos) in (1, 3):
        digitos = digitos[:-1] + "0" + digitos[-1]
        antes = len(digitos)
    nuevo = "/".join(p for p in (digitos[:2], digitos[2:4], digitos[4:]) if p)
    posicion = antes + (antes > 2) + (antes > 4)
    if al_final and len(digitos) in (2, 4) and (tecleado.isdigit() or tecleado == "/"):
        nuevo += "/"
        posicion = len(nuevo)
    return nuevo, posicion
