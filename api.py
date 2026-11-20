"""Puente entre la interfaz web (pywebview) y la lógica de la aplicación.

Cada método público lo llama JavaScript y devuelve {"ok": True, "datos": ...} o
{"ok": False, "error": "texto"}. Las fechas viajan como dd/mm/aaaa hacia la pantalla y como
aaaa-mm-dd en la base de datos.
"""
import functools
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, timedelta

import agenda
import ausencias
import base_datos as bd
import configuracion
import documentos
import evaluacion as ev
import importador
import informes
import logica
import ranking
import respaldos
import version

ETAPAS = ["Prueba de habilidades", "Pruebas psicométricas", "Entrevista"]
PSICO = "Pruebas psicométricas"
HABIL = "Prueba de habilidades"
PERSONAL = ("empleados", "amonestaciones", "vacaciones", "memos", "ausencias")


def campo(clave, etiqueta, tipo="texto", req=False, opciones=None, completo=False, pdf=False):
    return dict(clave=clave, etiqueta=etiqueta, tipo=tipo, req=req, opciones=opciones or [],
                completo=completo, pdf=pdf)


CAMPOS = {
    "empleados": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("puesto", "Puesto", "opcion", True, ranking.PUESTOS),
        campo("departamento", "Departamento", "opcion", True, configuracion.DEPARTAMENTOS),
        campo("fecha_ingreso", "Fecha de ingreso", "fecha"),
        campo("fecha_cumpleanos", "Fecha de cumpleaños", "fecha"),
        campo("grupo", "Grupo de autorización de vacaciones", "opcion", False,
              configuracion.GRUPOS, completo=True),
    ],
    "pruebas": [
        campo("candidato", "Candidato", "opcion", True, completo=True),
        campo("puesto", "Puesto"),
        campo("fecha", "Fecha de evaluación", "fecha", True),
        campo("fecha_prueba", "Fecha de la prueba", "fecha"),
        campo("tipo_prueba", "Tipo de prueba", "opcion", False, [HABIL, PSICO]),
        campo("puntaje", "Puntaje"),
        campo("observaciones", "Observaciones", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "entrevistas": [
        campo("candidato", "Nombre completo", "opcion", True, completo=True),
        campo("telefono", "Número de teléfono", req=True),
        campo("puesto", "Plaza", "opcion", False, ranking.PLAZAS),
        campo("fecha", "Fecha de la entrevista", "fecha", True),
        campo("hora", "Hora (ej. 10:00 o 2:30 pm)", "hora", True),
        campo("entrevistador", "Entrevistador"),
        campo("resultado", "Resultado", "opcion", False, ["Aprobado", "En proceso", "No aprobado"]),
        campo("observaciones", "Observaciones", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "amonestaciones": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("fecha", "Fecha", "fecha", True),
        campo("numero_vez", "Número de vez", "opcion", True, ["1", "2", "3", "4", "5"]),
        campo("falta", "Falta cometida", req=True, completo=True),
        campo("aspecto", "Aspecto a mejorar", completo=True),
        campo("detalle", "Detalle de la falta", "largo"),
        campo("firmante", "Firma (nombre)", req=True),
        campo("cargo_firmante", "Firma (cargo)", req=True),
        campo("archivo", "Carta firmada y escaneada (PDF)", "archivo", pdf=True),
    ],
    "vacaciones": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("folio", "Folio (vacío = automático)"),
        campo("fecha_solicitud", "Fecha de la solicitud", "fecha", True),
        campo("autoriza", "Autoriza", "opcion", True, completo=True),
        campo("fecha_inicio", "Primer día de goce", "fecha", True),
        campo("dias", "Días de goce (ej. 10.5)", "texto", True),
        campo("fecha_fin", "Último día de goce", "fecha", True),
        campo("fecha_regreso", "Fecha de regreso", "fecha"),
        campo("periodo_desde", "Periodo laborado desde", "fecha", True),
        campo("periodo_hasta", "Periodo laborado hasta", "fecha", True),
        campo("fecha_constancia", "Fecha de la constancia (vacía = día siguiente)", "fecha",
              completo=True),
        campo("observaciones", "Observaciones", "largo"),
        campo("archivo_solicitud", "Solicitud firmada y escaneada (PDF)", "archivo", pdf=True),
        campo("archivo_constancia", "Constancia firmada y escaneada (PDF)", "archivo", pdf=True),
    ],
    "embudo": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("telefono", "Número de teléfono", req=True),
        campo("plaza", "Plaza", "opcion", False, ranking.PLAZAS),
        campo("etapa", "Etapa", "opcion", True, ETAPAS),
        campo("asistencia", "Asistencia", "opcion", False, agenda.ASISTENCIAS),
        campo("fecha", "Fecha de la prueba o entrevista", "fecha", True),
        campo("hora", "Hora (ej. 10:00 o 2:30 pm)", "hora", True),
        campo("notas", "Notas", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "no_aprobados": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("telefono", "Número de teléfono"),
        campo("etapa", "Etapa en la que quedó", "opcion", True, ETAPAS),
        campo("fecha_descarte", "Fecha en que se descartó", "fecha"),
        campo("motivo", "Motivo", "largo"),
        campo("notas", "Notas", "largo"),
    ],
    "memos": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("fecha", "Fecha", "fecha", True),
        campo("emisor", "De"),
        campo("tema", "Tema o política", "opcion", True, configuracion.TEMAS_MEMO, completo=True),
        campo("observaciones", "Observaciones", "largo"),
        campo("archivo", "Memo firmado y escaneado (PDF)", "archivo", pdf=True),
    ],
    "ausencias": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("tipo", "Tipo de ausencia", "opcion", True, ausencias.TIPOS),
        campo("etapa", "Etapa", "opcion", True, ausencias.ETAPAS),
        campo("fecha", "Primer día", "fecha", True),
        campo("fecha_fin", "Último día (vacío si fue un solo día)", "fecha"),
        campo("fecha_cierre", "Fecha de cierre", "fecha"),
        campo("motivo", "Motivo o detalle", "largo"),
        campo("archivo", "Justificante (PDF)", "archivo", pdf=True),
    ],
}

COLUMNAS = {
    "empleados": [("nombre_completo", "Nombre"), ("puesto", "Puesto"),
                  ("departamento", "Departamento")],
    "pruebas": [("candidato", "Candidato"), ("tipo_prueba", "Tipo"), ("fecha", "F. evaluación"),
                ("situacion", "Situación"), ("fecha_prueba", "F. prueba"), ("puntaje", "Nota"),
                ("adjuntos", "Archivos")],
    "entrevistas": [("candidato", "Nombre"), ("telefono", "Teléfono"), ("fecha", "Fecha"),
                    ("hora", "Hora"), ("resultado", "Resultado"), ("adjuntos", "Archivos")],
    "amonestaciones": [("empleado", "Empleado"), ("fecha", "Fecha"), ("numero_vez", "Vez"),
                       ("falta", "Falta"), ("archivo", "Comprobante")],
    "vacaciones": [("folio", "Folio"), ("empleado", "Empleado"), ("fecha_inicio", "Desde"),
                   ("dias", "Días"), ("archivo_solicitud", "Solicitud"),
                   ("archivo_constancia", "Constancia")],
    "memos": [("empleado", "Empleado"), ("fecha", "Fecha"), ("tema", "Tema"),
              ("archivo", "Comprobante")],
    "ausencias": [("empleado", "Empleado"), ("tipo", "Tipo"), ("fecha", "Desde"), ("dias", "Días"),
                  ("etapa", "Etapa"), ("archivo", "Justificante")],
    "embudo": [("nombre_completo", "Nombre"), ("telefono", "Teléfono"), ("plaza", "Plaza"),
               ("etapa", "Etapa"), ("fecha", "Fecha"), ("hora", "Hora"),
               ("situacion", "Situación"), ("adjuntos", "Archivos")],
    "no_aprobados": [("nombre_completo", "Nombre"), ("telefono", "Teléfono"),
                     ("etapa", "Quedó en"), ("motivo", "Motivo"), ("fecha_descarte", "Descartado")],
}

# clave: (tabla, estado, grupo, título, subtítulo, formulario, botón nuevo, acciones, cabecera)
MODULOS = {
    "resumen": dict(titulo="Resumen", grupo="", tipo="resumen"),
    "embudo": dict(tabla="embudo", estado="Activo", grupo="Selección", titulo="Embudo de confirmados",
                   sub="Personas que confirmaron su asistencia a las pruebas o a la entrevista",
                   acciones=[("mover_etapa", "Mover de etapa", "sec"),
                             ("registrar_resultado", "Registrar resultado", "sec"),
                             ("marcar_recibido", "Marcar recibido", "sec"),
                             ("descartar", "Descartar candidato", "sec")]),
    "pruebas": dict(tabla="pruebas", grupo="Selección", titulo="Pruebas", formulario=False,
                    sub="Cada prueba se registra con su ficha de calificaciones; la nota final "
                        "es el promedio",
                    acciones=[("abrir_prueba", "Abrir / editar", "sec"),
                              ("pasar_entrevista", "Pasar a entrevista", "sec"),
                              ("descartar_registro", "Descartar candidato", "sec"),
                              ("eliminar", "Eliminar", "peligro")],
                    cabecera=[("nueva_habilidades", "+ Prueba de habilidades", "pri"),
                              ("nueva_psicometrica", "+ Psicométrica", "sec"),
                              ("plantilla", "Plantilla de importación", "fan"),
                              ("importar", "Importar pruebas", "sec")]),
    "entrevistas": dict(tabla="entrevistas", grupo="Selección", titulo="Entrevistas",
                        sub="Entrevistas realizadas a los candidatos",
                        acciones=[("descartar_registro", "Descartar candidato", "sec")]),
    "ranking": dict(grupo="Selección", titulo="Ranking de candidatos", tipo="ranking"),
    "no_aprobados": dict(tabla="embudo", estado="No aprobado", grupo="Selección",
                         titulo="No aprobados", sub="Candidatos que no continúan en el proceso",
                         acciones=[("reactivar", "Reactivar en el embudo", "sec")]),
    "empleados": dict(tabla="empleados", grupo="Personal", titulo="Empleados",
                      sub="Nombre, puesto y departamento son obligatorios; lo demás puedes ir "
                          "completándolo"),
    "amonestaciones": dict(tabla="amonestaciones", grupo="Personal", titulo="Amonestaciones",
                           sub="Cartas de amonestación y su comprobante firmado",
                           acciones=[("crear_carta", "Crear carta (Word)", "sec")]),
    "vacaciones": dict(tabla="vacaciones", grupo="Personal", titulo="Vacaciones",
                       sub="Solicitud, constancia de goce y comprobantes escaneados",
                       acciones=[("sugerir_periodo", "Sugerir periodo", "sec"),
                                 ("crear_solicitud", "Crear solicitud", "sec"),
                                 ("crear_constancia", "Crear constancia", "sec")]),
    "memos": dict(tabla="memos", grupo="Personal", titulo="Memorándums",
                  sub="Políticas internas firmadas por cada empleado"),
    "ausencias": dict(tabla="ausencias", grupo="Personal", titulo="Ausencias",
                      sub="Faltas, permisos e incapacidades, desde que se reportan hasta su cierre",
                      acciones=[("avanzar_ausencia", "Siguiente etapa", "sec")]),
    "documentos": dict(grupo="Documentos", titulo="Vista previa", tipo="documentos"),
    "pendientes": dict(grupo="Documentos", titulo="Pendientes de completar", tipo="pendientes"),
    "respaldos": dict(grupo="Sistema", titulo="Respaldos", tipo="respaldos"),
    "configuracion": dict(grupo="Sistema", titulo="Configuración", tipo="configuracion"),
}

RENOMBRES = {
    "plazas": lambda v, n: bd.renombrar_plaza(v, n),
    "puestos": lambda v, n: bd.renombrar_valor("empleados", "puesto", v, n),
    "departamentos": lambda v, n: bd.renombrar_valor("empleados", "departamento", v, n),
    "temas_memo": lambda v, n: bd.renombrar_valor("memos", "tema", v, n),
    "tipos_ausencia": lambda v, n: bd.renombrar_valor("ausencias", "tipo", v, n),
    "etapas_ausencia": lambda v, n: bd.renombrar_valor("ausencias", "etapa", v, n),
    "categorias_adjunto": lambda v, n: bd.renombrar_valor("adjuntos", "categoria", v, n),
    "grupos": lambda v, n: bd.renombrar_valor("empleados", "grupo", v, n),
}


def _mostrar(clave, valor):
    if valor is None:
        return ""
    if clave.startswith("fecha"):
        return logica.formatear(valor)
    if clave == "dias":
        return logica.texto_dias(valor)
    if clave == "hora":
        return logica.formatear_hora(valor)
    if clave == "adjuntos":
        return f"{valor} archivo{'s' if valor != 1 else ''}" if valor else ""
    if clave.startswith("archivo"):
        return "Listo" if valor else ""
    return str(valor)


def _nombre_visible(guardado):
    nombre = guardado or ""
    return nombre.split("_", 1)[1] if "_" in nombre and nombre.split("_", 1)[0].isdigit() \
        else nombre


class SinDatos(Exception):
    pass


def seguro(funcion):
    @functools.wraps(funcion)
    def envoltura(self, *args, **kwargs):
        try:
            return {"ok": True, "datos": funcion(self, *args, **kwargs)}
        except (ValueError, SinDatos) as e:
            return {"ok": False, "error": str(e)}
        except sqlite3.IntegrityError as e:
            return {"ok": False, "error": f"No se pudo guardar: {e}"}
        except OSError as e:
            return {"ok": False, "error": f"No se pudo completar la operación: {e}"}
        except Exception as e:  # la pantalla nunca debe quedarse sin respuesta
            return {"ok": False, "error": f"Error inesperado: {type(e).__name__}: {e}"}
    return envoltura


class Api:
    def __init__(self):
        self._ventana = None
        self._dialogos = None  # se puede reemplazar en pruebas
        self._actualizacion = None
        self.alerta_base = None

    # ------------------------------------------------------------------ utilidades
    def _dialogo(self, tipo, **kw):
        if self._dialogos is not None:
            return self._dialogos(tipo, **kw)
        import webview
        modo = {"abrir": webview.OPEN_DIALOG, "guardar": webview.SAVE_DIALOG,
                "carpeta": webview.FOLDER_DIALOG}[tipo]
        tipos = kw.get("tipos") or ()
        r = self._ventana.create_file_dialog(
            modo, allow_multiple=kw.get("multiple", False), save_filename=kw.get("nombre", ""),
            file_types=tuple(tipos))
        if not r:
            return None
        if tipo == "guardar":
            return r if isinstance(r, str) else r[0]
        return list(r) if kw.get("multiple") else r[0]

    @staticmethod
    def _abrir_ruta(ruta):
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
        except OSError as e:
            raise ValueError(f"No se pudo abrir {ruta}: {e}")

    # ------------------------------------------------------------------ arranque
    @seguro
    def inicio(self):
        return {"version": version.VERSION, "alerta_base": self.alerta_base,
                "modulos": self._modulos(),
                "puede_actualizar": self._puede_actualizar(), "hoy": date.today().isoformat()}

    @staticmethod
    def _puede_actualizar():
        import actualizador
        return actualizador.puede_actualizarse()

    def _modulos(self):
        salida = []
        for clave, m in MODULOS.items():
            item = {"clave": clave, "titulo": m["titulo"], "grupo": m["grupo"],
                    "tipo": m.get("tipo", "crud"), "sub": m.get("sub", "")}
            if "tabla" in m:
                item.update(tabla=m["tabla"], formulario=m.get("formulario", True),
                            acciones=[dict(id=a, texto=t, tipo=k) for a, t, k in m.get("acciones", [])],
                            cabecera=[dict(id=a, texto=t, tipo=k) for a, t, k in m.get("cabecera", [])],
                            campos=CAMPOS[clave if clave in CAMPOS else m["tabla"]],
                            columnas=[dict(clave=c, titulo=t) for c, t in COLUMNAS[clave if clave in COLUMNAS else m["tabla"]]],
                            persona=m["tabla"] in PERSONAL)
            salida.append(item)
        return salida

    @seguro
    def listas(self):
        """Listas que cambian con la configuración (para refrescar los desplegables)."""
        return {
            "campos": {k: {c["clave"]: list(c["opciones"]) for c in v if c["tipo"] == "opcion"}
                       for k, v in CAMPOS.items()},
            "empleados": [{"id": i, "nombre": n} for i, n in bd.empleados_basico()],
            "candidatos": sorted({r["nombre_completo"] for r in bd.listar("embudo")}),
            "categorias": list(bd.CATEGORIAS_ADJUNTO)}

    # ------------------------------------------------------------------ listados
    def _registros(self, clave, buscar="", persona=None, etapa=None):
        m = MODULOS[clave]
        tabla, estado = m["tabla"], m.get("estado")
        registros = bd.listar(tabla, buscar)
        columnas = COLUMNAS[clave if clave in COLUMNAS else tabla]
        if any(c[0] == "adjuntos" for c in columnas):
            conteos = bd.conteo_adjuntos(tabla)
            for r in registros:
                r["adjuntos"] = conteos.get(r["id"], 0)
        if persona is not None:
            k = "id" if tabla == "empleados" else "empleado_id"
            registros = [r for r in registros if r.get(k) == persona]
        franja = None
        if tabla == "ausencias":
            franja = ausencias.embudo(registros)
            if etapa:
                registros = [r for r in registros if r.get("etapa") == etapa]
        if estado:
            registros = [r for r in registros if r.get("estado") == estado]
        if any(c[0] == "situacion" for c in columnas):
            hoy = date.today()
            for r in registros:
                r["situacion"] = (agenda.situacion_prueba(r, hoy) if tabla == "pruebas"
                                  else agenda.situacion(r, hoy))
        if estado == "Activo":
            registros.sort(key=lambda r: (r.get("fecha") or "9999", r.get("hora") or ""))
        return registros, columnas, franja

    @seguro
    def listar(self, clave, buscar="", persona=None, etapa=None):
        registros, columnas, franja = self._registros(clave, buscar, persona, etapa)
        filas = [{"id": r["id"],
                  "celdas": [_mostrar(c, r.get(c)) for c, _ in columnas],
                  "atrasado": str(r.get("situacion", "")).startswith("Atrasad")} for r in registros]
        extra = {}
        if MODULOS[clave].get("estado") == "Activo":
            extra["por_etapa"] = {e: sum(1 for r in registros if r["etapa"] == e) for e in ETAPAS}
        if franja is not None:
            extra["franja"] = franja
        return {"filas": filas, "total": len(filas), **extra}

    @seguro
    def personas(self):
        return [{"id": i, "nombre": n} for i, n in bd.empleados_basico()]

    # ------------------------------------------------------------------ formulario
    def _valores_form(self, clave, fila):
        campos = CAMPOS[clave if clave in CAMPOS else MODULOS[clave]["tabla"]]
        valores = {}
        for c in campos:
            k, t, v = c["clave"], c["tipo"], fila.get(c["clave"])
            if t == "adjuntos":
                continue
            if t == "archivo":
                valores[k] = {"actual": v or "", "origen": None, "nombre": _nombre_visible(v)}
            elif t == "empleado":
                valores[k] = "" if v is None else str(v)
            elif t == "fecha":
                valores[k] = logica.formatear(v) if v else ""
            elif t == "hora":
                valores[k] = logica.formatear_hora(v) if v else ""
            elif k == "dias":
                valores[k] = "" if v is None else logica.texto_dias(v)
            else:
                valores[k] = "" if v is None else str(v)
        if MODULOS[clave].get("tabla") == "vacaciones" and fila.get("fecha_fin"):
            try:
                valores["fecha_regreso"] = logica.formatear(logica.fecha_regreso(
                    logica.formatear(fila["fecha_fin"])))
            except ValueError:
                valores["fecha_regreso"] = ""
        return valores

    def _adjuntos_de(self, tabla, id_registro):
        return [{"id": x["id"], "archivo": x["archivo"], "origen": None,
                 "nombre": _nombre_visible(x["archivo"]), "categoria": x["categoria"]}
                for x in bd.adjuntos_de(tabla, id_registro)]

    @seguro
    def obtener(self, clave, id_registro):
        tabla = MODULOS[clave]["tabla"]
        fila = bd.obtener(tabla, id_registro)
        if fila is None:
            raise ValueError("El registro ya no existe.")
        r = {"id": id_registro, "valores": self._valores_form(clave, fila)}
        if any(c["tipo"] == "adjuntos" for c in CAMPOS[clave if clave in CAMPOS else tabla]):
            r["adjuntos"] = self._adjuntos_de(tabla, id_registro)
        return r

    @seguro
    def nuevo(self, clave):
        tabla = MODULOS[clave]["tabla"]
        campos = CAMPOS[clave if clave in CAMPOS else tabla]
        v = self._valores_form(clave, {})
        if tabla == "vacaciones":
            v["folio"] = bd.siguiente_folio(date.today().year)
        if tabla == "amonestaciones":
            v.update(firmante=bd.leer_config("ultimo_firmante", ""),
                     cargo_firmante=bd.leer_config("ultimo_cargo", ""), numero_vez="1")
        if tabla == "memos":
            v["emisor"] = bd.leer_config("ultimo_emisor_memo", "")
        if tabla == "ausencias":
            v["etapa"] = ausencias.ETAPAS[0]
        if tabla == "embudo":
            v["etapa"] = ETAPAS[0]
            if "asistencia" in v:
                v["asistencia"] = agenda.ASISTENCIAS[0]
        return {"id": None, "valores": v, "adjuntos": [] if any(
            c["tipo"] == "adjuntos" for c in campos) else None}

    def _leer(self, clave, valores, id_actual, empleados_hay=True):
        tabla = MODULOS[clave]["tabla"]
        campos = CAMPOS[clave if clave in CAMPOS else tabla]
        datos = {}
        for c in campos:
            k, t = c["clave"], c["tipo"]
            if t in ("archivo", "adjuntos") or k == "fecha_regreso":
                continue
            v = str(valores.get(k) or "").strip()
            if c["req"] and not v:
                if t == "empleado" and not bd.empleados_basico():
                    raise ValueError("Primero registra al empleado en la sección Empleados.")
                raise ValueError(f"Falta completar: {c['etiqueta']}.")
            if t == "fecha" and v:
                v = logica.a_iso(v)
                if not v:
                    raise ValueError(f"Fecha no válida en: {c['etiqueta']}. Usa dd/mm/aaaa.")
            elif t == "hora" and v:
                v = logica.parsear_hora(v)
                if not v:
                    raise ValueError(f"Hora no válida en: {c['etiqueta']}. Escribe por ejemplo "
                                     "10:00 o 2:30 pm.")
            elif t == "empleado":
                v = int(v)
            elif k == "numero_vez":
                v = int(v)
            datos[k] = v if v not in ("", None) else None
        if tabla == "ausencias":
            dias = ausencias.dias_de(datos["fecha"], datos.get("fecha_fin"))
            if dias is None:
                raise ValueError("El último día es anterior al primero.")
            datos["dias"] = dias
            if datos.get("fecha_cierre") and datos["fecha_cierre"] < datos["fecha"]:
                raise ValueError("La fecha de cierre es anterior a la ausencia.")
        if tabla == "vacaciones":
            if datos["fecha_fin"] < datos["fecha_inicio"]:
                raise ValueError("El último día de goce es anterior al primero.")
            if datos["periodo_hasta"] < datos["periodo_desde"]:
                raise ValueError("El periodo laborado es inválido (hasta < desde).")
            datos["dias"] = logica.leer_dias(datos["dias"])
            if datos["dias"] != logica.dias_vacaciones(datos["fecha_inicio"], datos["fecha_fin"]):
                raise ValueError("Los días de goce no coinciden con las fechas. Cambia los días, "
                                 "el último día o la fecha de regreso y se ajustan solos.")
            if datos["folio"] and any(v["folio"] == datos["folio"] and v["id"] != id_actual
                                      for v in bd.listar("vacaciones")):
                raise ValueError(f"El folio {datos['folio']} ya existe. Escribe otro.")
        return datos

    @seguro
    def guardar(self, clave, id_actual, valores, adjuntos=None):
        m = MODULOS[clave]
        tabla = m["tabla"]
        datos = self._leer(clave, valores, id_actual)
        campos = CAMPOS[clave if clave in CAMPOS else tabla]
        for c in campos:
            if c["tipo"] == "archivo":
                a = valores.get(c["clave"]) or {}
                datos[c["clave"]] = bd.copiar_archivo(a["origen"]) if a.get("origen") \
                    else (a.get("actual") or None)
        adjuntos = adjuntos or []
        for a in adjuntos:
            if a.get("origen"):
                a["archivo"] = bd.copiar_archivo(a["origen"])
                a["origen"] = None
        if tabla == "embudo" and id_actual is None:
            datos["estado"] = m.get("estado") or "Activo"
        if tabla == "vacaciones" and not datos.get("folio"):
            datos["folio"] = bd.siguiente_folio(datos["fecha_solicitud"][:4])
        nuevo_id = bd.guardar(tabla, datos, id_actual)
        if any(c["tipo"] == "adjuntos" for c in campos):
            actuales = {a["id"] for a in adjuntos if a.get("id")}
            for previo in bd.adjuntos_de(tabla, nuevo_id):
                if previo["id"] not in actuales:
                    bd.quitar_adjunto(previo["id"])
            for a in adjuntos:
                if not a.get("id"):
                    bd.agregar_adjunto(tabla, nuevo_id, a["archivo"], a.get("categoria", "Otro"))
        if tabla == "amonestaciones":
            bd.guardar_config("ultimo_firmante", datos["firmante"])
            bd.guardar_config("ultimo_cargo", datos["cargo_firmante"])
        if tabla in ("pruebas", "entrevistas"):
            bd.confirmar_asistencia(datos["candidato"], tabla == "entrevistas")
        if tabla == "memos" and datos.get("emisor"):
            bd.guardar_config("ultimo_emisor_memo", datos["emisor"])
        return self.obtener(clave, nuevo_id)["datos"]

    @seguro
    def eliminar(self, clave, id_registro):
        try:
            bd.eliminar(MODULOS[clave]["tabla"], id_registro)
        except sqlite3.IntegrityError:
            raise ValueError("Este empleado tiene amonestaciones, vacaciones o memos registrados.")
        return True

    # ------------------------------------------------------------------ archivos
    @seguro
    def elegir_archivos(self, pdf=False, multiple=False):
        tipos = ("PDF (*.pdf)",) if pdf else (
            "Documentos (*.pdf;*.doc;*.docx;*.xls;*.xlsx;*.xlsm)",)
        r = self._dialogo("abrir", tipos=tipos, multiple=multiple)
        if not r:
            return []
        rutas = r if isinstance(r, list) else [r]
        return [{"ruta": p, "nombre": os.path.basename(p)} for p in rutas]

    @seguro
    def abrir_archivo(self, nombre=None, origen=None):
        if not origen and not nombre:
            raise ValueError("Todavía no hay un archivo guardado.")
        ruta = origen or bd.ruta_archivo(nombre)
        if not os.path.exists(ruta):
            raise ValueError("El archivo ya no está disponible en la carpeta de datos.")
        self._abrir_ruta(ruta)
        return True

    @seguro
    def candidato_telefono(self, nombre):
        r = bd.embudo_de(nombre)
        return (r or {}).get("telefono") or ""

    # ------------------------------------------------------------------ vacaciones
    @seguro
    def calcular_goce(self, origen, v):
        """Recalcula días / último día / regreso según el campo que el usuario editó."""
        salida = {}
        try:
            inicio = logica.parsear_fecha(v.get("fecha_inicio", ""))
            if inicio is None:
                return salida
            if origen == "dias":
                fin = logica.fecha_fin_por_dias(inicio, logica.leer_dias(v.get("dias", "")))
            elif origen == "fecha_regreso":
                fin = logica.ultimo_dia_antes_de(v.get("fecha_regreso", ""), inicio)
            else:
                fin = logica.parsear_fecha(v.get("fecha_fin", ""))
                if fin is None:
                    return salida
            dias = logica.dias_vacaciones(inicio, fin)
        except ValueError:
            return salida
        if origen != "dias":
            salida["dias"] = logica.texto_dias(dias)
        if origen != "fecha_fin":
            salida["fecha_fin"] = logica.formatear(fin)
        if origen != "fecha_regreso":
            salida["fecha_regreso"] = logica.formatear(logica.fecha_regreso(fin))
        return salida

    @seguro
    def sugerir_periodo(self, empleado_id, fecha_inicio, fecha_solicitud, avisar=True):
        emp = bd.obtener("empleados", int(empleado_id)) if empleado_id not in (None, "") else None
        referencia = fecha_inicio or fecha_solicitud
        if not emp or not emp.get("fecha_ingreso") or not logica.parsear_fecha(referencia):
            if avisar:
                raise ValueError("Para calcularlo elige el empleado (con su fecha de ingreso "
                                 "registrada) y el primer día de goce.")
            return None
        periodo = logica.periodo_vencido(emp["fecha_ingreso"], referencia)
        if periodo is None:
            if avisar:
                raise ValueError("El empleado aún no cumple un año de trabajo.")
            return None
        return {"periodo_desde": logica.formatear(periodo[0]),
                "periodo_hasta": logica.formatear(periodo[1])}

    @seguro
    def autorizadores(self, empleado_id):
        emp = bd.obtener("empleados", int(empleado_id)) if empleado_id not in (None, "") else None
        return logica.autorizadores(emp.get("grupo")) if emp else []

    # ------------------------------------------------------------------ acciones
    def _generar(self, funcion, clave, id_registro, mensaje):
        ruta = funcion(bd.obtener(MODULOS[clave]["tabla"], id_registro))
        return {"mensaje": mensaje, "documento": ruta}

    @seguro
    def accion(self, clave, nombre, id_registro=None, extra=None):
        extra = extra or {}
        tabla = MODULOS[clave]["tabla"]
        if nombre == "crear_solicitud":
            return self._generar(documentos.generar_solicitud_vacaciones, clave, id_registro,
                                 "Solicitud creada.")
        if nombre == "crear_constancia":
            return self._generar(documentos.generar_constancia_vacaciones, clave, id_registro,
                                 "Constancia creada.")
        if nombre == "crear_carta":
            return self._generar(documentos.generar_amonestacion, clave, id_registro,
                                 "Carta de amonestación creada.")
        if nombre == "mover_etapa":
            r = bd.obtener("embudo", id_registro)
            if r["etapa"] == ETAPAS[-1]:
                raise ValueError("El candidato ya está en la última etapa (Entrevista).")
            siguiente = ETAPAS[(ETAPAS.index(r["etapa"]) if r["etapa"] in ETAPAS else 0) + 1]
            bd.guardar("embudo", {"etapa": siguiente, "fecha": None, "hora": None,
                                  "asistencia": "Pendiente"}, id_registro)
            return {"mensaje": f"Pasó a {siguiente}. Escribe la fecha y la hora de esta etapa.",
                    "recargar": id_registro}
        if nombre == "avanzar_ausencia":
            r = bd.obtener("ausencias", id_registro)
            if r["etapa"] == ausencias.ETAPAS[-1]:
                raise ValueError("Esta ausencia ya está en la última etapa.")
            nueva = ausencias.siguiente(r["etapa"])
            cambios = {"etapa": nueva}
            if nueva == ausencias.ETAPAS[-1] and not r.get("fecha_cierre"):
                cambios["fecha_cierre"] = date.today().isoformat()
            bd.guardar("ausencias", cambios, id_registro)
            return {"mensaje": f"Pasó a {nueva}.", "recargar": id_registro}
        if nombre == "marcar_recibido":
            bd.guardar("embudo", {"asistencia": "Asistió"}, id_registro)
            return {"mensaje": "Marcado como recibido.", "recargar": id_registro}
        if nombre == "registrar_resultado":
            r = bd.obtener("embudo", id_registro)
            fecha = logica.formatear(r["fecha"]) if r["fecha"] else ""
            heredar = [{"id": None, "archivo": x["archivo"], "origen": None,
                        "nombre": _nombre_visible(x["archivo"]), "categoria": x["categoria"]}
                       for x in bd.adjuntos_de("embudo", r["id"])]
            if r["etapa"] == "Entrevista":
                return {"navegar": {"modulo": "entrevistas", "valores": {
                    "candidato": r["nombre_completo"], "telefono": r["telefono"] or "",
                    "puesto": r.get("plaza") or "", "fecha": fecha,
                    "hora": logica.formatear_hora(r["hora"]) if r["hora"] else ""},
                    "heredar": heredar}}
            if r["etapa"] == HABIL:
                return {"navegar": {"ficha": {"candidato": r["nombre_completo"], "fecha": fecha,
                                              "puesto": r.get("plaza") or ""},
                                    "heredar": heredar}}
            return {"navegar": {"psicometrica": {"candidato": r["nombre_completo"],
                                                 "fecha": r["fecha"]}}}
        if nombre == "descartar":
            bd.guardar("embudo", {"estado": "No aprobado", "motivo": (extra.get("motivo") or "").strip() or None,
                                  "fecha_descarte": date.today().isoformat()}, id_registro)
            return {"mensaje": "Candidato pasó a No aprobados.", "limpiar": True}
        if nombre == "reactivar":
            bd.guardar("embudo", {"estado": "Activo", "motivo": None, "fecha_descarte": None},
                       id_registro)
            return {"mensaje": "Candidato regresó al embudo. Revisa su fecha y hora.",
                    "limpiar": True}
        if nombre == "descartar_registro":
            registro = bd.obtener(tabla, id_registro)
            if tabla == "entrevistas":
                etapa = "Entrevista"
                bd.guardar("entrevistas", {"resultado": "No aprobado"}, id_registro)
            else:
                etapa = registro.get("tipo_prueba") or ETAPAS[0]
            bd.descartar_candidato(registro["candidato"], etapa, (extra.get("motivo") or "").strip(),
                                   registro.get("telefono"))
            return {"mensaje": "Candidato pasó a No aprobados.", "limpiar": True}
        if nombre == "pasar_entrevista":
            nombre_c = bd.obtener("pruebas", id_registro)["candidato"]
            bd.confirmar_asistencia(nombre_c, False)
            destino = bd.pasar_a_entrevista(nombre_c)
            return {"navegar": {"modulo": "embudo", "id": destino},
                    "mensaje": "Está en Entrevista. Escribe la fecha y la hora y guarda."}
        raise ValueError(f"Acción desconocida: {nombre}")

    @seguro
    def guardar_psicometrica(self, candidato, puntaje, id_registro=None, fecha=None):
        candidato = (candidato or "").strip()
        if not candidato:
            raise ValueError("Escribe el nombre del candidato.")
        datos = {"candidato": candidato, "tipo_prueba": PSICO,
                 "puntaje": (puntaje or "").strip() or None,
                 "fecha": fecha or date.today().isoformat(),
                 "fecha_prueba": date.today().isoformat()}
        nuevo = bd.guardar("pruebas", datos, id_registro)
        bd.confirmar_asistencia(candidato, False)
        return {"id": nuevo, "mensaje": "Prueba psicométrica guardada."}

    @seguro
    def psicometrica(self, id_registro):
        r = bd.obtener("pruebas", id_registro)
        return {"candidato": r["candidato"], "puntaje": r.get("puntaje") or "", "fecha": r["fecha"]}

    # ------------------------------------------------------------------ ficha de evaluación
    @seguro
    def ficha(self, id_registro=None, prefijo=None):
        prefijo = prefijo or {}
        reg = bd.obtener("pruebas", id_registro) if id_registro else None
        if id_registro and reg is None:
            raise ValueError("La prueba ya no existe.")
        detalle = ev.desde_texto((reg or {}).get("detalle"))
        hoy = date.today().isoformat()
        r = {
            "id": id_registro, "escala": ev.ESCALA, "detalle": detalle,
            "candidato": (reg or {}).get("candidato") or prefijo.get("candidato", ""),
            "puesto": (reg or {}).get("puesto") or prefijo.get("puesto", ""),
            "fecha": logica.formatear((reg or {}).get("fecha")) if reg and reg.get("fecha")
            else prefijo.get("fecha", logica.formatear(hoy)),
            "fecha_prueba": logica.formatear(reg["fecha_prueba"]) if reg and reg.get("fecha_prueba") else "",
            "observaciones": (reg or {}).get("observaciones") or "",
            "adjuntos": self._adjuntos_de("pruebas", id_registro) if id_registro else [],
            "globales": {sec["nombre"]: sec["global"] for sec in ev.SECCIONES if sec["global"]},
        }
        return r

    @seguro
    def ficha_calcular(self, detalle):
        """Resultados por sección y promedio, para mostrarlos mientras se escribe."""
        d = self._detalle_leido(detalle, estricto=False)
        secciones = []
        for s in d["secciones"]:
            res = ev.resultado(s)
            secciones.append(None if res is None else {"puntos": res[0], "maximo": res[1],
                                                       "fraccion": res[2]})
        p = ev.promedio(d)
        return {"secciones": secciones, "promedio": p}

    def _detalle_leido(self, detalle, estricto):
        resultado = ev.vacio()
        previas = {s["nombre"]: s for s in detalle.get("secciones", [])}
        for sec in resultado["secciones"]:
            previa = previas.get(sec["nombre"], {})
            glob = previa.get("global")
            try:
                sec["global"] = ev.leer_nota(str(glob) if glob is not None else "", 10)
            except ValueError as e:
                if estricto:
                    raise ValueError(f"{sec['nombre']}: {e}")
                sec["global"] = None
            notas = {c["criterio"]: c.get("calificacion") for c in previa.get("criterios", [])}
            for c in sec["criterios"]:
                v = notas.get(c["criterio"])
                try:
                    c["calificacion"] = ev.leer_nota("" if v is None else str(v), c["maximo"])
                except ValueError as e:
                    if estricto:
                        raise ValueError(f"{c['criterio']}: {e}")
                    c["calificacion"] = None
        resultado["pendientes"] = detalle.get("pendientes", "") or ""
        return resultado

    @seguro
    def ficha_guardar(self, datos, forzar=None):
        forzar = forzar or []
        candidato = (datos.get("candidato") or "").strip()
        if not candidato:
            raise ValueError("Falta completar: Candidato.")
        t_eval, t_hecha = (datos.get("fecha") or "").strip(), (datos.get("fecha_prueba") or "").strip()
        fecha, hecha = logica.a_iso(t_eval), logica.a_iso(t_hecha)
        if (t_eval and not fecha) or (t_hecha and not hecha):
            raise ValueError("Fecha no válida. Usa dd/mm/aaaa.")
        detalle = self._detalle_leido(datos["detalle"], estricto=True)
        con_notas = ev.promedio(detalle) is not None
        if con_notas and not hecha:
            hecha = date.today().isoformat()
        fecha = fecha or hecha
        if not fecha:
            raise ValueError("Falta la fecha de evaluación.")
        if hecha and hecha > date.today().isoformat():
            raise ValueError("La fecha de la prueba no puede ser futura: es el día que la hizo.")
        id_actual = datos.get("id")
        if hecha and not con_notas and "sin_notas" not in forzar:
            return {"pregunta": "Indicaste que ya la hizo pero no escribiste calificaciones.\n"
                                "¿Guardar así?", "clave": "sin_notas"}
        if not id_actual and "repetida" not in forzar and any(
                p["fecha"] == fecha and p["candidato"].strip().lower() == candidato.lower()
                and p.get("tipo_prueba") == HABIL for p in bd.listar("pruebas")):
            return {"pregunta": f"{candidato} ya tiene una prueba de habilidades en esa fecha.\n"
                                "¿Guardar otra de todos modos?", "clave": "repetida"}
        detalle["pendientes"] = (datos.get("detalle") or {}).get("pendientes", "").strip()
        registro = {"candidato": candidato, "puesto": (datos.get("puesto") or "").strip() or None,
                    "fecha": fecha, "fecha_prueba": hecha or None, "tipo_prueba": HABIL,
                    "puntaje": ev.texto_puntaje(detalle),
                    "observaciones": (datos.get("observaciones") or "").strip() or None,
                    "detalle": ev.a_texto(detalle)}
        nuevo = bd.guardar("pruebas", registro, id_actual)
        adjuntos = datos.get("adjuntos") or []
        for a in adjuntos:
            if a.get("origen"):
                a["archivo"] = bd.copiar_archivo(a["origen"])
        actuales = {a["id"] for a in adjuntos if a.get("id")}
        for previo in bd.adjuntos_de("pruebas", nuevo):
            if previo["id"] not in actuales:
                bd.quitar_adjunto(previo["id"])
        for a in adjuntos:
            if not a.get("id"):
                bd.agregar_adjunto("pruebas", nuevo, a["archivo"], a.get("categoria", "Otro"))
        if hecha:
            bd.confirmar_asistencia(candidato, False)
        else:
            bd.reagendar_prueba(candidato, fecha)
        return {"guardado": nuevo}

    # ------------------------------------------------------------------ importar pruebas
    @seguro
    def plantilla_importacion(self):
        ruta = self._dialogo("guardar", nombre="plantilla_pruebas.xlsx",
                             tipos=("Excel (*.xlsx)", "JSON (*.json)"))
        if not ruta:
            return None
        importador.crear_plantilla(ruta)
        return {"mensaje": "Plantilla guardada.", "ruta": ruta}

    @seguro
    def importar_previa(self):
        ruta = self._dialogo("abrir", tipos=("Excel, JSON o CSV (*.xlsx;*.xlsm;*.json;*.csv)",))
        if not ruta:
            return None
        validas, errores = importador.cargar_archivo(ruta)
        nuevas, repetidas = importador.separar_repetidas(validas)
        self._importacion = nuevas

        def f(d):
            return {"candidato": d["candidato"], "puesto": d.get("puesto") or "",
                    "fecha": logica.formatear(d["fecha"]), "tipo": d.get("tipo_prueba") or "",
                    "puntaje": d.get("puntaje") or ""}
        return {"archivo": os.path.basename(ruta), "nuevas": [f(d) for d in nuevas],
                "repetidas": len(repetidas), "errores": [[n, e] for n, e in errores]}

    @seguro
    def importar_confirmar(self):
        nuevas = getattr(self, "_importacion", [])
        n = importador.guardar_pruebas(nuevas)
        self._importacion = []
        return {"mensaje": f"{n} pruebas importadas."}

    # ------------------------------------------------------------------ resumen
    @seguro
    def resumen(self):
        hoy = date.today()
        embudo = bd.listar("embudo")
        pruebas = bd.listar("pruebas")
        activos = agenda.elementos(embudo, pruebas)
        datos = agenda.resumen(activos, hoy)

        def item(r):
            return {"nombre": r["nombre_completo"], "etapa": r["etapa"],
                    "tipo": agenda.tipo(r["etapa"]), "hora": logica.formatear_hora(r["hora"])
                    if r.get("hora") else "", "telefono": r.get("telefono") or "",
                    "recibido": r.get("asistencia") == "Asistió", "id": r.get("id"),
                    "origen": r.get("origen", "embudo")}
        atras = [dict(item(r), fecha=logica.formatear(r["fecha"]),
                      dias=agenda.dias_atraso(r, hoy), texto=agenda.texto_dias(agenda.dias_atraso(r, hoy)))
                 for r in datos["atrasados"]]
        falt = bd.pendientes()
        proximos = []
        for emp in bd.listar("empleados"):
            r = logica.proximo_cumpleanos(emp["fecha_cumpleanos"], hoy) if emp.get("fecha_cumpleanos") else None
            if r and r[1] <= configuracion.PARAMETROS["dias_cumpleanos"]:
                proximos.append((r[1], r[0], emp["nombre_completo"]))
        cumples = [{"nombre": n, "dias": d,
                    "fecha": f"{f.day} de {logica.MESES[f.month - 1]}"} for d, f, n in sorted(proximos)[:5]]
        vacaciones = bd.listar("vacaciones")
        aus = bd.listar("ausencias")
        empleados = bd.listar("empleados")
        ficha_ranking = ranking.clasificar(embudo, pruebas, bd.listar("entrevistas"))
        # tendencia: pruebas y entrevistas agendadas en los próximos 14 días
        dias = []
        for i in range(14):
            d = hoy + timedelta(days=i)
            delDia = [r for r in activos if r.get("fecha") == d.isoformat()]
            dias.append({"fecha": d.isoformat(), "etiqueta": f"{d.day}/{d.month}",
                         "pruebas": sum(1 for r in delDia if agenda.tipo(r["etapa"]) == "Prueba"),
                         "entrevistas": sum(1 for r in delDia if agenda.tipo(r["etapa"]) == "Entrevista")})
        por_mes = [0] * 12
        for v in vacaciones:
            f = str(v.get("fecha_inicio") or "")
            if f.startswith(str(hoy.year)):
                por_mes[int(f[5:7]) - 1] += float(v.get("dias") or 0)
        deptos = {}
        for e in empleados:
            deptos[e.get("departamento") or "Sin departamento"] = deptos.get(
                e.get("departamento") or "Sin departamento", 0) + 1
        notas = [f for f in ficha_ranking if f["nota"] is not None]
        return {
            "hoy": [item(r) for r in datos["hoy"]], "manana": [item(r) for r in datos["manana"]],
            "conteo_hoy": datos["conteo_hoy"], "conteo_manana": datos["conteo_manana"],
            "por_venir": datos["por_venir"], "total_por_venir": datos["total_por_venir"],
            "total_activos": datos["total_activos"], "atrasados": atras,
            "pendientes": {"total": len(falt), "primeros": [
                {"tabla": p["tabla"], "id": p["id"], "referencia": p["referencia"],
                 "modulo": p["modulo"]} for p in falt[:4]]},
            "cumples": cumples, "dias_cumple": configuracion.PARAMETROS["dias_cumpleanos"],
            "tarjetas": {"empleados": len(empleados), "amonestaciones": len(bd.listar("amonestaciones")),
                         "vacaciones_anio": sum(1 for v in vacaciones
                                                if str(v.get("fecha_inicio", "")).startswith(str(hoy.year))),
                         "ausencias_abiertas": sum(1 for a in aus if a.get("etapa") != ausencias.ETAPAS[-1])},
            "graficas": {
                "agenda": dias,
                "embudo": [{"etiqueta": e, "valor": sum(1 for r in activos if r["etapa"] == e)}
                           for e in ETAPAS],
                "ranking": [{"etiqueta": f["candidato"], "valor": f["nota"], "plaza": f["plaza"]}
                            for f in notas[:8]],
                "ausencias": [{"etiqueta": e, "valor": sum(1 for a in aus if a.get("etapa") == e)}
                              for e in ausencias.ETAPAS],
                "vacaciones_mes": [{"etiqueta": m[:3].capitalize(), "valor": por_mes[i]}
                                   for i, m in enumerate(logica.MESES)],
                "departamentos": sorted([{"etiqueta": k, "valor": v} for k, v in deptos.items()],
                                        key=lambda x: -x["valor"])},
        }

    # ------------------------------------------------------------------ ranking
    def _ranking(self, plaza, incluir):
        return ranking.clasificar(bd.listar("embudo"), bd.listar("pruebas"), bd.listar("entrevistas"),
                                  None if plaza in (None, "", "Todas las plazas") else plaza, incluir)

    @seguro
    def ranking(self, plaza=None, incluir=False):
        todas = ranking.mejores_por_plaza(bd.listar("embudo"), bd.listar("pruebas"),
                                          bd.listar("entrevistas"))
        return {"plazas": ranking.PLAZAS + [ranking.SIN_PLAZA],
                "mejores": [{"plaza": p, "candidatos": v["candidatos"],
                             "mejor": None if v["mejor"] is None else
                             {"candidato": v["mejor"]["candidato"], "nota": v["mejor"]["nota"]}}
                            for p, v in todas.items()],
                "filas": [{"posicion": f["posicion"], "candidato": f["candidato"], "plaza": f["plaza"],
                           "nota": f["nota"], "etapa": f["etapa"], "entrevista": f["entrevista"]}
                          for f in self._ranking(plaza, incluir)]}

    @seguro
    def exportar_ranking(self, plaza=None, incluir=False):
        from openpyxl import Workbook
        ruta = self._dialogo("guardar", nombre="ranking_candidatos.xlsx", tipos=("Excel (*.xlsx)",))
        if not ruta:
            return None
        libro = Workbook()
        hoja = libro.active
        hoja.title = "Ranking"
        hoja.append(["#", "Candidato", "Plaza", "Nota (%)", "Etapa", "Entrevista"])
        for f in self._ranking(plaza, incluir):
            hoja.append([f["posicion"], f["candidato"], f["plaza"], f["nota"], f["etapa"], f["entrevista"]])
        for letra, ancho in zip("ABCDEF", (6, 30, 26, 10, 24, 18)):
            hoja.column_dimensions[letra].width = ancho
        libro.save(ruta)
        return {"mensaje": "Ranking exportado.", "ruta": ruta}

    # ------------------------------------------------------------------ pendientes
    @seguro
    def pendientes(self):
        return [{"tabla": p["tabla"], "modulo": p["modulo"], "id": p["id"],
                 "referencia": p["referencia"], "falta": p["falta"],
                 "fecha": logica.formatear(p["fecha"]) if p["fecha"] else ""} for p in bd.pendientes()]

    # ------------------------------------------------------------------ informes
    def _informe(self, tabla, persona, desde, hasta):
        d, h = logica.a_iso(desde) if desde else None, logica.a_iso(hasta) if hasta else None
        if (desde and not d) or (hasta and not h):
            raise ValueError("Fecha no válida. Usa dd/mm/aaaa.")
        if d and h and d > h:
            raise ValueError("La fecha «desde» es posterior a «hasta».")
        titulo, cols, filas = informes.construir(tabla, persona, d, h)
        nombre = next((n for i, n in bd.empleados_basico() if i == persona), None)
        return titulo, cols, filas, informes.subtitulo(nombre, d, h, len(filas)), nombre

    @seguro
    def informe(self, tabla, persona=None, desde="", hasta=""):
        titulo, cols, filas, sub, _ = self._informe(tabla, persona, desde, hasta)
        return {"titulo": titulo, "columnas": cols, "filas": filas, "subtitulo": sub}

    def _nombre_informe(self, titulo, persona, ext):
        base = f"{titulo}_{persona or 'todos'}_{date.today():%Y-%m-%d}".replace(" ", "_")
        return base + ext

    @seguro
    def informe_excel(self, tabla, persona=None, desde="", hasta=""):
        titulo, cols, filas, sub, nombre = self._informe(tabla, persona, desde, hasta)
        ruta = self._dialogo("guardar", nombre=self._nombre_informe(titulo, nombre, ".xlsx"),
                             tipos=("Excel (*.xlsx)",))
        if not ruta:
            return None
        informes.exportar_xlsx(ruta, titulo, cols, filas)
        return {"mensaje": "Informe exportado a Excel.", "ruta": ruta}

    @seguro
    def informe_imagen(self, tabla, persona=None, desde="", hasta="", modo="copiar"):
        titulo, cols, filas, sub, nombre = self._informe(tabla, persona, desde, hasta)
        img = informes.imagen_tabla(titulo, sub, cols, filas)
        if modo == "copiar":
            try:
                informes.copiar_imagen(img)
                return {"mensaje": f"Imagen copiada ({len(filas)} registros). Pégala con Ctrl+V."}
            except OSError as e:
                ruta = os.path.join(tempfile.gettempdir(), self._nombre_informe(titulo, nombre, ".png"))
                img.save(ruta)
                return {"mensaje": f"No se pudo copiar ({e}). Se guardó en: {ruta}", "ruta": ruta}
        ruta = self._dialogo("guardar", nombre=self._nombre_informe(titulo, nombre, ".png"),
                             tipos=("Imagen PNG (*.png)",))
        if not ruta:
            return None
        img.save(ruta)
        return {"mensaje": "Imagen guardada.", "ruta": ruta}

    # ------------------------------------------------------------------ documentos
    @seguro
    def documentos_listar(self):
        from datetime import datetime
        return [{"ruta": r, "nombre": os.path.basename(r),
                 "fecha": datetime.fromtimestamp(t).strftime("%d/%m/%Y %H:%M")}
                for r, t in documentos.listar_documentos()]

    @seguro
    def documento_leer(self, ruta):
        return documentos.leer_para_editar(ruta)

    @seguro
    def documento_guardar(self, ruta, textos):
        documentos.guardar_edicion(ruta, textos)
        return {"mensaje": "Documento guardado."}

    @seguro
    def documento_abrir(self, ruta):
        self._abrir_ruta(ruta)
        return True

    # ------------------------------------------------------------------ configuración
    @seguro
    def config_obtener(self):
        return configuracion._estado()

    @seguro
    def config_guardar(self, estado, renombres=None):
        for r in renombres or []:
            funcion = RENOMBRES.get(r["lista"])
            if funcion and r["viejo"] != r["nuevo"]:
                funcion(r["viejo"], r["nuevo"])
        for clave in ("plazas", "puestos", "tipos_ausencia", "etapas_ausencia", "departamentos",
                      "temas_memo", "categorias_adjunto"):
            if clave in estado and not [x for x in estado[clave] if str(x).strip()]:
                raise ValueError("Las listas no pueden quedar vacías.")
        try:
            dias = int(estado.get("dias_cumpleanos"))
        except (TypeError, ValueError):
            raise ValueError("Los días de aviso deben ser un número entre 1 y 365.")
        if not 1 <= dias <= 365:
            raise ValueError("Los días de aviso deben ser un número entre 1 y 365.")
        estado["dias_cumpleanos"] = dias
        for c in ("empresa", "area", "ciudad", "escala"):
            if not str(estado.get(c, "")).strip():
                raise ValueError("Completa la empresa, el área, la ciudad y la escala.")
        for s in estado.get("secciones", []):
            for crit in s["criterios"]:
                try:
                    if float(crit[1]) <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValueError(f"El máximo de «{crit[0]}» debe ser un número mayor que 0.")
        configuracion.aplicar(estado)
        configuracion.guardar()
        return configuracion._estado()

    @seguro
    def config_restablecer(self):
        configuracion.restablecer()
        return configuracion._estado()

    # ------------------------------------------------------------------ respaldos
    def _fila_respaldo(self, r):
        return {"ruta": r["ruta"], "nombre": r["nombre"], "tipo": r["tipo"],
                "fecha": r["fecha"].strftime("%d/%m/%Y %H:%M"), "tamano": r["tamano"]}

    @seguro
    def respaldos_estado(self):
        e = respaldos.verificar()
        return {"ok": e["ok"], "error": e["error"], "tablas": e["tablas"], "adjuntos": e["adjuntos"],
                "tamano": e["tamano"], "tamano_adjuntos": e["tamano_adjuntos"],
                "carpeta": bd.CARPETA_DATOS, "externa": bd.leer_config(respaldos.CLAVE_EXTERNA, ""),
                "lista": [self._fila_respaldo(r) for r in respaldos.listar_respaldos()]}

    @seguro
    def respaldo_crear(self):
        info = respaldos.crear_respaldo(os.path.join(
            respaldos.carpeta_respaldos(), respaldos.nombre_nuevo(respaldos.PREFIJO_MANUAL)))
        externo = respaldos.copiar_externo(info["ruta"])
        extra = " y en la otra carpeta" if externo else (
            " (falló la copia en la otra carpeta)" if externo is False else "")
        return {"mensaje": f"Respaldo creado{extra}.", "ok": info["ok"]}

    @seguro
    def respaldo_externa(self, quitar=False):
        if quitar:
            bd.guardar_config(respaldos.CLAVE_EXTERNA, "")
            return {"mensaje": "Se dejó de copiar a otra carpeta."}
        carpeta = self._dialogo("carpeta")
        if not carpeta:
            return None
        bd.guardar_config(respaldos.CLAVE_EXTERNA, carpeta)
        return {"mensaje": "Cada respaldo también se copiará a esa carpeta."}

    @seguro
    def respaldo_excel(self):
        ruta = self._dialogo("guardar", nombre=f"RRHH_todos_los_datos_{date.today():%Y-%m-%d}.xlsx",
                             tipos=("Excel (*.xlsx)",))
        if not ruta:
            return None
        respaldos.exportar_todo_xlsx(ruta)
        return {"mensaje": "Datos exportados a Excel."}

    @seguro
    def respaldo_guardar_como(self, ruta):
        import shutil
        destino = self._dialogo("guardar", nombre=os.path.basename(ruta), tipos=("Respaldo (*.zip)",))
        if not destino:
            return None
        shutil.copy2(ruta, destino)
        return {"mensaje": "Copia guardada."}

    @seguro
    def respaldo_elegir_archivo(self):
        return self._dialogo("abrir", tipos=("Respaldo (*.zip)",))

    @seguro
    def respaldo_restaurar(self, ruta):
        m = respaldos.restaurar(ruta)
        return {"mensaje": f"Respaldo del {str(m.get('creado', ''))[:10]} restaurado."}

    @seguro
    def respaldo_restaurar_ultimo(self):
        copias = [r for r in respaldos.listar_respaldos() if r["tipo"] != "Antes de restaurar"]
        if not copias:
            raise ValueError("No hay copias para restaurar.")
        m = respaldos.restaurar(copias[0]["ruta"])
        return {"mensaje": f"Respaldo del {str(m.get('creado', ''))[:10]} restaurado."}

    @seguro
    def abrir_carpeta_respaldos(self):
        os.makedirs(respaldos.carpeta_respaldos(), exist_ok=True)
        self._abrir_ruta(respaldos.carpeta_respaldos())
        return True

    # ------------------------------------------------------------------ actualizaciones
    @seguro
    def buscar_actualizacion(self):
        import actualizador
        try:
            datos = actualizador.buscar_nueva()
        except (OSError, ValueError) as e:
            raise ValueError(f"No se pudo consultar GitHub: {e}")
        self._actualizacion = datos
        return datos

    @seguro
    def instalar_actualizacion(self):
        import actualizador
        if not self._actualizacion:
            raise ValueError("No hay una actualización pendiente.")
        if not actualizador.puede_actualizarse():
            raise ValueError("La actualización automática solo funciona en la versión instalada.")
        actualizador.instalar_y_reiniciar(self._actualizacion)
        if self._ventana is not None:
            self._ventana.destroy()
        return True

    @seguro
    def insignias(self):
        hoy = date.today()
        datos = agenda.resumen(agenda.elementos(bd.listar("embudo"), bd.listar("pruebas")), hoy)
        return {"atrasados": len(datos["atrasados"]), "pendientes": len(bd.pendientes())}

    @seguro
    def modo(self, nuevo=None):
        if nuevo in ("claro", "oscuro"):
            bd.guardar_config("modo", nuevo)
        return bd.leer_config("modo", "claro")

    @seguro
    def cerrar(self):
        if self.alerta_base is None:
            try:
                respaldos.respaldo_automatico(horas=2)
            except Exception:
                pass
        if self._ventana is not None:
            self._ventana.destroy()
        return True
