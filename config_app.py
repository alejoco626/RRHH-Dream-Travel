"""Constantes de la aplicación instalada y de su actualización."""
import os
import tempfile

import version

NOMBRE_APP = "RRHH – Dream & Travel"
ID_APP_WINDOWS = "DreamTravel.RRHH"
NOMBRE_INSTALADOR = "RRHH-Instalador.exe"
URL_ULTIMA_VERSION = f"https://api.github.com/repos/{version.REPOSITORIO}/releases/latest"
PREFIJO_DESCARGA = f"https://github.com/{version.REPOSITORIO}/releases/download/"
CARPETA_ACTUALIZACION = os.path.join(tempfile.gettempdir(), "DreamTravel_RRHH_Update")
AGENTE_HTTP = "DreamTravel-RRHH"
CARPETA_REGISTRO = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                                "DreamTravel")
ARCHIVO_ERRORES = os.path.join(CARPETA_REGISTRO, "rrhh_error.log")
