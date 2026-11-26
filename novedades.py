"""Notas que se muestran una sola vez, al abrir la app recién actualizada.

Antes de publicar una versión, agrega aquí su entrada con el mismo número del release.
Lo "nuevo" se muestra con punto negro (●), los "cambios" con guion y las "correcciones" con
punto (•); una sección vacía no aparece. Si la versión no tiene entrada, no se muestra ventana.
"""
import os

from actualizador import es_mas_nueva
from config_app import CARPETA_REGISTRO

SECCIONES = (
    ("nuevo", "Nuevo", "●"),
    ("cambios", "Cambios", "-"),
    ("correcciones", "Correcciones", "•"),
)

NOVEDADES = {
    "1.3.2": {
        "cambios": ["La tabla de Candidatos es más compacta y se ve completa junto al panel lateral"],
        "correcciones": ["Ya no aparece la palabra «null» al final de Matriz y ranking ni en el Resumen"],
    },
    "1.3.1": {
        "nuevo": ["Al cargar un JSON puedes actualizar también a los candidatos que ya estaban, viendo antes cuántos cambian"],
        "correcciones": ["Se unen como una sola persona los candidatos con el mismo correo aunque el teléfono tenga un error",
                         "Las evaluaciones en 0 del libro ya no se pierden al convertirlo"],
    },
    "1.3.0": {
        "nuevo": [
            "Reclutamiento: registro de candidatos igual que en el libro, con embudo por estado",
            "Evaluación por criterios (6 pruebas), promedio comparable, ranking y grupos A, B y C",
            "Programación como embudo aparte: lista, calendario y capacidad de pruebas y entrevistas",
            "Resumen del proceso con gráficas, y carga automática de los datos desde un archivo JSON",
        ],
        "cambios": ["El embudo, las pruebas y las entrevistas anteriores se ocultan mientras no tengan datos"],
    },
    "1.2.2": {
        "nuevo": ["La actualización automática ahora descarga el instalador, lo verifica y reabre la app sola"],
        "correcciones": ["Se corrigió la actualización que no terminaba de instalarse"],
    },
    "1.2.0": {
        "nuevo": [
            "Nueva interfaz con gráficas, animaciones y modo oscuro",
            "Respaldos y verificación de la base de datos",
            "Ausencias, Plazas y Puestos, e informes por persona",
        ],
    },
}

ARGUMENTO_ACTUALIZADO = "--actualizado"  # lo pasa el instalador al reabrir el programa
ARCHIVO_VERSION_VISTA = os.path.join(CARPETA_REGISTRO, "rrhh_ultima_version.txt")


def leer_version_vista():
    try:
        with open(ARCHIVO_VERSION_VISTA, encoding="utf-8") as archivo:
            return archivo.read().strip() or None
    except OSError:
        return None


def guardar_version_vista(version):
    try:
        os.makedirs(os.path.dirname(ARCHIVO_VERSION_VISTA), exist_ok=True)
        with open(ARCHIVO_VERSION_VISTA, "w", encoding="utf-8") as archivo:
            archivo.write(version)
    except OSError:
        pass


def notas_a_mostrar(version_actual, recien_actualizado, version_vista):
    """Las notas de esta versión si hay que mostrarlas ahora; si no, None."""
    notas = NOVEDADES.get(version_actual)
    if not notas or not any(notas.get(clave) for clave, _titulo, _vineta in SECCIONES):
        return None
    if recien_actualizado:
        return notas
    if version_vista is not None and es_mas_nueva(version_actual, version_vista):
        return notas
    return None
