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
    "1.4.5": {
        "correcciones": ["La actualización automática ya no se cierra sola a mitad de camino: el instalador cierra la app sin cerrarse a sí mismo"],
    },
    "1.4.4": {
        "correcciones": ["Al actualizar, la app se cierra sola y el instalador ya no necesita que cierres RRHH.exe a mano"],
    },
    "1.4.3": {
        "nuevo": ["Al cargar un archivo de datos, la app compara lo que trae con lo que tiene y avisa si algo quedó sin cargar"],
        "cambios": ["El mensaje de carga ahora incluye las entradas de historial y los totales que quedaron en la app"],
    },
    "1.4.2": {
        "cambios": ["La carga automática reconoce el archivo de datos aunque tenga otro nombre (WhatsApp, correo, «(1)»…)"],
        "correcciones": ["Si no hay datos, la app lo avisa y ofrece el botón «Cargar datos (JSON)» en lugar de quedar en blanco"],
    },
    "1.4.1": {
        "nuevo": ["Aviso «Posible duplicado» en la tabla y en la ficha cuando dos candidatos comparten teléfono, correo o nombre, con el motivo"],
        "cambios": ["Las filas repetidas se guardan tal como están en el libro (nombre, teléfono, correo, puesto y fuente) dentro del historial"],
    },
    "1.4.0": {
        "nuevo": ["Nueva sección «Reagendas»: cuántas veces cada persona cambió su prueba o entrevista, con colores y su historial",
                  "Si cambias la fecha u hora de una cita ya agendada, la app pregunta si es una reagenda y avisa al pasar el máximo",
                  "Los candidatos repetidos conservan todo lo anterior en su historial (cada postulación y cada cita cambiada)",
                  "En Configuración: máximo de reagendas, capacidad, horarios, umbrales, pruebas del promedio y listas de candidatos"],
        "cambios": ["«Resumen» y «Resumen del proceso» ahora son uno solo y muestra la cantidad real de personas",
                    "El JSON incluye el historial y se puede cargar sin duplicar nada"],
        "correcciones": ["Al unir repetidos ya no se pierde la entrevista agendada si la fila más nueva no la tenía"],
    },
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
