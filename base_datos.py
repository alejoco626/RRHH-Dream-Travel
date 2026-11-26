import os
from datetime import date
import shutil
import sqlite3
import sys
import time


def _carpeta_base():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _carpeta_datos():
    if os.environ.get("RRHH_DATOS"):
        return os.environ["RRHH_DATOS"]
    junto = os.path.join(_carpeta_base(), "datos")
    if getattr(sys, "frozen", False) and sys.platform == "win32" and not os.path.isdir(junto):
        raiz = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(raiz, "RRHH Dream & Travel", "datos")
    return junto


CARPETA_DATOS = _carpeta_datos()
CARPETA_ARCHIVOS = os.path.join(CARPETA_DATOS, "archivos")
RUTA_DB = os.path.join(CARPETA_DATOS, "rrhh.db")

COLUMNAS = {
    "empleados": ["nombre_completo", "puesto", "departamento", "fecha_ingreso",
                  "fecha_cumpleanos", "correo", "grupo"],
    "pruebas": ["candidato", "puesto", "fecha", "fecha_prueba", "tipo_prueba", "puntaje",
                "observaciones", "archivo", "detalle"],
    "entrevistas": ["candidato", "telefono", "puesto", "fecha", "hora", "entrevistador",
                    "resultado", "observaciones", "archivo"],
    "amonestaciones": ["empleado_id", "fecha", "numero_vez", "falta", "aspecto",
                       "detalle", "firmante", "cargo_firmante", "archivo"],
    "vacaciones": ["empleado_id", "folio", "fecha_solicitud", "fecha_inicio",
                   "fecha_fin", "dias", "periodo_desde", "periodo_hasta",
                   "autoriza", "fecha_constancia", "observaciones",
                   "archivo_solicitud", "archivo_constancia"],
    "memos": ["empleado_id", "fecha", "tema", "emisor", "observaciones", "archivo"],
    "ausencias": ["empleado_id", "tipo", "fecha", "fecha_fin", "dias", "motivo", "etapa",
                  "fecha_cierre", "archivo"],
    "embudo": ["nombre_completo", "telefono", "plaza", "etapa", "fecha", "hora", "estado",
               "motivo", "fecha_descarte", "notas", "asistencia"],
    "candidatos": ["nombre", "puesto", "fecha_aplicacion", "telefono", "asistencia", "correo",
                   "fuente", "ronda", "estado", "fecha_prueba", "horario_prueba",
                   "fecha_entrevista", "hora_entrevista", "observaciones", "pendientes",
                   "evaluacion", "recomendacion", "lectura", "motivo", "convocatoria"],
    "historial": ["candidato_id", "tipo", "fecha", "hora", "detalle"],
    "programacion": ["fecha_inicio", "fecha_fin", "actividad", "fase", "responsable", "estado",
                     "reporte", "notas", "convocatoria"],
}
CON_EMPLEADO = ("amonestaciones", "vacaciones", "memos", "ausencias")
VERSION_ESQUEMA = 11
CATEGORIAS_ADJUNTO = ["CV", "Prueba de Excel", "Otro"]
EXT_ADJUNTOS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".xlsm")

TPL_EMPLEADOS = """
CREATE TABLE {nombre} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    puesto TEXT NOT NULL,
    departamento TEXT NOT NULL,
    fecha_ingreso TEXT,
    fecha_cumpleanos TEXT,
    correo TEXT,
    grupo TEXT
);"""

TPL_VACACIONES = """
CREATE TABLE {nombre} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    folio TEXT,
    fecha_solicitud TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    dias REAL NOT NULL,
    periodo_desde TEXT NOT NULL,
    periodo_hasta TEXT NOT NULL,
    autoriza TEXT,
    fecha_constancia TEXT,
    observaciones TEXT,
    archivo_solicitud TEXT,
    archivo_constancia TEXT
);"""

ESQUEMA = (
    TPL_EMPLEADOS.format(nombre="IF NOT EXISTS empleados") + TPL_VACACIONES.format(
        nombre="IF NOT EXISTS vacaciones") + """
CREATE TABLE IF NOT EXISTS candidatos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    puesto TEXT,
    fecha_aplicacion TEXT,
    telefono TEXT,
    asistencia TEXT NOT NULL DEFAULT 'Sin contactar',
    correo TEXT,
    fuente TEXT,
    ronda TEXT DEFAULT 'Primera',
    estado TEXT NOT NULL DEFAULT 'Nuevo',
    fecha_prueba TEXT,
    horario_prueba TEXT,
    fecha_entrevista TEXT,
    hora_entrevista TEXT,
    observaciones TEXT,
    pendientes TEXT,
    evaluacion TEXT,
    recomendacion TEXT,
    lectura TEXT,
    motivo TEXT,
    convocatoria TEXT
);
CREATE INDEX IF NOT EXISTS ix_candidatos_estado ON candidatos(estado);
CREATE TABLE IF NOT EXISTS historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidato_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    fecha TEXT,
    hora TEXT,
    detalle TEXT
);
CREATE INDEX IF NOT EXISTS ix_historial_candidato ON historial(candidato_id);
CREATE TABLE IF NOT EXISTS programacion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    actividad TEXT NOT NULL,
    fase TEXT,
    responsable TEXT,
    estado TEXT NOT NULL DEFAULT 'Sin reporte',
    reporte TEXT,
    notas TEXT,
    convocatoria TEXT
);
CREATE INDEX IF NOT EXISTS ix_programacion_fecha ON programacion(fecha_inicio);
CREATE TABLE IF NOT EXISTS pruebas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidato TEXT NOT NULL,
    puesto TEXT,
    fecha TEXT NOT NULL,
    fecha_prueba TEXT,
    tipo_prueba TEXT,
    puntaje TEXT,
    observaciones TEXT,
    archivo TEXT,
    detalle TEXT
);
CREATE TABLE IF NOT EXISTS entrevistas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidato TEXT NOT NULL,
    telefono TEXT,
    puesto TEXT,
    fecha TEXT NOT NULL,
    hora TEXT,
    entrevistador TEXT,
    resultado TEXT,
    observaciones TEXT,
    archivo TEXT
);
CREATE TABLE IF NOT EXISTS amonestaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    fecha TEXT NOT NULL,
    numero_vez INTEGER NOT NULL DEFAULT 1,
    falta TEXT NOT NULL,
    aspecto TEXT,
    detalle TEXT,
    firmante TEXT,
    cargo_firmante TEXT,
    archivo TEXT
);
CREATE TABLE IF NOT EXISTS memos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    fecha TEXT NOT NULL,
    tema TEXT NOT NULL,
    emisor TEXT,
    observaciones TEXT,
    archivo TEXT
);
CREATE TABLE IF NOT EXISTS ausencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id INTEGER NOT NULL REFERENCES empleados(id),
    tipo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    fecha_fin TEXT,
    dias REAL,
    motivo TEXT,
    etapa TEXT NOT NULL DEFAULT 'Reportada',
    fecha_cierre TEXT,
    archivo TEXT
);
CREATE TABLE IF NOT EXISTS embudo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    telefono TEXT,
    plaza TEXT,
    etapa TEXT NOT NULL DEFAULT 'Prueba de habilidades',
    fecha TEXT,
    hora TEXT,
    estado TEXT NOT NULL DEFAULT 'Activo',
    motivo TEXT,
    fecha_descarte TEXT,
    notas TEXT,
    asistencia TEXT NOT NULL DEFAULT 'Pendiente'
);
CREATE TABLE IF NOT EXISTS adjuntos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tabla TEXT NOT NULL,
    registro_id INTEGER NOT NULL,
    archivo TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'Otro',
    fecha_subida TEXT
);
CREATE TABLE IF NOT EXISTS config (
    clave TEXT PRIMARY KEY,
    valor TEXT
);
""")


def _conectar():
    os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)
    con = sqlite3.connect(RUTA_DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def _ejecutar(sql, params=()):
    con = _conectar()
    try:
        with con:
            cur = con.execute(sql, params)
        return cur.lastrowid
    finally:
        con.close()


def _consultar(sql, params=()):
    con = _conectar()
    try:
        return [dict(f) for f in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def _validar_tabla(tabla):
    if tabla not in COLUMNAS:
        raise ValueError(f"Tabla desconocida: {tabla}")


def _migrar_a_v2(con):
    def columnas(tabla):
        return [r["name"] for r in con.execute(f"PRAGMA table_info({tabla})")]

    def existe(tabla):
        return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                           (tabla,)).fetchone() is not None

    con.execute("PRAGMA foreign_keys = OFF")
    partes = ["BEGIN;"]
    comunes = [c for c in ["id"] + COLUMNAS["empleados"] if c in columnas("empleados")]
    lista = ", ".join(comunes)
    partes += [TPL_EMPLEADOS.format(nombre="empleados_nuevo"),
               f"INSERT INTO empleados_nuevo ({lista}) SELECT {lista} FROM empleados;",
               "DROP TABLE empleados;", "ALTER TABLE empleados_nuevo RENAME TO empleados;"]
    if existe("vacaciones"):
        viejas = columnas("vacaciones")
        comunes = [c for c in ["id"] + COLUMNAS["vacaciones"] if c in viejas]
        destino, origen = list(comunes), list(comunes)
        if "archivo" in viejas:
            destino.append("archivo_solicitud")
            origen.append("archivo")
        partes += [TPL_VACACIONES.format(nombre="vacaciones_nueva"),
                   f"INSERT INTO vacaciones_nueva ({', '.join(destino)}) "
                   f"SELECT {', '.join(origen)} FROM vacaciones;",
                   "DROP TABLE vacaciones;",
                   "ALTER TABLE vacaciones_nueva RENAME TO vacaciones;"]
    partes.append("COMMIT;")
    con.executescript("\n".join(partes))
    con.execute("PRAGMA foreign_keys = ON")


def crear_tablas():
    os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)
    con = _conectar()
    try:
        version = con.execute("PRAGMA user_version").fetchone()[0]
        hay_empleados = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='empleados'").fetchone()
        if hay_empleados and version < VERSION_ESQUEMA:
            shutil.copy2(RUTA_DB, f"{RUTA_DB}.v{version}.respaldo")
            if version < 2:
                _migrar_a_v2(con)
        with con:
            con.executescript(ESQUEMA)
            if version < 8 and "plaza" not in [
                    r["name"] for r in con.execute("PRAGMA table_info(embudo)")]:
                con.execute("ALTER TABLE embudo ADD COLUMN plaza TEXT")
            if version < 7 and "fecha_prueba" not in [
                    r["name"] for r in con.execute("PRAGMA table_info(pruebas)")]:
                con.execute("ALTER TABLE pruebas ADD COLUMN fecha_prueba TEXT")
                con.execute("UPDATE pruebas SET fecha_prueba = fecha "
                            "WHERE puntaje IS NOT NULL AND puntaje != ''")
            if version < 6 and "asistencia" not in [
                    r["name"] for r in con.execute("PRAGMA table_info(embudo)")]:
                con.execute("ALTER TABLE embudo ADD COLUMN asistencia TEXT NOT NULL "
                            "DEFAULT 'Pendiente'")
            if version < 5:
                for tabla, columna in (("pruebas", "detalle"), ("entrevistas", "telefono"),
                                       ("entrevistas", "hora")):
                    if columna not in [r["name"] for r in
                                       con.execute(f"PRAGMA table_info({tabla})")]:
                        con.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} TEXT")
            if version < 4:
                for t in ("pruebas", "entrevistas"):
                    for r in con.execute(f"SELECT id, archivo FROM {t} "
                                         f"WHERE archivo IS NOT NULL AND archivo != ''").fetchall():
                        con.execute(
                            "INSERT INTO adjuntos (tabla, registro_id, archivo, categoria, "
                            "fecha_subida) VALUES (?, ?, ?, 'Otro', date('now'))",
                            (t, r["id"], r["archivo"]))
        con.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")
    finally:
        con.close()


def listar(tabla, filtro=""):
    _validar_tabla(tabla)
    if tabla in CON_EMPLEADO:
        sql = (f"SELECT t.*, e.nombre_completo AS empleado FROM {tabla} t "
               f"LEFT JOIN empleados e ON e.id = t.empleado_id ORDER BY t.id DESC")
    else:
        sql = f"SELECT * FROM {tabla} ORDER BY id DESC"
    filas = _consultar(sql)
    filtro = (filtro or "").strip().lower()
    if filtro:
        filas = [f for f in filas
                 if any(filtro in str(v).lower() for v in f.values() if v is not None)]
    return filas


def guardar(tabla, datos, id_registro=None):
    _validar_tabla(tabla)
    columnas = [c for c in COLUMNAS[tabla] if c in datos]
    valores = [datos[c] for c in columnas]
    if id_registro is None:
        marcas = ", ".join("?" for _ in columnas)
        return _ejecutar(
            f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({marcas})", valores)
    asignaciones = ", ".join(f"{c} = ?" for c in columnas)
    _ejecutar(f"UPDATE {tabla} SET {asignaciones} WHERE id = ?", valores + [id_registro])
    return id_registro


def insertar_varios(tabla, lista):
    _validar_tabla(tabla)
    if not lista:
        return 0
    columnas = [c for c in COLUMNAS[tabla] if any(c in d for d in lista)]
    sql = (f"INSERT INTO {tabla} ({', '.join(columnas)}) "
           f"VALUES ({', '.join('?' for _ in columnas)})")
    con = _conectar()
    try:
        with con:
            con.executemany(sql, [[d.get(c) for c in columnas] for d in lista])
    finally:
        con.close()
    return len(lista)


def eliminar(tabla, id_registro):
    _validar_tabla(tabla)
    _ejecutar(f"DELETE FROM {tabla} WHERE id = ?", (id_registro,))
    if tabla == "candidatos":
        _ejecutar("DELETE FROM historial WHERE candidato_id = ?", (id_registro,))
    _ejecutar("DELETE FROM adjuntos WHERE tabla = ? AND registro_id = ?", (tabla, id_registro))


TIPOS_HISTORIAL = ("prueba", "entrevista", "postulacion")


def historial_de(candidato_id):
    """Lo que se fue reagendando o postulando antes, del más antiguo al más reciente."""
    return _consultar("SELECT * FROM historial WHERE candidato_id = ? ORDER BY id", (candidato_id,))


def agregar_historial(candidato_id, tipo, fecha=None, hora=None, detalle=""):
    if tipo not in TIPOS_HISTORIAL:
        raise ValueError("Tipo de historial no válido.")
    return _ejecutar("INSERT INTO historial (candidato_id, tipo, fecha, hora, detalle) "
                     "VALUES (?, ?, ?, ?, ?)", (candidato_id, tipo, fecha or "", hora or "",
                                                 detalle or ""))


def contar_reagendas():
    """{candidato_id: (reagendas de prueba, reagendas de entrevista)}."""
    cuentas = {}
    for f in _consultar("SELECT candidato_id, tipo, COUNT(*) AS n FROM historial "
                        "WHERE tipo IN ('prueba', 'entrevista') GROUP BY candidato_id, tipo"):
        p, e = cuentas.get(f["candidato_id"], (0, 0))
        cuentas[f["candidato_id"]] = (p + f["n"], e) if f["tipo"] == "prueba" else (p, e + f["n"])
    return cuentas


def adjuntos_de(tabla, id_registro):
    return _consultar("SELECT * FROM adjuntos WHERE tabla = ? AND registro_id = ? ORDER BY id",
                      (tabla, id_registro))


def agregar_adjunto(tabla, id_registro, archivo, categoria="Otro"):
    return _ejecutar(
        "INSERT INTO adjuntos (tabla, registro_id, archivo, categoria, fecha_subida) "
        "VALUES (?, ?, ?, ?, date('now'))", (tabla, id_registro, archivo, categoria))


def quitar_adjunto(id_adjunto):
    _ejecutar("DELETE FROM adjuntos WHERE id = ?", (id_adjunto,))


def embudo_de(nombre):
    clave = (nombre or "").strip().lower()
    filas = [r for r in listar("embudo") if r["nombre_completo"].strip().lower() == clave]
    filas.sort(key=lambda r: r["estado"] != "Activo")
    return filas[0] if filas else None


def confirmar_asistencia(nombre, entrevista):
    clave = (nombre or "").strip().lower()
    for r in listar("embudo"):
        if (r["estado"] == "Activo" and r["nombre_completo"].strip().lower() == clave
                and (r["etapa"] == "Entrevista") == entrevista):
            guardar("embudo", {"asistencia": "Asistió"}, r["id"])


def descartar_candidato(nombre, etapa, motivo=None, telefono=None):
    r = embudo_de(nombre)
    cambios = {"estado": "No aprobado", "motivo": motivo or None,
               "fecha_descarte": date.today().isoformat(), "etapa": etapa}
    if r:
        return guardar("embudo", cambios, r["id"])
    cambios.update(nombre_completo=nombre.strip(), telefono=telefono or None)
    return guardar("embudo", cambios)


def reagendar_prueba(nombre, fecha):
    clave = (nombre or "").strip().lower()
    for r in listar("embudo"):
        if (r["estado"] == "Activo" and r["etapa"] != "Entrevista"
                and r["nombre_completo"].strip().lower() == clave):
            guardar("embudo", {"fecha": fecha, "asistencia": "Pendiente"}, r["id"])


def pasar_a_entrevista(nombre, telefono=None):
    cambios = {"etapa": "Entrevista", "estado": "Activo", "asistencia": "Pendiente",
               "fecha": None, "hora": None, "motivo": None, "fecha_descarte": None}
    r = embudo_de(nombre)
    if r:
        return guardar("embudo", cambios, r["id"])
    cambios.update(nombre_completo=nombre.strip(), telefono=telefono or None)
    return guardar("embudo", cambios)


def conteo_adjuntos(tabla):
    return {r["registro_id"]: r["n"] for r in _consultar(
        "SELECT registro_id, COUNT(*) AS n FROM adjuntos WHERE tabla = ? GROUP BY registro_id",
        (tabla,))}


def obtener(tabla, id_registro):
    _validar_tabla(tabla)
    for fila in listar(tabla):
        if fila["id"] == id_registro:
            return fila
    return None


def siguiente_folio(anio):
    filas = _consultar("SELECT folio FROM vacaciones WHERE folio LIKE ?", (f"{anio}-%",))
    numeros = []
    for f in filas:
        try:
            numeros.append(int(f["folio"].split("-")[1]))
        except (ValueError, IndexError, AttributeError):
            pass
    return f"{anio}-{(max(numeros) if numeros else 0) + 1:04d}"


def empleados_basico():
    return [(f["id"], f["nombre_completo"]) for f in
            _consultar("SELECT id, nombre_completo FROM empleados ORDER BY nombre_completo")]


def pendientes():
    reglas = (
        ("pruebas", "Pruebas", (("archivo", "Falta subir el CV o archivos"),)),
        ("entrevistas", "Entrevistas", (("archivo", "Falta subir el CV o archivos"),)),
        ("amonestaciones", "Amonestaciones", (("archivo", "Falta la carta firmada"),)),
        ("vacaciones", "Vacaciones", (("archivo_solicitud", "Falta la solicitud firmada"),
                                      ("archivo_constancia", "Falta la constancia firmada"))),
        ("memos", "Memorándums", (("archivo", "Falta el memo firmado"),)),
    )
    resultado = []
    for tabla, etiqueta, requisitos in reglas:
        con_archivos = conteo_adjuntos(tabla) if tabla in ("pruebas", "entrevistas") else {}
        for fila in listar(tabla):
            referencia = fila.get("candidato") or fila.get("empleado") or ""
            if tabla == "vacaciones" and fila.get("folio"):
                referencia = f"{referencia} ({fila['folio']})"
            fecha = fila.get("fecha") or fila.get("fecha_inicio") or ""
            for campo, falta in requisitos:
                if tabla in ("pruebas", "entrevistas"):
                    falta_archivo = not con_archivos.get(fila["id"])
                else:
                    falta_archivo = not fila.get(campo)
                if falta_archivo:
                    resultado.append({"tabla": tabla, "modulo": etiqueta, "id": fila["id"],
                                      "referencia": referencia, "fecha": fecha,
                                      "falta": falta})
    return resultado


def copiar_archivo(origen):
    os.makedirs(CARPETA_ARCHIVOS, exist_ok=True)
    nombre = f"{int(time.time())}_{os.path.basename(origen)}"
    shutil.copy2(origen, os.path.join(CARPETA_ARCHIVOS, nombre))
    return nombre


def ruta_archivo(nombre):
    return os.path.join(CARPETA_ARCHIVOS, nombre)


_RENOMBRABLES = {("embudo", "plaza"), ("pruebas", "puesto"), ("entrevistas", "puesto"),
                 ("empleados", "departamento"), ("empleados", "grupo"), ("empleados", "puesto"), ("memos", "tema"), ("ausencias", "tipo"), ("ausencias", "etapa"),
                 ("adjuntos", "categoria"), ("candidatos", "fuente"), ("candidatos", "puesto"), ("programacion", "responsable")}


def renombrar_valor(tabla, columna, viejo, nuevo):
    if (tabla, columna) not in _RENOMBRABLES:
        raise ValueError("Columna no permitida.")
    _ejecutar(f"UPDATE {tabla} SET {columna} = ? WHERE {columna} = ?", (nuevo, viejo))


def renombrar_plaza(viejo, nuevo):
    for tabla, columna in (("embudo", "plaza"), ("pruebas", "puesto"), ("entrevistas", "puesto")):
        renombrar_valor(tabla, columna, viejo, nuevo)


def leer_config(clave, defecto=None):
    filas = _consultar("SELECT valor FROM config WHERE clave = ?", (clave,))
    return filas[0]["valor"] if filas else defecto


def guardar_config(clave, valor):
    _ejecutar("INSERT INTO config (clave, valor) VALUES (?, ?) "
              "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor", (clave, valor))
