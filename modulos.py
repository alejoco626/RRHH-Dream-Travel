import os
import re
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, simpledialog

import agenda
import ausencias
import informes
import base_datos as bd
import configuracion
import dialogo_informe
import documentos
import dialogo_importar
import importador
import logica
import ranking
import tema
from componentes import (autoformato_fecha, Boton, CajaTexto, CampoBusqueda, Combo, Etiqueta, Marco, Separador,
                         ZonaDesplazable, crear_tabla, podar)
from tkinter import ttk

DEPARTAMENTOS = configuracion.DEPARTAMENTOS
GRUPOS = configuracion.GRUPOS
TEMAS_MEMO = configuracion.TEMAS_MEMO


ETAPAS = ["Prueba de habilidades", "Pruebas psicométricas", "Entrevista"]


def abrir_ruta(ruta):
    import subprocess
    import sys
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta])
    except OSError as e:
        messagebox.showerror("No se pudo abrir", f"{ruta}\n\n{e}")


def campo(clave, etiqueta, tipo="texto", req=False, opciones=None, completo=False, pdf=False):
    return dict(clave=clave, etiqueta=etiqueta, tipo=tipo, req=req, opciones=opciones or [],
                completo=completo, pdf=pdf)


CAMPOS = {
    "empleados": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("puesto", "Puesto", "opcion", True, ranking.PUESTOS),
        campo("departamento", "Departamento", "opcion", True, DEPARTAMENTOS),
        campo("fecha_ingreso", "Fecha de ingreso (dd/mm/aaaa)", "fecha"),
        campo("fecha_cumpleanos", "Fecha de cumpleaños (dd/mm/aaaa)", "fecha"),
        campo("grupo", "Grupo de autorización de vacaciones", "opcion", False, GRUPOS,
              completo=True),
    ],
    "pruebas": [
        campo("candidato", "Candidato (elige del embudo o escribe)", "opcion", True,
              completo=True),
        campo("puesto", "Puesto"),
        campo("fecha", "Fecha de evaluación (dd/mm/aaaa)", "fecha", True),
        campo("fecha_prueba", "Fecha de la prueba (dd/mm/aaaa)", "fecha"),
        campo("tipo_prueba", "Tipo de prueba", "opcion", False,
              ["Prueba de habilidades", "Pruebas psicométricas"]),
        campo("puntaje", "Puntaje"),
        campo("observaciones", "Observaciones", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "entrevistas": [
        campo("candidato", "Nombre completo (elige del embudo o escribe)", "opcion", True,
              completo=True),
        campo("telefono", "Número de teléfono", req=True),
        campo("puesto", "Plaza", "opcion", False, ranking.PLAZAS),
        campo("fecha", "Fecha de la entrevista (dd/mm/aaaa)", "fecha", True),
        campo("hora", "Hora (ej. 10:00 o 2:30 pm)", "hora", True),
        campo("entrevistador", "Entrevistador"),
        campo("resultado", "Resultado", "opcion", False,
              ["Aprobado", "En proceso", "No aprobado"]),
        campo("observaciones", "Observaciones", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "amonestaciones": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("fecha", "Fecha (dd/mm/aaaa)", "fecha", True),
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
        campo("folio", "Folio (editable; vacío = automático)"),
        campo("fecha_solicitud", "Fecha de la solicitud (dd/mm/aaaa)", "fecha", True),
        campo("autoriza", "Autoriza", "opcion", True, completo=True),
        campo("fecha_inicio", "Primer día de goce (dd/mm/aaaa)", "fecha", True),
        campo("dias", "Días de goce (ej. 10.5)", "texto", True),
        campo("fecha_fin", "Último día de goce (dd/mm/aaaa)", "fecha", True),
        campo("fecha_regreso", "Fecha de regreso (dd/mm/aaaa)", "fecha"),
        campo("periodo_desde", "Periodo laborado desde (dd/mm/aaaa)", "fecha", True),
        campo("periodo_hasta", "Periodo laborado hasta (dd/mm/aaaa)", "fecha", True),
        campo("fecha_constancia", "Fecha de la constancia (vacía = día siguiente)", "fecha",
              completo=True),
        campo("observaciones", "Observaciones", "largo"),
        campo("archivo_solicitud", "Solicitud firmada y escaneada (PDF)", "archivo", pdf=True),
        campo("archivo_constancia", "Constancia de goce firmada y escaneada (PDF)", "archivo",
              pdf=True),
    ],
    "embudo": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("telefono", "Número de teléfono", req=True),
        campo("plaza", "Plaza", "opcion", False, ranking.PLAZAS),
        campo("etapa", "Etapa", "opcion", True, ETAPAS),
        campo("asistencia", "Asistencia", "opcion", False, agenda.ASISTENCIAS),
        campo("fecha", "Fecha de la prueba o entrevista (dd/mm/aaaa)", "fecha", True),
        campo("hora", "Hora (ej. 10:00 o 2:30 pm)", "hora", True),
        campo("notas", "Notas", "largo"),
        campo("adjuntos", "CV y archivos (PDF, Word o Excel)", "adjuntos"),
    ],
    "no_aprobados": [
        campo("nombre_completo", "Nombre completo", req=True, completo=True),
        campo("telefono", "Número de teléfono"),
        campo("etapa", "Etapa en la que quedó", "opcion", True, ETAPAS),
        campo("fecha_descarte", "Fecha en que se descartó (dd/mm/aaaa)", "fecha"),
        campo("motivo", "Motivo", "largo"),
        campo("notas", "Notas", "largo"),
    ],
    "memos": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("fecha", "Fecha (dd/mm/aaaa)", "fecha", True),
        campo("emisor", "De"),
        campo("tema", "Tema o política", "opcion", True, TEMAS_MEMO, completo=True),
        campo("observaciones", "Observaciones", "largo"),
        campo("archivo", "Memo firmado y escaneado (PDF)", "archivo", pdf=True),
    ],
    "ausencias": [
        campo("empleado_id", "Empleado", "empleado", True, completo=True),
        campo("tipo", "Tipo de ausencia", "opcion", True, ausencias.TIPOS),
        campo("etapa", "Etapa del embudo", "opcion", True, ausencias.ETAPAS),
        campo("fecha", "Primer día (dd/mm/aaaa)", "fecha", True),
        campo("fecha_fin", "Último día (vacío si fue un solo día)", "fecha"),
        campo("fecha_cierre", "Fecha de cierre (dd/mm/aaaa)", "fecha"),
        campo("motivo", "Motivo o detalle", "largo"),
        campo("archivo", "Justificante (PDF)", "archivo", pdf=True),
    ],
}

COLUMNAS = {
    "empleados": [("nombre_completo", "Nombre", 210), ("puesto", "Puesto", 150),
                  ("departamento", "Departamento", 150)],
    "pruebas": [("candidato", "Candidato", 180), ("tipo_prueba", "Tipo", 140),
                ("fecha", "F. evaluación", 100), ("situacion", "Situación", 120),
                ("fecha_prueba", "F. de la prueba", 110), ("puntaje", "Nota", 70),
                ("adjuntos", "Archivos", 90)],
    "entrevistas": [("candidato", "Nombre", 190), ("telefono", "Teléfono", 110),
                    ("fecha", "Fecha", 90), ("hora", "Hora", 80),
                    ("resultado", "Resultado", 100), ("adjuntos", "Archivos", 100)],
    "amonestaciones": [("empleado", "Empleado", 190), ("fecha", "Fecha", 90),
                       ("numero_vez", "Vez", 50), ("falta", "Falta", 190),
                       ("archivo", "Comprobante", 100)],
    "vacaciones": [("folio", "Folio", 80), ("empleado", "Empleado", 170),
                   ("fecha_inicio", "Desde", 90), ("dias", "Días", 50),
                   ("archivo_solicitud", "Solicitud", 90),
                   ("archivo_constancia", "Constancia", 90)],
    "memos": [("empleado", "Empleado", 190), ("fecha", "Fecha", 90), ("tema", "Tema", 260),
              ("archivo", "Comprobante", 100)],
    "ausencias": [("empleado", "Empleado", 170), ("tipo", "Tipo", 130), ("fecha", "Desde", 90),
                  ("dias", "Días", 50), ("etapa", "Etapa", 140),
                  ("archivo", "Justificante", 90)],
    "embudo": [("nombre_completo", "Nombre", 180), ("telefono", "Teléfono", 100),
               ("plaza", "Plaza", 140), ("etapa", "Etapa", 140), ("fecha", "Fecha", 85), ("hora", "Hora", 75),
               ("situacion", "Situación", 85), ("adjuntos", "Archivos", 85)],
    "no_aprobados": [("nombre_completo", "Nombre", 190), ("telefono", "Teléfono", 110),
                     ("etapa", "Quedó en", 160), ("motivo", "Motivo", 190),
                     ("fecha_descarte", "Descartado", 90)],
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
        return f"✓ {valor} archivo{'s' if valor != 1 else ''}" if valor else "● Pendiente"
    if clave.startswith("archivo"):
        return "✓ Listo" if valor else "● Pendiente"
    return str(valor)


def _nombre_visible(guardado):
    return re.sub(r"^\d+_", "", guardado or "")


class Pagina(Marco):
    def __init__(self, master, app, titulo, subtitulo=""):
        super().__init__(master, fondo="app")
        self.app = app
        self._es_pagina = True
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        cabecera = Marco(self, fondo="app")
        cabecera.grid(row=0, column=0, sticky="ew", padx=30, pady=(26, 18))
        cabecera.columnconfigure(0, weight=1)
        textos = Marco(cabecera, fondo="app")
        textos.grid(row=0, column=0, sticky="w")
        Etiqueta(textos, titulo, fondo="app", fuente=tema.F_TITULO).pack(anchor="w")
        Etiqueta(textos, subtitulo, fondo="app", tono="sec").pack(anchor="w", pady=(2, 0))
        self.zona_acciones = Marco(cabecera, fondo="app")
        self.zona_acciones.grid(row=0, column=1, sticky="e")
        self.cuerpo = Marco(self, fondo="app")
        self.cuerpo.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 26))

    def refrescar(self):
        pass


PERSONAL = ("empleados", "amonestaciones", "vacaciones", "memos", "ausencias")


class ModuloCrud(Pagina):
    def __init__(self, master, app, tabla, titulo, subtitulo, acciones=None,
                 acciones_cabecera=None, clave=None, estado=None, boton_nuevo=True,
                 formulario=True):
        super().__init__(master, app, titulo, subtitulo)
        self.tabla = tabla
        self.clave = clave or tabla
        self.estado = estado
        self.campos = CAMPOS[self.clave]
        self.columnas = COLUMNAS[self.clave]
        self.vars, self.textos, self.filas, self.archivos = {}, {}, {}, {}
        self.combos, self.adjuntos, self._arbol_adj = {}, [], None
        self.empleados = []
        self.personas = []
        self.filtro_persona = None
        self.combo_empleado = None
        self.combo_autoriza = None
        self.combo_categoria = None
        self._guia_goce = "fecha_fin"
        self.id_actual = None
        self.formulario = formulario
        self.acciones = acciones or []
        if boton_nuevo:
            Boton(self.zona_acciones, "+ Nuevo", self._pulsar_nuevo, fondo="app").pack(
                side="left", padx=(10, 0))
        if self.tabla in PERSONAL:
            Boton(self.zona_acciones, "Ver informes", self.ver_informes, tipo="secundario",
                  fondo="app").pack(side="left", padx=(10, 0))
        for texto, funcion, tipo in (acciones_cabecera or []):
            Boton(self.zona_acciones, texto, lambda f=funcion: f(self), tipo=tipo,
                  fondo="app").pack(side="left", padx=(10, 0))
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)
        self._crear_lista()
        if formulario:
            self._crear_formulario()
        if self.tabla == "vacaciones":
            self.vars["folio"].set(bd.siguiente_folio(date.today().year))
        if self.tabla == "embudo":
            self.vars["etapa"].set(ETAPAS[0])
            if "asistencia" in self.vars:
                self.vars["asistencia"].set(agenda.ASISTENCIAS[0])
        if self.tabla == "ausencias":
            self.vars["etapa"].set(ausencias.ETAPAS[0])
        if self.tabla == "pruebas":
            self.arbol.bind("<Double-1>", lambda e: accion_abrir_prueba(self))
        if self.tabla == "entrevistas":
            self.combos["candidato"].bind("<<ComboboxSelected>>",
                                          lambda e: self._al_elegir_candidato())

    def _crear_lista(self):
        tarjeta = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        tarjeta.grid(row=0, column=0, sticky="nsew")
        tarjeta.rowconfigure(1, weight=1)
        tarjeta.columnconfigure(0, weight=1)
        barra = Marco(tarjeta, fondo="tarjeta")
        barra.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        barra.columnconfigure(0, weight=1)
        self.buscador = CampoBusqueda(barra, "Buscar por referencia", self.refrescar)
        self.buscador.grid(row=0, column=0, sticky="ew")
        columna_total = 1
        if self.tabla in PERSONAL:
            self.v_persona = tk.StringVar(value=informes.TODAS)
            self.combo_persona = Combo(barra, [informes.TODAS], solo_lectura=True, ancho=26)
            self.combo_persona.configure(textvariable=self.v_persona)
            self.combo_persona.grid(row=0, column=1, padx=(10, 0))
            self.combo_persona.bind("<<ComboboxSelected>>", lambda e: self._elegir_persona())
            self.boton_informe_persona = Boton(barra, "Ver informes de esta persona",
                                               self.ver_informes, tipo="primario", alto=32,
                                               fuente=tema.F_PEQ_NEG)
            columna_total = 3
        self.etiqueta_total = Etiqueta(barra, "", tono="sec")
        self.etiqueta_total.grid(row=0, column=columna_total, padx=(14, 0))
        fila_tabla = 1
        if self.tabla == "ausencias":
            self.filtro_etapa = None
            self._crear_franja_ausencias(tarjeta)
            fila_tabla = 2
            tarjeta.rowconfigure(1, weight=0)
            tarjeta.rowconfigure(2, weight=1)
        cont, self.arbol = crear_tabla(tarjeta, self.columnas)
        cont.grid(row=fila_tabla, column=0, sticky="nsew", padx=(12, 4), pady=(0, 12))
        self.arbol.bind("<<TreeviewSelect>>", self._al_seleccionar)
        if not self.formulario:
            Separador(tarjeta).grid(row=2, column=0, sticky="ew")
            pie = Marco(tarjeta, fondo="tarjeta")
            pie.grid(row=3, column=0, sticky="ew", padx=16, pady=12)
            for texto, funcion, tipo in self.acciones:
                Boton(pie, texto, lambda f=funcion: f(self), tipo=tipo).pack(
                    side="left", padx=(0, 8))

    def _elegir_persona(self):
        nombre = self.v_persona.get()
        self.filtro_persona = next((i for i, n in self.personas if n == nombre), None)
        if self.filtro_persona is None:
            self.boton_informe_persona.grid_remove()
        else:
            self.boton_informe_persona.grid(row=0, column=2, padx=(10, 0))
        self.refrescar()

    def ver_informes(self):
        dialogo_informe.DialogoInforme(self.app, self.tabla, self.filtro_persona)

    def _crear_franja_ausencias(self, tarjeta):
        self.franja = Marco(tarjeta, fondo="tarjeta")
        self.franja.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.fichas_ausencia = []

    def _pintar_franja_ausencias(self, datos):
        for f in self.franja.winfo_children():
            f.destroy()
        etapas = datos["etapas"]
        mayor = max([n for _, n in etapas] + [1])
        for i, (etapa, n) in enumerate(etapas):
            self.franja.columnconfigure(i, weight=1, uniform="etapa_ausencia")
            ficha = Marco(self.franja, fondo="sel" if self.filtro_etapa == etapa else "zebra",
                          borde=True)
            ficha.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            fondo = "sel" if self.filtro_etapa == etapa else "zebra"
            cifra = Etiqueta(ficha, str(n), fondo=fondo, fuente=tema.F_SUB, anchor="center")
            cifra.pack(fill="x", pady=(8, 0))
            nombre = Etiqueta(ficha, etapa, fondo=fondo, tono="sec", fuente=tema.F_PEQ,
                              anchor="center")
            nombre.pack(fill="x", padx=4)
            pista = Marco(ficha, fondo="borde", height=5)
            pista.pack(fill="x", padx=10, pady=(6, 8))
            relleno = Marco(pista, fondo="primario")
            relleno.place(x=0, y=0, relheight=1, relwidth=n / mayor)
            for w in (ficha, cifra, nombre, pista):
                w.bind("<Button-1>", lambda e, et=etapa: self._filtrar_etapa(et))
                w.configure(cursor="hand2")

    def _filtrar_etapa(self, etapa):
        self.filtro_etapa = None if self.filtro_etapa == etapa else etapa
        self.refrescar()

    def _crear_formulario(self):
        tarjeta = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        tarjeta.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        tarjeta.rowconfigure(1, weight=1)
        tarjeta.columnconfigure(0, weight=1)
        self.titulo_form = Etiqueta(tarjeta, "Nuevo registro", fuente=tema.F_SUB)
        self.titulo_form.grid(row=0, column=0, sticky="w", padx=22, pady=(18, 4))

        zona = ZonaDesplazable(tarjeta)
        zona.grid(row=1, column=0, sticky="nsew", padx=(22, 8))
        self.zona = zona
        interior = zona.interior
        interior.columnconfigure(0, weight=1, uniform="campo")
        interior.columnconfigure(1, weight=1, uniform="campo")
        fila, col = 0, 0
        self._primer_campo = None
        for c in self.campos:
            completo = c["completo"] or c["tipo"] in ("largo", "archivo", "adjuntos")
            if completo and col == 1:
                fila += 2
                col = 0
            padx = (0, 0) if completo else ((0, 8) if col == 0 else (8, 0))
            span = 2 if completo else 1
            Etiqueta(interior, c["etiqueta"], tono="sec", fuente=tema.F_PEQ).grid(
                row=fila, column=col, columnspan=span, sticky="w", padx=padx, pady=(12, 4))
            widget = self._crear_campo(interior, c)
            widget.grid(row=fila + 1, column=col, columnspan=span, sticky="ew", padx=padx)
            if self._primer_campo is None and c["tipo"] not in ("adjuntos", "archivo"):
                self._primer_campo = widget
            if completo:
                fila += 2
                col = 0
            else:
                col += 1
                if col == 2:
                    col = 0
                    fila += 2
        Etiqueta(interior, "", tono="sec").grid(row=fila + 3, column=0, pady=4)

        Separador(tarjeta).grid(row=2, column=0, sticky="ew")
        pie = Marco(tarjeta, fondo="tarjeta")
        pie.grid(row=3, column=0, sticky="ew", padx=22, pady=16)
        botones = Marco(pie, fondo="tarjeta")
        botones.pack(fill="x")
        Boton(botones, "Guardar", self.guardar).pack(side="left")
        Boton(botones, "Limpiar", self.limpiar, tipo="secundario").pack(side="left", padx=8)
        Boton(botones, "Eliminar", self.eliminar, tipo="peligro").pack(side="right")
        if self.acciones:
            rejilla = Marco(pie, fondo="tarjeta")
            rejilla.pack(fill="x", pady=(4, 0))
            rejilla.columnconfigure((0, 1), weight=1, uniform="accion")
            for i, (texto, funcion) in enumerate(self.acciones):
                ultimo_solo = i == len(self.acciones) - 1 and len(self.acciones) % 2 == 1
                Boton(rejilla, texto, lambda f=funcion: f(self), tipo="secundario").grid(
                    row=i // 2, column=0 if ultimo_solo else i % 2,
                    columnspan=2 if ultimo_solo else 1, sticky="ew",
                    padx=(0, 4) if i % 2 == 0 and not ultimo_solo else (4, 0) if
                    i % 2 == 1 else 0, pady=(8, 0))

    def _crear_campo(self, padre, c):
        tipo, clave = c["tipo"], c["clave"]
        if tipo == "largo":
            caja = CajaTexto(padre)
            self.textos[clave] = caja
            return caja
        if tipo == "archivo":
            return self._crear_campo_archivo(padre, c)
        if tipo == "adjuntos":
            return self._crear_campo_adjuntos(padre)
        var = tk.StringVar()
        self.vars[clave] = var
        if tipo == "opcion":
            w = Combo(padre, c["opciones"])
            w.configure(textvariable=var)
            if clave == "autoriza":
                self.combo_autoriza = w
            self.combos[clave] = w
            return w
        if tipo == "empleado":
            w = Combo(padre, solo_lectura=True)
            w.configure(textvariable=var)
            w.bind("<<ComboboxSelected>>", lambda e: self._al_elegir_empleado())
            self.combo_empleado = w
            return w
        w = ttk.Entry(padre, textvariable=var, style="Moderno.TEntry", width=20)
        if tipo == "fecha":
            autoformato_fecha(w)
        if self.tabla == "vacaciones" and clave in self.CLAVES_GOCE:
            w.bind("<KeyRelease>", lambda e, k=clave: self._recalcular(k), add="+")
        return w

    def _crear_campo_archivo(self, padre, c):
        clave = c["clave"]
        estado = {"var": tk.StringVar(), "actual": "", "origen": None, "pdf": c["pdf"]}
        self.archivos[clave] = estado
        marco = Marco(padre, fondo="tarjeta")
        marco.columnconfigure(0, weight=1)
        ttk.Entry(marco, textvariable=estado["var"], state="readonly",
                  style="Moderno.TEntry", width=20).grid(row=0, column=0, columnspan=3,
                                                          sticky="ew")
        fila = Marco(marco, fondo="tarjeta")
        fila.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        Boton(fila, "Adjuntar PDF" if c["pdf"] else "Adjuntar", lambda k=clave: self.adjuntar(k),
              tipo="secundario", alto=32, fuente=tema.F_PEQ_NEG).pack(side="left")
        Boton(fila, "Ver", lambda k=clave: self.abrir_archivo(k), tipo="secundario", alto=32,
              fuente=tema.F_PEQ_NEG).pack(side="left", padx=6)
        Boton(fila, "Quitar", lambda k=clave: self.quitar_archivo(k), tipo="fantasma",
              alto=32, fuente=tema.F_PEQ_NEG).pack(side="left")
        return marco

    def _crear_campo_adjuntos(self, padre):
        marco = Marco(padre, fondo="tarjeta")
        marco.columnconfigure(0, weight=1)
        cont, self._arbol_adj = crear_tabla(marco, [("nombre", "Documento", 250),
                                                    ("categoria", "Tipo", 110)])
        self._arbol_adj.configure(height=4)
        cont.grid(row=0, column=0, sticky="ew")
        fila = Marco(marco, fondo="tarjeta")
        fila.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.var_categoria = tk.StringVar(value=bd.CATEGORIAS_ADJUNTO[0])
        combo = Combo(fila, bd.CATEGORIAS_ADJUNTO, solo_lectura=True, ancho=14)
        combo.configure(textvariable=self.var_categoria)
        self.combo_categoria = combo
        combo.pack(side="left")
        for texto, funcion, tipo in (("Agregar archivos", self.agregar_adjuntos, "secundario"),
                                     ("Ver", self.ver_adjunto, "secundario"),
                                     ("Quitar", self.quitar_adjunto, "fantasma")):
            Boton(fila, texto, funcion, tipo=tipo, alto=32, fuente=tema.F_PEQ_NEG).pack(
                side="left", padx=(8, 0))
        return marco

    def _pintar_adjuntos(self):
        if self._arbol_adj is None:
            return
        self._arbol_adj.delete(*self._arbol_adj.get_children())
        for i, a in enumerate(self.adjuntos):
            self._arbol_adj.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                                   values=(_nombre_visible(a["nombre"]), a["categoria"]))

    def agregar_adjuntos(self):
        rutas = filedialog.askopenfilenames(
            title="Elegir CV o archivos (puedes elegir varios)",
            filetypes=[("PDF, Word y Excel", "*.pdf *.doc *.docx *.xls *.xlsx *.xlsm"),
                       ("Todos los archivos", "*.*")])
        rechazados = []
        for ruta in rutas:
            if not ruta.lower().endswith(bd.EXT_ADJUNTOS):
                rechazados.append(os.path.basename(ruta))
                continue
            self.adjuntos.append({"id": None, "archivo": "", "origen": ruta,
                                  "nombre": os.path.basename(ruta),
                                  "categoria": self.var_categoria.get() or "Otro"})
        self._pintar_adjuntos()
        if rechazados:
            messagebox.showwarning("Archivos no válidos",
                                   "Solo se aceptan PDF, Word y Excel. No se agregaron:\n"
                                   + "\n".join(rechazados))

    def _adjunto_elegido(self):
        seleccion = self._arbol_adj.selection()
        return int(seleccion[0]) if seleccion else None

    def ver_adjunto(self):
        i = self._adjunto_elegido()
        if i is None:
            messagebox.showinfo("Archivos", "Selecciona un archivo de la lista.")
            return
        a = self.adjuntos[i]
        abrir_ruta(a["origen"] or bd.ruta_archivo(a["archivo"]))

    def quitar_adjunto(self):
        i = self._adjunto_elegido()
        if i is None:
            messagebox.showinfo("Archivos", "Selecciona el archivo que quieres quitar.")
            return
        self.adjuntos.pop(i)
        self._pintar_adjuntos()

    def _pulsar_nuevo(self):
        self.nuevo()
        self.app.avisar_cambio("Formulario nuevo: completa los datos y pulsa Guardar.", "info")

    def _al_elegir_candidato(self):
        nombre = self.vars["candidato"].get().strip().lower()
        for r in bd.listar("embudo"):
            if r["nombre_completo"].strip().lower() == nombre:
                if not self.vars["telefono"].get() and r.get("telefono"):
                    self.vars["telefono"].set(r["telefono"])
                break

    def nuevo(self, valores=None, heredar=None):
        self.limpiar()
        for clave, valor in (valores or {}).items():
            if clave in self.vars:
                self.vars[clave].set(valor)
        if heredar:
            self.adjuntos = [dict(a) for a in heredar]
            self._pintar_adjuntos()
        self.zona.lienzo.yview_moveto(0)
        primero = next(iter(self.combos.values()), None) if self.combos else None
        try:
            (self._primer_campo or primero).focus_set()
        except (AttributeError, tk.TclError):
            pass

    def refrescar(self):
        if self.combo_empleado is not None:
            self.empleados = bd.empleados_basico()
            self.combo_empleado.configure(values=[f"{i} - {n}" for i, n in self.empleados])
        if self.tabla in PERSONAL:
            self.personas = bd.empleados_basico()
            self.combo_persona.configure(values=[informes.TODAS] + [n for _, n in self.personas])
            if self.filtro_persona is not None and self.filtro_persona not in dict(self.personas):
                self.filtro_persona = None
                self.v_persona.set(informes.TODAS)
                self.boton_informe_persona.grid_remove()
        if "candidato" in self.combos:
            nombres = sorted({r["nombre_completo"] for r in bd.listar("embudo")})
            self.combos["candidato"].configure(values=nombres)
        for c in self.campos:
            if c["tipo"] == "opcion" and c["opciones"] and c["clave"] in self.combos:
                self.combos[c["clave"]].configure(values=list(c["opciones"]))
        if self.combo_categoria is not None:
            self.combo_categoria.configure(values=list(bd.CATEGORIAS_ADJUNTO))
        self.arbol.delete(*self.arbol.get_children())
        self.filas = {}
        registros = bd.listar(self.tabla, self.buscador.texto())
        if any(c[0] == "adjuntos" for c in self.columnas):
            conteos = bd.conteo_adjuntos(self.tabla)
            for r in registros:
                r["adjuntos"] = conteos.get(r["id"], 0)
        if self.filtro_persona is not None:
            clave = "id" if self.tabla == "empleados" else "empleado_id"
            registros = [r for r in registros if r.get(clave) == self.filtro_persona]
        if self.tabla == "ausencias":
            self._pintar_franja_ausencias(ausencias.embudo(registros))
            if self.filtro_etapa:
                registros = [r for r in registros if r.get("etapa") == self.filtro_etapa]
        if self.estado:
            registros = [r for r in registros if r.get("estado") == self.estado]
        if any(c[0] == "situacion" for c in self.columnas):
            hoy = date.today()
            for r in registros:
                r["situacion"] = (agenda.situacion_prueba(r, hoy) if self.tabla == "pruebas"
                                  else agenda.situacion(r, hoy))
        if self.estado == "Activo":
            registros.sort(key=lambda r: (r.get("fecha") or "9999", r.get("hora") or ""))
        for n, fila in enumerate(registros):
            self.filas[fila["id"]] = fila
            etiquetas = ["par" if n % 2 == 0 else "impar"]
            if str(fila.get("situacion", "")).startswith("Atrasad"):
                etiquetas.append("atrasado")
            self.arbol.insert("", "end", iid=str(fila["id"]),
                              values=[_mostrar(c[0], fila.get(c[0])) for c in self.columnas],
                              tags=tuple(etiquetas))
        total = len(self.filas)
        if self.estado == "Activo":
            por_etapa = [f"{sum(1 for f in self.filas.values() if f['etapa'] == e)} {c}"
                         for e, c in zip(ETAPAS, ("habilidades", "psicométricas", "entrevista"))]
            self.etiqueta_total.configure(text=f"{total} en el embudo  ·  " + "  ·  ".join(por_etapa))
        elif self.tabla == "ausencias":
            texto = f"{total} registro{'s' if total != 1 else ''}"
            if self.filtro_etapa:
                texto += f"  ·  filtrado: {self.filtro_etapa} (clic de nuevo para quitar)"
            self.etiqueta_total.configure(text=texto)
        else:
            self.etiqueta_total.configure(text=f"{total} registro{'s' if total != 1 else ''}")
        if self.id_actual in self.filas:
            self.arbol.selection_set(str(self.id_actual))

    def seleccionar(self, id_registro):
        self.refrescar()
        if id_registro in self.filas:
            self.arbol.selection_set(str(id_registro))
            self.arbol.see(str(id_registro))
            self.cargar(self.filas[id_registro])

    def _al_seleccionar(self, _evento=None):
        seleccion = self.arbol.selection()
        if seleccion:
            self.cargar(self.filas[int(seleccion[0])])

    def _texto_empleado(self, id_empleado):
        for i, n in self.empleados:
            if i == id_empleado:
                return f"{i} - {n}"
        return ""

    def cargar(self, fila):
        self.id_actual = fila["id"]
        if not self.formulario:
            return
        self.titulo_form.configure(text="Editando registro")
        for c in self.campos:
            k, t, v = c["clave"], c["tipo"], fila.get(c["clave"])
            if t == "largo":
                self.textos[k].delete("1.0", "end")
                self.textos[k].insert("1.0", v or "")
            elif t == "archivo":
                a = self.archivos[k]
                a["actual"], a["origen"] = v or "", None
                a["var"].set(_nombre_visible(a["actual"]))
            elif t == "adjuntos":
                self.adjuntos = [{"id": x["id"], "archivo": x["archivo"], "origen": None,
                                  "nombre": x["archivo"], "categoria": x["categoria"]}
                                 for x in bd.adjuntos_de(self.tabla, fila["id"])]
                self._pintar_adjuntos()
            elif t == "empleado":
                self.vars[k].set(self._texto_empleado(v))
            elif t == "fecha":
                self.vars[k].set(logica.formatear(v) if v else "")
            elif t == "hora":
                self.vars[k].set(logica.formatear_hora(v) if v else "")
            elif k == "dias":
                self.vars[k].set("" if v is None else logica.texto_dias(v))
            else:
                self.vars[k].set("" if v is None else str(v))
        if self.tabla == "vacaciones":
            self._poner_regreso()

    def limpiar(self):
        self.id_actual = None
        if not self.formulario:
            return
        self.titulo_form.configure(text="Nuevo registro")
        for c in self.campos:
            k, t = c["clave"], c["tipo"]
            if t == "largo":
                self.textos[k].delete("1.0", "end")
            elif t == "archivo":
                self.quitar_archivo(k)
            elif t == "adjuntos":
                self.adjuntos = []
                self._pintar_adjuntos()
            else:
                self.vars[k].set("")
        seleccionadas = self.arbol.selection()
        if seleccionadas:
            self.arbol.selection_remove(*seleccionadas)
        if self.tabla == "vacaciones":
            self.vars["folio"].set(bd.siguiente_folio(date.today().year))
        if self.tabla == "amonestaciones":
            self.vars["firmante"].set(bd.leer_config("ultimo_firmante", ""))
            self.vars["cargo_firmante"].set(bd.leer_config("ultimo_cargo", ""))
            self.vars["numero_vez"].set("1")
        if self.tabla == "memos":
            self.vars["emisor"].set(bd.leer_config("ultimo_emisor_memo", ""))
        if self.tabla == "ausencias":
            self.vars["etapa"].set(ausencias.ETAPAS[0])
        if self.tabla == "embudo":
            self.vars["etapa"].set(ETAPAS[0])
            if "asistencia" in self.vars:
                self.vars["asistencia"].set(agenda.ASISTENCIAS[0])

    def leer(self):
        datos = {}
        for c in self.campos:
            k, t = c["clave"], c["tipo"]
            if t in ("archivo", "adjuntos") or k == "fecha_regreso":
                continue
            v = self.textos[k].get("1.0", "end").strip() if t == "largo" \
                else self.vars[k].get().strip()
            if c["req"] and not v:
                if t == "empleado" and not self.empleados:
                    raise ValueError("Primero registra al empleado en la sección Empleados.")
                raise ValueError(f"Falta completar: {c['etiqueta']}.")
            if t == "fecha" and v:
                v = logica.a_iso(v)
                if not v:
                    raise ValueError(f"Fecha no válida en: {c['etiqueta']}.")
            elif t == "hora" and v:
                v = logica.parsear_hora(v)
                if not v:
                    raise ValueError(f"Hora no válida en: {c['etiqueta']}. Escribe por ejemplo "
                                     f"10:00 o 2:30 pm.")
            elif t == "empleado":
                v = int(v.split(" - ")[0])
            elif k == "numero_vez":
                v = int(v)
            datos[k] = v if v not in ("", None) else None
        if self.tabla == "ausencias":
            dias = ausencias.dias_de(datos["fecha"], datos.get("fecha_fin"))
            if dias is None:
                raise ValueError("El último día es anterior al primero.")
            datos["dias"] = dias
            if datos.get("fecha_cierre") and datos["fecha_cierre"] < datos["fecha"]:
                raise ValueError("La fecha de cierre es anterior a la ausencia.")
        if self.tabla == "vacaciones":
            if datos["fecha_fin"] < datos["fecha_inicio"]:
                raise ValueError("El último día de goce es anterior al primero.")
            if datos["periodo_hasta"] < datos["periodo_desde"]:
                raise ValueError("El periodo laborado es inválido (hasta < desde).")
            datos["dias"] = logica.leer_dias(datos["dias"])
            if datos["dias"] != logica.dias_vacaciones(datos["fecha_inicio"], datos["fecha_fin"]):
                raise ValueError("Los días de goce no coinciden con las fechas. Cambia los "
                                 "días, el último día o la fecha de regreso y se ajustan solos.")
            if datos["folio"] and any(
                    v["folio"] == datos["folio"] and v["id"] != self.id_actual
                    for v in bd.listar("vacaciones")):
                raise ValueError(f"El folio {datos['folio']} ya existe. Escribe otro.")
        return datos

    def guardar(self):
        try:
            datos = self.leer()
        except ValueError as e:
            messagebox.showwarning("Revisar datos", str(e))
            return False
        for clave, a in self.archivos.items():
            if a["origen"]:
                try:
                    datos[clave] = bd.copiar_archivo(a["origen"])
                except OSError as e:
                    messagebox.showerror("No se pudo adjuntar el archivo", str(e))
                    return False
            else:
                datos[clave] = a["actual"]
        for a in self.adjuntos:
            if a["origen"]:
                try:
                    a["archivo"] = bd.copiar_archivo(a["origen"])
                except OSError as e:
                    messagebox.showerror("No se pudo adjuntar el archivo", str(e))
                    return False
                a["origen"] = None
        if self.tabla == "embudo" and self.id_actual is None:
            datos["estado"] = self.estado or "Activo"
        if self.tabla == "vacaciones" and not datos.get("folio"):
            datos["folio"] = bd.siguiente_folio(datos["fecha_solicitud"][:4])
        try:
            self.id_actual = bd.guardar(self.tabla, datos, self.id_actual)
        except sqlite3.IntegrityError as e:
            messagebox.showwarning("No se pudo guardar", str(e))
            return False
        if self._arbol_adj is not None:
            actuales = {a["id"] for a in self.adjuntos if a["id"]}
            for previo in bd.adjuntos_de(self.tabla, self.id_actual):
                if previo["id"] not in actuales:
                    bd.quitar_adjunto(previo["id"])
            for a in self.adjuntos:
                if not a["id"]:
                    a["id"] = bd.agregar_adjunto(self.tabla, self.id_actual, a["archivo"],
                                                 a["categoria"])
        if self.tabla == "amonestaciones":
            bd.guardar_config("ultimo_firmante", datos["firmante"])
            bd.guardar_config("ultimo_cargo", datos["cargo_firmante"])
        if self.tabla in ("pruebas", "entrevistas"):
            bd.confirmar_asistencia(datos["candidato"], self.tabla == "entrevistas")
        if self.tabla == "memos" and datos.get("emisor"):
            bd.guardar_config("ultimo_emisor_memo", datos["emisor"])
        guardado = self.id_actual
        self.refrescar()
        self.cargar(bd.obtener(self.tabla, guardado))
        self.app.avisar_cambio("Guardado.")
        return True

    def eliminar(self):
        if self.id_actual is None:
            messagebox.showinfo("Eliminar", "Selecciona un registro de la lista.")
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar este registro?"):
            return
        try:
            bd.eliminar(self.tabla, self.id_actual)
        except sqlite3.IntegrityError:
            messagebox.showwarning(
                "No se puede eliminar",
                "Este empleado tiene amonestaciones, vacaciones o memos registrados.")
            return
        self.limpiar()
        self.refrescar()
        self.app.avisar_cambio("Eliminado.")

    def adjuntar(self, clave):
        a = self.archivos[clave]
        tipos = [("PDF", "*.pdf")] if a["pdf"] else [("Todos los archivos", "*.*")]
        ruta = filedialog.askopenfilename(title="Elegir archivo", filetypes=tipos)
        if not ruta:
            return
        if a["pdf"] and not ruta.lower().endswith(".pdf"):
            messagebox.showwarning("Archivo no válido", "Sube el comprobante escaneado en PDF.")
            return
        a["origen"] = ruta
        a["var"].set(os.path.basename(ruta) + "  (sin guardar)")

    def abrir_archivo(self, clave):
        a = self.archivos[clave]
        if a["origen"]:
            abrir_ruta(a["origen"])
        elif a["actual"]:
            abrir_ruta(bd.ruta_archivo(a["actual"]))

    def quitar_archivo(self, clave):
        a = self.archivos[clave]
        a["origen"], a["actual"] = None, ""
        a["var"].set("")

    def _al_elegir_empleado(self):
        if self.tabla != "vacaciones":
            return
        self._sugerir_autoriza()
        self.sugerir_periodo(avisar=False)

    def _empleado_elegido(self):
        texto = self.vars["empleado_id"].get()
        return bd.obtener("empleados", int(texto.split(" - ")[0])) if texto else None

    def _sugerir_autoriza(self):
        emp = self._empleado_elegido()
        opciones = logica.autorizadores(emp.get("grupo")) if emp else []
        if self.combo_autoriza is not None:
            self.combo_autoriza.configure(values=opciones)
        if opciones:
            self.vars["autoriza"].set(opciones[0])

    CLAVES_GOCE = ("fecha_inicio", "dias", "fecha_fin", "fecha_regreso")

    def _poner_regreso(self):
        try:
            self.vars["fecha_regreso"].set(
                logica.formatear(logica.fecha_regreso(self.vars["fecha_fin"].get())))
        except ValueError:
            self.vars["fecha_regreso"].set("")

    def _recalcular(self, origen):
        v = self.vars
        if origen == "fecha_inicio":
            origen = self._guia_goce
        else:
            self._guia_goce = origen
        try:
            inicio = logica.parsear_fecha(v["fecha_inicio"].get())
            if inicio is None:
                return
            if origen == "dias":
                fin = logica.fecha_fin_por_dias(inicio, logica.leer_dias(v["dias"].get()))
            elif origen == "fecha_regreso":
                fin = logica.ultimo_dia_antes_de(v["fecha_regreso"].get(), inicio)
            else:
                fin = logica.parsear_fecha(v["fecha_fin"].get())
                if fin is None:
                    return
            dias = logica.dias_vacaciones(inicio, fin)
        except ValueError:
            return
        if origen != "dias":
            v["dias"].set(logica.texto_dias(dias))
        if origen != "fecha_fin":
            v["fecha_fin"].set(logica.formatear(fin))
        if origen != "fecha_regreso":
            v["fecha_regreso"].set(logica.formatear(logica.fecha_regreso(fin)))

    def sugerir_periodo(self, avisar=True):
        emp = self._empleado_elegido()
        referencia = self.vars["fecha_inicio"].get() or self.vars["fecha_solicitud"].get()
        if not emp or not emp.get("fecha_ingreso") or not logica.parsear_fecha(referencia):
            if avisar:
                messagebox.showinfo(
                    "Periodo laborado",
                    "Para calcularlo elige el empleado (con su fecha de ingreso registrada) "
                    "y el primer día de goce.")
            return
        periodo = logica.periodo_vencido(emp["fecha_ingreso"], referencia)
        if periodo is None:
            if avisar:
                messagebox.showinfo("Periodo laborado",
                                    "El empleado aún no cumple un año de trabajo.")
            return
        self.vars["periodo_desde"].set(logica.formatear(periodo[0]))
        self.vars["periodo_hasta"].set(logica.formatear(periodo[1]))


def _generar(modulo, funcion, mensaje):
    if not modulo.guardar():
        return
    try:
        ruta = funcion(bd.obtener(modulo.tabla, modulo.id_actual))
    except (ValueError, OSError, KeyError) as e:
        messagebox.showerror("No se pudo crear el documento", str(e))
        return
    modulo.app.avisar_cambio(mensaje)
    modulo.app.ver_documento(ruta)


def accion_solicitud(m):
    _generar(m, documentos.generar_solicitud_vacaciones, "Solicitud creada.")


def accion_constancia(m):
    _generar(m, documentos.generar_constancia_vacaciones, "Constancia creada.")


def accion_amonestacion(m):
    _generar(m, documentos.generar_amonestacion, "Carta de amonestación creada.")


def accion_periodo(m):
    m.sugerir_periodo()


def accion_mover_etapa(m):
    actual = m.vars["etapa"].get()
    if actual == ETAPAS[-1]:
        messagebox.showinfo("Embudo", "El candidato ya está en la última etapa (Entrevista).")
        return
    if not m.guardar():
        return
    siguiente = ETAPAS[(ETAPAS.index(actual) if actual in ETAPAS else 0) + 1]
    bd.guardar("embudo", {"etapa": siguiente, "fecha": None, "hora": None,
                          "asistencia": "Pendiente"}, m.id_actual)
    m.refrescar()
    m.cargar(bd.obtener("embudo", m.id_actual))
    m.app.avisar_cambio(f"Pasó a {siguiente}. Escribe la fecha y la hora de esta etapa.", "info")


def accion_avanzar_ausencia(m):
    if m.id_actual is None:
        messagebox.showinfo("Ausencias", "Selecciona primero la ausencia en la lista.")
        return
    actual = m.vars["etapa"].get()
    if actual == ausencias.ETAPAS[-1]:
        messagebox.showinfo("Ausencias", "Esta ausencia ya está en la última etapa.")
        return
    nueva = ausencias.siguiente(actual)
    m.vars["etapa"].set(nueva)
    if nueva == ausencias.ETAPAS[-1] and not m.vars["fecha_cierre"].get().strip():
        m.vars["fecha_cierre"].set(logica.formatear(date.today().isoformat()))
    if m.guardar():
        m.app.avisar_cambio(f"Pasó a {nueva}.", "info")


def accion_marcar_recibido(m):
    if m.id_actual is None:
        messagebox.showinfo("Embudo", "Selecciona primero al candidato en la lista.")
        return
    bd.guardar("embudo", {"asistencia": "Asistió"}, m.id_actual)
    m.refrescar()
    m.cargar(bd.obtener("embudo", m.id_actual))
    m.app.avisar_cambio("Marcado como recibido.")


def accion_registrar_resultado(m):
    if not m.guardar():
        return
    r = bd.obtener("embudo", m.id_actual)
    fecha = logica.formatear(r["fecha"]) if r["fecha"] else ""
    heredar = [{"id": None, "archivo": x["archivo"], "origen": None, "nombre": x["archivo"],
                "categoria": x["categoria"]} for x in bd.adjuntos_de("embudo", r["id"])]
    if r["etapa"] == "Entrevista":
        m.app.nuevo_en("entrevistas", {
            "candidato": r["nombre_completo"], "telefono": r["telefono"] or "",
            "puesto": r.get("plaza") or "",
            "fecha": fecha, "hora": logica.formatear_hora(r["hora"])}, heredar)
    elif r["etapa"] == "Prueba de habilidades":
        m.app.abrir_ficha(valores={"candidato": r["nombre_completo"], "fecha": r["fecha"],
                                   "puesto": r.get("plaza")},
                          heredar=heredar)
    else:
        _registrar_psicometrica(m, r["nombre_completo"], r["fecha"])


def accion_nueva_habilidades(m):
    m.app.abrir_ficha()


def _registrar_psicometrica(m, candidato="", fecha=None, registro=None):
    nombre = simpledialog.askstring(
        "Pruebas psicométricas", "Candidato:", initialvalue=candidato, parent=m.app)
    if not nombre or not nombre.strip():
        return
    previo = (registro or {}).get("puntaje") or ""
    puntaje = simpledialog.askstring(
        "Pruebas psicométricas", "Puntaje o resultado (ej. 78 o 78 %):",
        initialvalue=previo, parent=m.app)
    if puntaje is None:
        return
    datos = {"candidato": nombre.strip(), "tipo_prueba": "Pruebas psicométricas",
             "puntaje": puntaje.strip() or None,
             "fecha": fecha or date.today().isoformat(),
             "fecha_prueba": date.today().isoformat()}
    id_registro = bd.guardar("pruebas", datos, registro["id"] if registro else None)
    bd.confirmar_asistencia(datos["candidato"], False)
    m.app.avisar_cambio("Prueba psicométrica guardada.")
    m.seleccionar(id_registro)


def accion_nueva_psicometrica(m):
    _registrar_psicometrica(m)


def accion_eliminar(m):
    m.eliminar()


def accion_abrir_prueba(m):
    if m.id_actual is None:
        messagebox.showinfo("Abrir prueba", "Selecciona una prueba de la lista.")
        return
    registro = bd.obtener("pruebas", m.id_actual)
    if registro.get("tipo_prueba") == "Pruebas psicométricas":
        _registrar_psicometrica(m, registro["candidato"], registro["fecha"], registro)
    else:
        m.app.abrir_ficha(registro=registro)


def accion_pasar_a_entrevista(m):
    if m.id_actual is None:
        messagebox.showinfo("Pasar a entrevista", "Selecciona primero una prueba de la lista.")
        return
    nombre = bd.obtener("pruebas", m.id_actual)["candidato"]
    bd.confirmar_asistencia(nombre, False)
    destino = bd.pasar_a_entrevista(nombre)
    m.app.ir_a("embudo", destino)
    m.app.avisar_cambio("Está en Entrevista. Escribe la fecha y la hora y guarda.", "info")


def accion_descartar_registro(m):
    if m.id_actual is None:
        messagebox.showinfo("Descartar", "Selecciona primero un registro de la lista.")
        return
    registro = bd.obtener(m.tabla, m.id_actual)
    motivo = simpledialog.askstring(
        "Descartar candidato",
        f"Motivo por el que {registro['candidato']} no continúa (opcional).\n"
        "Pasará a No aprobados:", parent=m.app)
    if motivo is None:
        return
    if m.tabla == "entrevistas":
        etapa = "Entrevista"
        bd.guardar("entrevistas", {"resultado": "No aprobado"}, m.id_actual)
    else:
        etapa = registro.get("tipo_prueba") or ETAPAS[0]
    bd.descartar_candidato(registro["candidato"], etapa, motivo.strip(),
                           registro.get("telefono"))
    m.limpiar()
    m.refrescar()
    m.app.avisar_cambio("Candidato pasó a No aprobados.", "info")


def accion_descartar(m):
    if m.id_actual is None:
        messagebox.showinfo("Descartar", "Selecciona primero al candidato en la lista.")
        return
    motivo = simpledialog.askstring(
        "Descartar candidato",
        "Motivo por el que no continúa (opcional).\nPasará a la sección No aprobados:",
        parent=m.app)
    if motivo is None:
        return
    bd.guardar("embudo", {"estado": "No aprobado", "motivo": motivo.strip() or None,
                          "fecha_descarte": date.today().isoformat()}, m.id_actual)
    m.limpiar()
    m.refrescar()
    m.app.avisar_cambio("Candidato pasó a No aprobados.", "info")


def accion_reactivar(m):
    if m.id_actual is None:
        messagebox.showinfo("Reactivar", "Selecciona primero al candidato en la lista.")
        return
    bd.guardar("embudo", {"estado": "Activo", "motivo": None, "fecha_descarte": None},
               m.id_actual)
    m.limpiar()
    m.refrescar()
    m.app.avisar_cambio("Candidato regresó al embudo. Revisa su fecha y hora.", "info")


def accion_plantilla_importacion(m):
    ruta = filedialog.asksaveasfilename(
        title="Guardar plantilla de importación", defaultextension=".xlsx",
        initialfile="plantilla_pruebas.xlsx",
        filetypes=[("Excel", "*.xlsx"), ("JSON", "*.json")])
    if not ruta:
        return
    try:
        importador.crear_plantilla(ruta)
    except (ValueError, OSError) as e:
        messagebox.showerror("No se pudo crear la plantilla", str(e))
        return
    m.app.avisar_cambio("Plantilla guardada.")


def accion_importar_pruebas(m):
    ruta = filedialog.askopenfilename(
        title="Importar pruebas",
        filetypes=[("Excel, JSON o CSV", "*.xlsx *.xlsm *.json *.csv"), ("Todos", "*.*")])
    if not ruta:
        return
    try:
        validas, errores = importador.cargar_archivo(ruta)
    except (ValueError, OSError) as e:
        messagebox.showerror("No se pudo leer el archivo", str(e))
        return
    nuevas, repetidas = importador.separar_repetidas(validas)

    def confirmar():
        try:
            cantidad = importador.guardar_pruebas(nuevas)
        except sqlite3.Error as e:
            messagebox.showerror("No se pudo importar", str(e))
            return
        m.refrescar()
        m.app.avisar_cambio(f"{cantidad} pruebas importadas.")

    dialogo_importar.DialogoImportacion(m.app, ruta, nuevas, repetidas, errores, confirmar)


class Resumen(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Resumen", "Agenda de pruebas y entrevistas, y estado de RRHH")
        self.cuerpo.columnconfigure((0, 1, 2), weight=1, uniform="col")
        self.cuerpo.rowconfigure((1, 2), weight=1)
        self.hoy = self._tarjeta_dia(0)
        self.manana = self._tarjeta_dia(1)
        self.global_ = self._tarjeta(0, 2, "Pruebas y entrevistas por venir", "primario")
        self.atrasados = self._tarjeta(1, 0, "Atrasados sin confirmar", "acento", columnas=2)
        self.pendientes = self._tarjeta(1, 2, "Archivos pendientes", "acento")
        self.cumples = self._tarjeta(2, 0, "Próximos cumpleaños", "primario", columnas=2)
        self.personal = self._tarjeta(2, 2, "Personal", "primario")

    def _tarjeta(self, fila, columna, titulo, color, columnas=1):
        tarjeta = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        tarjeta.grid(row=fila, column=columna, columnspan=columnas, sticky="nsew",
                     padx=(0 if columna == 0 else 8, 0 if columna + columnas == 3 else 8),
                     pady=(0, 14))
        Marco(tarjeta, fondo=color, height=3).pack(fill="x")
        Etiqueta(tarjeta, titulo, fuente=tema.F_SUB).pack(anchor="w", padx=18, pady=(12, 6))
        interior = Marco(tarjeta, fondo="tarjeta")
        interior.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        return interior

    def _tarjeta_dia(self, columna):
        return self._tarjeta(0, columna, "Hoy" if columna == 0 else "Mañana", "primario")

    @staticmethod
    def _vaciar(contenedor):
        for w in contenedor.winfo_children():
            w.destroy()

    @staticmethod
    def _fila(contenedor, *textos, negrita_primero=True):
        fila = Marco(contenedor, fondo="tarjeta")
        fila.pack(fill="x", pady=2)
        for i, texto in enumerate(textos):
            Etiqueta(fila, texto, tono="texto" if i == 0 else "sec",
                     fuente=tema.F_NEG if i == 0 and negrita_primero else tema.F_TEXTO).pack(
                side="left", padx=(0, 8))
        return fila

    def _cifras(self, contenedor, conteo):
        cifras = Marco(contenedor, fondo="tarjeta")
        cifras.pack(fill="x")
        for clave, nombre in (("Prueba", "Pruebas"), ("Entrevista", "Entrevistas")):
            bloque = Marco(cifras, fondo="tarjeta")
            bloque.pack(side="left", padx=(0, 28))
            Etiqueta(bloque, str(conteo[clave]), fuente=tema.F_KPI).pack(anchor="w")
            Etiqueta(bloque, nombre, tono="sec").pack(anchor="w")

    def _pintar_dia(self, contenedor, lista, conteo):
        self._vaciar(contenedor)
        self._cifras(contenedor, conteo)
        if not lista:
            Etiqueta(contenedor, "Nada agendado.", tono="sec").pack(anchor="w", pady=(10, 0))
        for r in lista[:3]:
            hora = logica.formatear_hora(r.get("hora")) or "Sin hora"
            self._fila(contenedor, hora, f"{r['nombre_completo']} · {agenda.tipo(r['etapa'])}",
                       negrita_primero=False).pack_configure(pady=(8 if r is lista[0] else 2, 2))
        if len(lista) > 3:
            Etiqueta(contenedor, f"y {len(lista) - 3} más", tono="sec").pack(anchor="w")

    def _marcar_recibido(self, registro):
        bd.guardar("embudo", {"asistencia": "Asistió"}, registro["id"])
        self.app.avisar_cambio(f"{registro['nombre_completo']} marcado como recibido.")
        self.refrescar()

    def _pintar_atrasados(self, atrasados):
        self._vaciar(self.atrasados)
        if not atrasados:
            Etiqueta(self.atrasados, "Nadie atrasado. Todo al día.", tono="sec").pack(anchor="w")
            return
        for r in atrasados[:5]:
            fila = Marco(self.atrasados, fondo="tarjeta")
            fila.pack(fill="x", pady=3)
            Etiqueta(fila, r["nombre_completo"], fuente=tema.F_NEG).pack(side="left")
            atraso = agenda.texto_dias(agenda.dias_atraso(r, date.today()))
            Etiqueta(fila, f"  {agenda.tipo(r['etapa'])} · {logica.formatear(r['fecha'])} · "
                           f"{atraso} de atraso · {r.get('telefono') or 'sin teléfono'}",
                     tono="sec").pack(side="left")
            if r.get("origen") == "pruebas":
                Boton(fila, "Abrir ficha",
                      lambda r=r: self.app.abrir_ficha(registro=bd.obtener("pruebas", r["id"])),
                      tipo="secundario", alto=28, fuente=tema.F_PEQ_NEG).pack(side="right")
                continue
            Boton(fila, "Abrir", lambda r=r: self.app.ir_a("embudo", r["id"]), tipo="fantasma",
                  alto=28, fuente=tema.F_PEQ_NEG).pack(side="right")
            Boton(fila, "Asistió", lambda r=r: self._marcar_recibido(r), tipo="secundario",
                  alto=28, fuente=tema.F_PEQ_NEG).pack(side="right", padx=(0, 6))
        if len(atrasados) > 5:
            Etiqueta(self.atrasados, f"y {len(atrasados) - 5} más en el Embudo",
                     tono="sec").pack(anchor="w", pady=(4, 0))

    def refrescar(self):
        hoy = date.today()
        embudo = bd.listar("embudo")
        activos = agenda.elementos(embudo, bd.listar("pruebas"))
        datos = agenda.resumen(activos, hoy)
        self._pintar_dia(self.hoy, datos["hoy"], datos["conteo_hoy"])
        self._pintar_dia(self.manana, datos["manana"], datos["conteo_manana"])

        self._vaciar(self.global_)
        self._cifras(self.global_, datos["por_venir"])
        Etiqueta(self.global_, f"{datos['total_por_venir']} en total, sin importar la fecha",
                 tono="sec").pack(anchor="w", pady=(10, 0))
        Etiqueta(self.global_, f"{datos['total_activos']} activos · "
                               f"{len(datos['atrasados'])} atrasados", tono="sec").pack(anchor="w")

        self._pintar_atrasados(datos["atrasados"])

        self._vaciar(self.pendientes)
        faltantes = bd.pendientes()
        if not faltantes:
            Etiqueta(self.pendientes, "Todo al día.", tono="sec").pack(anchor="w")
        for p in faltantes[:4]:
            fila = self._fila(self.pendientes, p["referencia"], p["modulo"])
            for w in [fila] + fila.winfo_children():
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e, p=p: self.app.ir_a(p["tabla"], p["id"]))
        if len(faltantes) > 4:
            Etiqueta(self.pendientes, f"y {len(faltantes) - 4} más", tono="sec").pack(anchor="w")

        self._vaciar(self.cumples)
        proximos = []
        for emp in bd.listar("empleados"):
            r = logica.proximo_cumpleanos(emp["fecha_cumpleanos"], hoy) \
                if emp.get("fecha_cumpleanos") else None
            if r and r[1] <= configuracion.PARAMETROS["dias_cumpleanos"]:
                proximos.append((r[1], r[0], emp["nombre_completo"]))
        if not proximos:
            Etiqueta(self.cumples, f"Sin cumpleaños en los próximos {configuracion.PARAMETROS['dias_cumpleanos']} días.",
                     tono="sec").pack(anchor="w")
        for dias, fecha, nombre in sorted(proximos)[:4]:
            cuando = "hoy" if dias == 0 else "mañana" if dias == 1 else f"en {dias} días"
            self._fila(self.cumples, nombre,
                       f"{fecha.day} de {logica.MESES[fecha.month - 1]} ({cuando})")

        self._vaciar(self.personal)
        este_anio = sum(1 for v in bd.listar("vacaciones")
                        if str(v.get("fecha_inicio", "")).startswith(str(hoy.year)))
        for texto, valor in (("Empleados", len(bd.listar("empleados"))),
                             ("Amonestaciones", len(bd.listar("amonestaciones"))),
                             ("Vacaciones este año", este_anio)):
            self._fila(self.personal, str(valor), texto)
        podar()


class Pendientes(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Pendientes de completar",
                         "Registros a los que les falta subir su PDF o archivo")
        self.filas = []
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)
        tarjeta = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        tarjeta.grid(row=0, column=0, sticky="nsew")
        tarjeta.rowconfigure(1, weight=1)
        tarjeta.columnconfigure(0, weight=1)
        self.resumen = Etiqueta(tarjeta, "", tono="sec")
        self.resumen.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 10))
        cont, self.arbol = crear_tabla(tarjeta, [("modulo", "Módulo", 140),
                                                 ("referencia", "Referencia", 300),
                                                 ("falta", "Falta", 220), ("fecha", "Fecha", 100)])
        cont.grid(row=1, column=0, sticky="nsew", padx=(12, 4), pady=(0, 12))
        self.arbol.bind("<Double-1>", self._abrir)
        Boton(self.zona_acciones, "Abrir registro", self._abrir, fondo="app").pack()

    def refrescar(self):
        self.arbol.delete(*self.arbol.get_children())
        self.filas = bd.pendientes()
        for i, p in enumerate(self.filas):
            self.arbol.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                              values=(p["modulo"], p["referencia"], p["falta"],
                                      logica.formatear(p["fecha"])))
        self.resumen.configure(text=f"{len(self.filas)} pendientes · doble clic para abrir "
                                    f"el registro")

    def _abrir(self, _evento=None):
        seleccion = self.arbol.selection()
        if seleccion:
            p = self.filas[int(seleccion[0])]
            self.app.ir_a(p["tabla"], p["id"])


class PaginaDocumentos(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Documentos",
                         "Previsualiza, edita y guarda los documentos de Word generados")
        self.ruta_actual = None
        self._rutas = []
        self._marcas = []
        self._n = 0
        self._silencio = False
        self.cuerpo.columnconfigure(1, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)

        lista = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        lista.grid(row=0, column=0, sticky="ns")
        lista.rowconfigure(1, weight=1)
        Etiqueta(lista, "Generados", fuente=tema.F_SUB).grid(row=0, column=0, sticky="w",
                                                              padx=18, pady=(16, 8))
        cont, self.arbol = crear_tabla(lista, [("nombre", "Documento", 260),
                                               ("fecha", "Modificado", 120)])
        cont.grid(row=1, column=0, sticky="nsew", padx=(12, 4))
        self.arbol.bind("<<TreeviewSelect>>", self._al_elegir)
        Boton(lista, "Abrir carpeta", lambda: abrir_ruta(documentos.CARPETA_DOCUMENTOS),
              tipo="secundario").grid(row=2, column=0, sticky="ew", padx=16, pady=14)

        der = Marco(self.cuerpo, fondo="app")
        der.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        der.rowconfigure(1, weight=1)
        der.columnconfigure(0, weight=1)
        barra = Marco(der, fondo="app")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.estado = Etiqueta(barra, "", fondo="app", tono="sec")
        self.estado.pack(side="left")
        self.b_word = Boton(barra, "Abrir en Word", self.abrir_en_word, tipo="secundario",
                            fondo="app")
        self.b_word.pack(side="right")
        self.b_descartar = Boton(barra, "Descartar cambios", self.descartar, tipo="secundario",
                                 fondo="app")
        self.b_descartar.pack(side="right", padx=8)
        self.b_guardar = Boton(barra, "Guardar cambios", self.guardar, fondo="app")
        self.b_guardar.pack(side="right")
        self._construir_hoja(der)
        self.cargar(None)

    def _construir_hoja(self, padre):
        hoja = tk.Frame(padre, bg="#FFFFFF", highlightthickness=1, highlightbackground="#D5DBE3")
        hoja.grid(row=1, column=0, sticky="ns")
        hoja.rowconfigure(2, weight=1)
        banda = tk.Frame(hoja, bg=tema.AZUL)
        banda.grid(row=0, column=0, columnspan=2, sticky="ew")
        try:
            self._logo = tk.PhotoImage(
                file=os.path.join(documentos._carpeta_plantillas(), "logo_vista.png"))
            tk.Label(banda, image=self._logo, bg=tema.AZUL, bd=0).pack(side="left", padx=(22, 14),
                                                                        pady=8)
        except tk.TclError:
            self._logo = None
        bloque = tk.Frame(banda, bg=tema.AZUL)
        bloque.pack(side="left", pady=8)
        tk.Label(bloque, text=documentos.EMPRESA, bg=tema.AZUL, fg="#FFFFFF",
                 font=(tema.FAMILIA, 14, "bold")).pack(anchor="w")
        tk.Label(bloque, text=documentos.AREA.upper(), bg=tema.AZUL, fg="#B7CBDD",
                 font=tema.F_PEQ).pack(anchor="w")
        tk.Frame(hoja, bg=tema.CORINTO, height=3).grid(row=1, column=0, columnspan=2,
                                                       sticky="ew")
        self.texto = tk.Text(hoja, wrap="word", width=74, height=26, relief="flat", bd=0,
                             font=(tema.FAMILIA, 11), bg="#FFFFFF", fg="#111827",
                             insertbackground="#111827", selectbackground="#CFE3F7",
                             selectforeground="#111827", padx=52, pady=26, undo=True,
                             spacing3=2, highlightthickness=0)
        self.texto.grid(row=2, column=0, sticky="nsew")
        barra = ttk.Scrollbar(hoja, orient="vertical", command=self.texto.yview,
                              style="Moderno.Vertical.TScrollbar")
        barra.grid(row=2, column=1, sticky="ns")
        self.texto.configure(yscrollcommand=barra.set)
        self.texto.bind("<<Modified>>", self._modificado)

    def _etiquetas(self, pa):
        t = self.texto
        etiquetas = []
        if pa["alineacion"] in ("centro", "derecha"):
            t.tag_configure(pa["alineacion"], justify="center" if pa["alineacion"] == "centro"
                            else "right")
            etiquetas.append(pa["alineacion"])
        tamano = round((pa["tamano"] or 12) * 0.92)
        if pa["negrita"] or tamano != 11:
            nombre = f"fuente_{int(pa['negrita'])}_{tamano}"
            t.tag_configure(nombre, font=(tema.FAMILIA, tamano,
                                          "bold" if pa["negrita"] else "normal"))
            etiquetas.append(nombre)
        if pa["subrayado"]:
            t.tag_configure("subrayado", underline=True)
            etiquetas.append("subrayado")
        if pa["color"]:
            nombre = f"color_{pa['color']}"
            t.tag_configure(nombre, foreground=f"#{pa['color']}")
            etiquetas.append(nombre)
        return tuple(etiquetas)

    def cargar(self, ruta):
        t = self.texto
        self._silencio = True
        t.configure(state="normal")
        t.delete("1.0", "end")
        for m in self._marcas:
            t.mark_unset(m)
        self._marcas, self._n = [], 0
        self.ruta_actual = ruta
        if ruta is None:
            t.insert("end", "Todavía no hay documentos.\n\nCrea una solicitud o constancia de "
                            "vacaciones, o una carta de amonestación, y aparecerá aquí para "
                            "que la revises y la edites antes de imprimirla.")
            t.configure(state="disabled")
            for b in (self.b_guardar, self.b_descartar, self.b_word):
                b.activar(False)
            self.estado.configure(text="")
        else:
            parrafos = documentos.leer_para_editar(ruta)
            for i, pa in enumerate(parrafos):
                t.mark_set(f"p{i}", "end-1c")
                t.mark_gravity(f"p{i}", "left")
                self._marcas.append(f"p{i}")
                t.insert("end", pa["texto"] + "\n", self._etiquetas(pa))
            t.mark_set("pfin", "end-1c")
            t.mark_gravity("pfin", "left")
            self._marcas.append("pfin")
            self._n = len(parrafos)
            t.edit_reset()
            t.edit_modified(False)
            self.b_word.activar(True)
        self._silencio = False
        self._poner_estado(False)

    def textos_actuales(self):
        nombres = [f"p{i}" for i in range(self._n)] + ["pfin"]
        salida = []
        for a, b in zip(nombres, nombres[1:]):
            trozo = self.texto.get(a, b)
            salida.append(trozo[:-1] if trozo.endswith("\n") else trozo)
        return salida

    def hay_cambios(self):
        return self.ruta_actual is not None and bool(self.texto.edit_modified())

    def _modificado(self, _e=None):
        if not self._silencio:
            self._poner_estado(bool(self.texto.edit_modified()))

    def _poner_estado(self, modificado):
        if self.ruta_actual is None:
            return
        nombre = os.path.basename(self.ruta_actual)
        self.estado.configure(text=("●  Cambios sin guardar  ·  " if modificado
                                    else "Sin cambios  ·  ") + nombre)
        self.b_guardar.activar(modificado)
        self.b_descartar.activar(modificado)

    def guardar(self):
        if self.ruta_actual is None:
            return
        try:
            documentos.guardar_edicion(self.ruta_actual, self.textos_actuales())
        except (OSError, ValueError) as e:
            messagebox.showerror(
                "No se pudo guardar",
                f"{e}\n\nSi el documento está abierto en Word, ciérralo e inténtalo de nuevo.")
            return
        ruta = self.ruta_actual
        self.cargar(ruta)
        self.refrescar()
        self.app.avisar_cambio("Cambios guardados en el documento.")

    def descartar(self):
        if self.ruta_actual is not None:
            self.cargar(self.ruta_actual)

    def abrir_en_word(self):
        if self.ruta_actual is not None:
            if self.hay_cambios():
                if not messagebox.askyesno("Cambios sin guardar",
                                           "Hay cambios sin guardar. ¿Guardarlos antes de abrir "
                                           "en Word?"):
                    return
                self.guardar()
            abrir_ruta(self.ruta_actual)

    def confirmar_salida(self):
        if not self.hay_cambios():
            return True
        r = messagebox.askyesnocancel("Cambios sin guardar",
                                      "Este documento tiene cambios sin guardar.\n"
                                      "¿Quieres guardarlos?")
        if r is None:
            return False
        if r:
            self.guardar()
        return True

    def refrescar(self):
        self._rutas = documentos.listar_documentos()
        self._silencio_lista = True
        self.arbol.delete(*self.arbol.get_children())
        for i, (ruta, mtime) in enumerate(self._rutas):
            nombre = os.path.splitext(os.path.basename(ruta))[0].replace("_", " ")
            self.arbol.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                              values=(nombre, datetime.fromtimestamp(mtime).strftime(
                                  "%d/%m/%Y %H:%M")))
        for i, (ruta, _) in enumerate(self._rutas):
            if ruta == self.ruta_actual:
                self.arbol.selection_set(str(i))
        self._silencio_lista = False
        if self.ruta_actual is None and self._rutas:
            self.arbol.selection_set("0")

    def _al_elegir(self, _e=None):
        if getattr(self, "_silencio_lista", False):
            return
        seleccion = self.arbol.selection()
        if not seleccion:
            return
        ruta = self._rutas[int(seleccion[0])][0]
        if ruta == self.ruta_actual:
            return
        if not self.confirmar_salida():
            self.refrescar()
            return
        self.cargar(ruta)

    def mostrar(self, ruta):
        if ruta != self.ruta_actual and not self.confirmar_salida():
            return
        self.cargar(ruta)
        self.refrescar()
