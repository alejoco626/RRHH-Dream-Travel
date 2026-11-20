import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime

import base_datos as bd
import version

PREFIJO_AUTO = "RRHH_auto_"
PREFIJO_MANUAL = "RRHH_respaldo_"
PREFIJO_SEGURIDAD = "RRHH_antes_de_restaurar_"
CONSERVAR_AUTO = 15
CONSERVAR_SEGURIDAD = 5
HORAS_ENTRE_AUTO = 8
CLAVE_EXTERNA = "carpeta_respaldo_externa"

NOMBRES = {
    "empleados": "Empleados", "amonestaciones": "Amonestaciones", "vacaciones": "Vacaciones",
    "memos": "Memorándums", "ausencias": "Ausencias", "embudo": "Candidatos (embudo)",
    "pruebas": "Pruebas", "entrevistas": "Entrevistas", "adjuntos": "Archivos de candidatos",
}


def carpeta_respaldos():
    return os.path.join(bd.CARPETA_DATOS, "respaldos")


def nombre_nuevo(prefijo):
    return f"{prefijo}{datetime.now():%Y-%m-%d_%H%M%S}.zip"


def verificar_archivo(ruta):
    resultado = {"ok": False, "integridad": "", "claves": [], "tablas": {}, "error": ""}
    if not os.path.exists(ruta):
        resultado["error"] = "No existe el archivo de la base de datos."
        return resultado
    try:
        con = sqlite3.connect(ruta)
        try:
            con.execute("PRAGMA query_only = ON")
            integridad = [f[0] for f in con.execute("PRAGMA integrity_check").fetchall()]
            resultado["integridad"] = "; ".join(integridad)
            resultado["claves"] = [tuple(f) for f in con.execute("PRAGMA foreign_key_check")]
            existentes = {f[0] for f in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for tabla in list(bd.COLUMNAS) + ["adjuntos"]:
                if tabla in existentes:
                    resultado["tablas"][tabla] = con.execute(
                        f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            resultado["esquema"] = con.execute("PRAGMA user_version").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as e:
        resultado["error"] = str(e)
        return resultado
    resultado["ok"] = integridad == ["ok"] and not resultado["claves"]
    if not resultado["ok"] and not resultado["error"]:
        resultado["error"] = resultado["integridad"] if integridad != ["ok"] else \
            "Hay registros enlazados a empleados que ya no existen."
    return resultado


def verificar():
    estado = verificar_archivo(bd.RUTA_DB)
    estado["tamano"] = os.path.getsize(bd.RUTA_DB) if os.path.exists(bd.RUTA_DB) else 0
    estado["adjuntos"], estado["tamano_adjuntos"] = _contar_archivos(bd.CARPETA_ARCHIVOS)
    return estado


def _contar_archivos(carpeta):
    cantidad = peso = 0
    for raiz, _, archivos in os.walk(carpeta):
        for a in archivos:
            cantidad += 1
            peso += os.path.getsize(os.path.join(raiz, a))
    return cantidad, peso


def _sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def crear_respaldo(ruta_zip):
    os.makedirs(os.path.dirname(os.path.abspath(ruta_zip)), exist_ok=True)
    temporal = tempfile.mkdtemp(prefix="rrhh_resp_")
    try:
        copia = os.path.join(temporal, "rrhh.db")
        origen = sqlite3.connect(bd.RUTA_DB)
        destino = sqlite3.connect(copia)
        try:
            origen.backup(destino)
        finally:
            destino.close()
            origen.close()
        estado = verificar_archivo(copia)
        adjuntos, _ = _contar_archivos(bd.CARPETA_ARCHIVOS)
        manifiesto = {"app": version.VERSION, "esquema": bd.VERSION_ESQUEMA,
                      "creado": datetime.now().isoformat(timespec="seconds"),
                      "sha256_db": _sha256(copia), "integridad_ok": estado["ok"],
                      "tablas": estado["tablas"], "adjuntos": adjuntos}
        parcial = ruta_zip + ".parcial"
        with zipfile.ZipFile(parcial, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(copia, "rrhh.db")
            z.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False, indent=1))
            for raiz, _, archivos in os.walk(bd.CARPETA_ARCHIVOS):
                for a in archivos:
                    completo = os.path.join(raiz, a)
                    relativo = os.path.relpath(completo, bd.CARPETA_ARCHIVOS).replace(os.sep, "/")
                    z.write(completo, f"archivos/{relativo}")
        os.replace(parcial, ruta_zip)
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
    return {"ruta": ruta_zip, "ok": estado["ok"], "tablas": estado["tablas"],
            "adjuntos": adjuntos, "tamano": os.path.getsize(ruta_zip), "error": estado["error"]}


def rotar(prefijo, conservar):
    carpeta = carpeta_respaldos()
    if not os.path.isdir(carpeta):
        return
    viejos = sorted((f for f in os.listdir(carpeta)
                     if f.startswith(prefijo) and f.endswith(".zip")), reverse=True)[conservar:]
    for f in viejos:
        try:
            os.remove(os.path.join(carpeta, f))
        except OSError:
            pass


def listar_respaldos():
    carpeta = carpeta_respaldos()
    filas = []
    if os.path.isdir(carpeta):
        for f in os.listdir(carpeta):
            if not f.endswith(".zip"):
                continue
            tipo = ("Automático" if f.startswith(PREFIJO_AUTO) else
                    "Antes de restaurar" if f.startswith(PREFIJO_SEGURIDAD) else "Manual")
            ruta = os.path.join(carpeta, f)
            filas.append({"ruta": ruta, "nombre": f, "tipo": tipo,
                          "fecha": datetime.fromtimestamp(os.path.getmtime(ruta)),
                          "tamano": os.path.getsize(ruta)})
    return sorted(filas, key=lambda r: r["fecha"], reverse=True)


def ultimo_automatico():
    return next((r for r in listar_respaldos() if r["tipo"] == "Automático"), None)


def copiar_externo(ruta_zip):
    destino = bd.leer_config(CLAVE_EXTERNA, "") if os.path.exists(bd.RUTA_DB) else ""
    if not destino:
        return None
    try:
        os.makedirs(destino, exist_ok=True)
        shutil.copy2(ruta_zip, os.path.join(destino, os.path.basename(ruta_zip)))
        return True
    except OSError:
        return False


def respaldo_automatico(horas=HORAS_ENTRE_AUTO):
    ultimo = ultimo_automatico()
    if ultimo and (datetime.now() - ultimo["fecha"]).total_seconds() < horas * 3600:
        return None
    ruta = os.path.join(carpeta_respaldos(), nombre_nuevo(PREFIJO_AUTO))
    info = crear_respaldo(ruta)
    if not info["ok"]:
        os.remove(ruta)
        raise OSError(f"La base de datos tiene errores; no se guardó el respaldo: {info['error']}")
    info["externo"] = copiar_externo(ruta)
    rotar(PREFIJO_AUTO, CONSERVAR_AUTO)
    return info


def _extraer_seguro(z, destino):
    base = os.path.realpath(destino)
    for nombre in z.namelist():
        objetivo = os.path.realpath(os.path.join(destino, nombre))
        if os.path.isabs(nombre) or not objetivo.startswith(base + os.sep) and objetivo != base:
            raise ValueError("El respaldo contiene rutas no permitidas.")
    z.extractall(destino)


def validar_respaldo(ruta_zip, destino):
    try:
        with zipfile.ZipFile(ruta_zip) as z:
            _extraer_seguro(z, destino)
    except zipfile.BadZipFile:
        raise ValueError("El archivo no es un respaldo válido (ZIP dañado).")
    base = os.path.join(destino, "rrhh.db")
    manifiesto_ruta = os.path.join(destino, "manifiesto.json")
    if not (os.path.exists(base) and os.path.exists(manifiesto_ruta)):
        raise ValueError("El archivo no parece un respaldo de esta aplicación.")
    with open(manifiesto_ruta, encoding="utf-8") as f:
        manifiesto = json.load(f)
    if manifiesto.get("sha256_db") != _sha256(base):
        raise ValueError("El respaldo está dañado: no coincide su huella de verificación.")
    if int(manifiesto.get("esquema", 0)) > bd.VERSION_ESQUEMA:
        raise ValueError("Este respaldo es de una versión más nueva de la aplicación. "
                         "Actualiza la aplicación antes de restaurarlo.")
    estado = verificar_archivo(base)
    if not estado["ok"]:
        raise ValueError(f"La base de datos del respaldo tiene errores: {estado['error']}")
    return manifiesto


def restaurar(ruta_zip):
    temporal = tempfile.mkdtemp(prefix="rrhh_rest_")
    try:
        manifiesto = validar_respaldo(ruta_zip, temporal)
        if os.path.exists(bd.RUTA_DB):
            try:
                crear_respaldo(os.path.join(carpeta_respaldos(), nombre_nuevo(PREFIJO_SEGURIDAD)))
                rotar(PREFIJO_SEGURIDAD, CONSERVAR_SEGURIDAD)
            except (sqlite3.DatabaseError, OSError):
                pass
        os.makedirs(bd.CARPETA_DATOS, exist_ok=True)
        nuevo = bd.RUTA_DB + ".nuevo"
        shutil.copy2(os.path.join(temporal, "rrhh.db"), nuevo)
        os.replace(nuevo, bd.RUTA_DB)
        for sobrante in (bd.RUTA_DB + "-journal", bd.RUTA_DB + "-wal", bd.RUTA_DB + "-shm"):
            if os.path.exists(sobrante):
                os.remove(sobrante)
        archivos = os.path.join(temporal, "archivos")
        if os.path.isdir(archivos):
            antes = bd.CARPETA_ARCHIVOS + ".antes"
            shutil.rmtree(antes, ignore_errors=True)
            if os.path.isdir(bd.CARPETA_ARCHIVOS):
                os.replace(bd.CARPETA_ARCHIVOS, antes)
            try:
                shutil.copytree(archivos, bd.CARPETA_ARCHIVOS)
            except OSError:
                shutil.rmtree(bd.CARPETA_ARCHIVOS, ignore_errors=True)
                if os.path.isdir(antes):
                    os.replace(antes, bd.CARPETA_ARCHIVOS)
                raise
            shutil.rmtree(antes, ignore_errors=True)
        bd.crear_tablas()
        return manifiesto
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def exportar_todo_xlsx(ruta):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    libro = Workbook()
    libro.remove(libro.active)
    relleno = PatternFill("solid", start_color="003D6B")
    for tabla, columnas in bd.COLUMNAS.items():
        hoja = libro.create_sheet(NOMBRES.get(tabla, tabla)[:31])
        extra = ["empleado"] if tabla in bd.CON_EMPLEADO else []
        cabecera = ["id"] + extra + list(columnas)
        hoja.append(cabecera)
        for r in bd.listar(tabla):
            hoja.append([r.get(c) for c in cabecera])
        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = relleno
        for i, c in enumerate(cabecera, start=1):
            hoja.column_dimensions[hoja.cell(row=1, column=i).column_letter].width = \
                min(max(len(c) + 3, 14), 40)
        hoja.freeze_panes = "A2"
    libro.save(ruta)
