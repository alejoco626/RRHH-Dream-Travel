import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request

import version

NOMBRE_EXE = "RRHH.exe"
CABECERAS = {"User-Agent": "RRHH-Dream-Travel", "Accept": "application/vnd.github+json"}


def numeros_version(texto):
    partes = re.findall(r"\d+", str(texto or ""))
    return tuple(int(p) for p in partes[:4]) or (0,)


def es_mas_nueva(remota, local):
    a, b = numeros_version(remota), numeros_version(local)
    largo = max(len(a), len(b))
    return a + (0,) * (largo - len(a)) > b + (0,) * (largo - len(b))


def datos_de_release(release):
    asset = next((a for a in release.get("assets", [])
                  if a.get("name", "").lower() == NOMBRE_EXE.lower()), None)
    if not asset:
        return None
    huella = str(asset.get("digest") or "")
    return {
        "version": release.get("tag_name", ""),
        "notas": (release.get("body") or "").strip(),
        "url": asset.get("browser_download_url", ""),
        "tamano": int(asset.get("size") or 0),
        "sha256": huella.split(":", 1)[1].lower() if huella.startswith("sha256:") else "",
    }


def buscar_nueva(local=None, timeout=6):
    local = local or version.VERSION
    url = f"https://api.github.com/repos/{version.REPOSITORIO}/releases/latest"
    pedido = urllib.request.Request(url, headers=CABECERAS)
    with urllib.request.urlopen(pedido, timeout=timeout) as r:
        release = json.loads(r.read().decode("utf-8"))
    datos = datos_de_release(release)
    if datos and datos["url"] and es_mas_nueva(datos["version"], local):
        return datos
    return None


def puede_actualizarse():
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def descargar(datos, destino, progreso=None):
    pedido = urllib.request.Request(datos["url"], headers={"User-Agent": CABECERAS["User-Agent"]})
    sha = hashlib.sha256()
    recibido = 0
    with urllib.request.urlopen(pedido, timeout=30) as r, open(destino, "wb") as f:
        total = int(r.headers.get("Content-Length") or datos["tamano"] or 0)
        while True:
            bloque = r.read(65536)
            if not bloque:
                break
            f.write(bloque)
            sha.update(bloque)
            recibido += len(bloque)
            if progreso and total:
                progreso(recibido / total)
    if datos["tamano"] and recibido != datos["tamano"]:
        raise OSError("La descarga quedó incompleta.")
    if datos["sha256"] and sha.hexdigest() != datos["sha256"]:
        raise OSError("El archivo descargado no coincide con el publicado.")


def texto_script(actual, nuevo, pid):
    return (
        "@echo off\r\n"
        "set /a n=0\r\n"
        ":esperar\r\n"
        "set /a n+=1\r\n"
        "ping 127.0.0.1 -n 2 >nul\r\n"
        f'move /y "{nuevo}" "{actual}" >nul 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  if %n% LSS 40 goto esperar\r\n"
        "  exit /b 1\r\n"
        ")\r\n"
        f'start "" "{actual}"\r\n'
        '(goto) 2>nul & del "%~f0"\r\n'
    )


def instalar_y_reiniciar(datos, progreso=None):
    actual = os.path.abspath(sys.executable)
    carpeta = os.path.dirname(actual)
    nuevo = os.path.join(carpeta, "RRHH_nuevo.exe")
    script = os.path.join(carpeta, "RRHH_actualizar.bat")
    descargar(datos, nuevo, progreso)
    with open(script, "w", encoding="ascii", newline="") as f:
        f.write(texto_script(actual, nuevo, os.getpid()))
    flags = 0x08000000 | 0x00000008
    subprocess.Popen(["cmd", "/c", script], creationflags=flags, close_fds=True, cwd=carpeta)
