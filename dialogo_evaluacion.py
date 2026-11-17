import os
import re
from datetime import date
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import base_datos as bd
import evaluacion as ev
import logica
import modulos
import ranking
import tema
from componentes import (autoformato_fecha, Boton, CajaTexto, Combo, Etiqueta, Marco, Separador,
                         ZonaDesplazable, crear_tabla, pasar_al_siguiente, registrar)


class DialogoEvaluacion(tk.Toplevel):
    def __init__(self, app, registro=None, valores=None, heredar=None, al_guardar=None):
        super().__init__(app)
        self.app, self.registro, self.heredar, self.al_guardar = app, registro, heredar, al_guardar
        self.title("Ficha de evaluación – Prueba de habilidades")
        self.transient(app)
        registrar(self, lambda w, p: w.configure(bg=p["fondo"]))
        pantalla_x, pantalla_y = self.winfo_screenwidth(), self.winfo_screenheight()
        ancho, alto = min(980, pantalla_x - 60), min(800, pantalla_y - 110)
        x = max(0, min(app.winfo_rootx() + (app.winfo_width() - ancho) // 2, pantalla_x - ancho))
        y = max(0, min(app.winfo_rooty() + (app.winfo_height() - alto) // 4, pantalla_y - alto - 60))
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(820, ancho), min(560, alto))

        datos = dict(registro or {})
        datos.update({k: v for k, v in (valores or {}).items() if v})
        self.v_candidato = tk.StringVar(value=datos.get("candidato", ""))
        self.v_puesto = tk.StringVar(value=datos.get("puesto") or "")
        fecha = datos.get("fecha") or ""
        self.v_fecha = tk.StringVar(value=logica.formatear(fecha) if fecha else "")
        hecha = datos.get("fecha_prueba") or ""
        self.v_hecha = tk.StringVar(value=logica.formatear(hecha) if hecha else "")
        detalle = ev.desde_texto(datos.get("detalle"))
        self.notas, self.globales, self.etiquetas, self.entradas = [], [], [], []
        self._token_aviso = None
        self.adjuntos = [
            {"id": x["id"], "archivo": x["archivo"], "origen": None, "nombre": x["archivo"],
             "categoria": x["categoria"]}
            for x in (bd.adjuntos_de("pruebas", registro["id"]) if registro else [])]
        self.adjuntos += [dict(a) for a in (heredar or [])]

        raiz = Marco(self, fondo="app")
        raiz.pack(fill="both", expand=True, padx=26, pady=20)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(2, weight=1)

        titulo = "Editar evaluación" if registro else "Nueva prueba de habilidades"
        Etiqueta(raiz, titulo, fondo="app", fuente=(tema.FAMILIA, 18, "bold")).grid(
            row=0, column=0, sticky="w")
        self._crear_encabezado(raiz)

        zona = self.zona = ZonaDesplazable(raiz, fondo="app")
        zona.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        zona.interior.columnconfigure(0, weight=1)
        for i, sec in enumerate(detalle["secciones"]):
            self._crear_seccion(zona.interior, i, sec).grid(row=i, column=0, sticky="ew",
                                                            pady=(0, 12), padx=(0, 8))
        extra = len(detalle["secciones"])
        Etiqueta(zona.interior, "Observaciones", fondo="app", fuente=tema.F_SUB).grid(
            row=extra, column=0, sticky="w", pady=(6, 4))
        self.t_obs = CajaTexto(zona.interior, alto=4)
        self.t_obs.grid(row=extra + 1, column=0, sticky="ew", padx=(0, 8))
        self.t_obs.insert("1.0", datos.get("observaciones") or "")
        Etiqueta(zona.interior, "Pendientes por confirmar", fondo="app",
                 fuente=tema.F_SUB).grid(row=extra + 2, column=0, sticky="w", pady=(14, 4))
        self.t_pend = CajaTexto(zona.interior, alto=3)
        self.t_pend.grid(row=extra + 3, column=0, sticky="ew", pady=(0, 12), padx=(0, 8))
        self.t_pend.insert("1.0", detalle["pendientes"])
        Etiqueta(zona.interior, "Archivos (CV y prueba de Excel)", fondo="app",
                 fuente=tema.F_SUB).grid(row=extra + 4, column=0, sticky="w", pady=(6, 4))
        self._crear_archivos(zona.interior).grid(row=extra + 5, column=0, sticky="ew",
                                                 pady=(0, 12), padx=(0, 8))
        self._pintar_adjuntos()

        pie = Marco(raiz, fondo="app")
        pie.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.total = Etiqueta(pie, "", fondo="app", fuente=tema.F_SUB)
        self.total.pack(side="left")
        self.aviso = Etiqueta(pie, "", fondo="app", tono="peligro", fuente=tema.F_NEG)
        self.aviso.pack(side="left", padx=20)
        Boton(pie, "Guardar", self.guardar, fondo="app").pack(side="right")
        Boton(pie, "Cancelar", self.destroy, tipo="secundario", fondo="app").pack(
            side="right", padx=(0, 10))

        for sec, fila in zip(detalle["secciones"], self.notas):
            for c, var in zip(sec["criterios"], fila):
                var.set("" if c["calificacion"] is None else f"{c['calificacion']:g}")
        for sec, var in zip(detalle["secciones"], self.globales):
            if var is not None and sec["global"] is not None:
                var.set(f"{sec['global']:g}")
        self._cableado = True
        self._actualizar()
        self.bind("<Return>", pasar_al_siguiente)
        self.bind("<KP_Enter>", pasar_al_siguiente)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-s>", lambda e: self.guardar())
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def _crear_encabezado(self, raiz):
        tarjeta = Marco(raiz, fondo="tarjeta", borde=True)
        tarjeta.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        tarjeta.columnconfigure((0, 3), weight=3, uniform="e")
        tarjeta.columnconfigure((1, 2), weight=2, uniform="e")
        nombres = sorted({r["nombre_completo"] for r in bd.listar("embudo")})
        campos = (("Candidato (elige del embudo o escribe)", self.v_candidato, nombres),
                  ("Fecha de evaluación (agendada)", self.v_fecha, None),
                  ("Fecha de la prueba (cuando la hizo)", self.v_hecha, None),
                  ("Plaza", self.v_puesto, ranking.PLAZAS))
        for i, (texto, var, opciones) in enumerate(campos):
            columna = i
            Etiqueta(tarjeta, texto, tono="sec", fuente=tema.F_PEQ).grid(
                row=0, column=columna, sticky="w", padx=16, pady=(14, 4))
            if opciones is not None:
                w = Combo(tarjeta, opciones)
                w.configure(textvariable=var)
            else:
                w = ttk.Entry(tarjeta, textvariable=var, style="Moderno.TEntry", width=18)
                if var in (self.v_fecha, self.v_hecha):
                    autoformato_fecha(w)
            w.grid(row=1, column=columna, sticky="ew", padx=16, pady=(0, 10))
        Etiqueta(tarjeta, "La fecha de evaluación avisa si la prueba está cerca o atrasada; la "
                          "fecha de la prueba se llena al calificar (si dejas notas y la omites, "
                          "se usa hoy).  Escala: " + ev.ESCALA, tono="sec", fuente=tema.F_PEQ,
                 wraplength=880, justify="left").grid(row=2, column=0, columnspan=4,
                                                      sticky="w", padx=16, pady=(0, 12))

    def _crear_seccion(self, padre, indice, sec):
        tarjeta = Marco(padre, fondo="tarjeta", borde=True)
        tarjeta.columnconfigure(0, weight=1)
        cab = Marco(tarjeta, fondo="tarjeta")
        cab.grid(row=0, column=0, columnspan=3, sticky="ew", padx=18, pady=(14, 6))
        Etiqueta(cab, sec["nombre"], fuente=tema.F_SUB).pack(side="left")
        etiqueta = Etiqueta(cab, "", tono="sec", fuente=tema.F_NEG)
        etiqueta.pack(side="right")
        self.etiquetas.append(etiqueta)
        Etiqueta(tarjeta, "CRITERIO", tono="sec", fuente=tema.F_PEQ_NEG).grid(
            row=1, column=0, sticky="w", padx=(18, 8))
        Etiqueta(tarjeta, "CALIFICACIÓN", tono="sec", fuente=tema.F_PEQ_NEG).grid(
            row=1, column=1, columnspan=2, sticky="w", padx=8)
        Separador(tarjeta).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        variables = []
        for fila, c in enumerate(sec["criterios"], start=3):
            Etiqueta(tarjeta, c["criterio"], wraplength=560, justify="left").grid(
                row=fila, column=0, sticky="w", padx=(18, 8), pady=5)
            variables.append(self._casilla(tarjeta, fila, c["maximo"], 5))
        self.notas.append(variables)
        texto_global = ev.SECCIONES[indice]["global"]
        if texto_global:
            fila = 3 + len(sec["criterios"])
            Etiqueta(tarjeta, texto_global, wraplength=560, justify="left", tono="sec").grid(
                row=fila, column=0, sticky="w", padx=(18, 8), pady=(8, 5))
            self.globales.append(self._casilla(tarjeta, fila, 10, 8))
        else:
            self.globales.append(None)
        Etiqueta(tarjeta, "", fuente=tema.F_PEQ).grid(row=99, column=0, pady=4)
        return tarjeta

    def _crear_archivos(self, padre):
        tarjeta = Marco(padre, fondo="tarjeta", borde=True)
        tarjeta.columnconfigure(0, weight=1)
        cont, self._arbol_adj = crear_tabla(tarjeta, [("nombre", "Documento", 420),
                                                      ("categoria", "Tipo", 140)])
        self._arbol_adj.configure(height=4)
        cont.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        fila = Marco(tarjeta, fondo="tarjeta")
        fila.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))
        self.var_categoria = tk.StringVar(value=bd.CATEGORIAS_ADJUNTO[0])
        combo = Combo(fila, bd.CATEGORIAS_ADJUNTO, solo_lectura=True, ancho=14)
        combo.configure(textvariable=self.var_categoria)
        combo.pack(side="left")
        for texto, funcion, tipo in (("Agregar archivos", self.agregar_adjuntos, "secundario"),
                                     ("Ver", self.ver_adjunto, "secundario"),
                                     ("Quitar", self.quitar_adjunto, "fantasma")):
            Boton(fila, texto, funcion, tipo=tipo, alto=32, fuente=tema.F_PEQ_NEG).pack(
                side="left", padx=(8, 0))
        return tarjeta

    def _pintar_adjuntos(self):
        self._arbol_adj.delete(*self._arbol_adj.get_children())
        for i, a in enumerate(self.adjuntos):
            self._arbol_adj.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                                   values=(modulos._nombre_visible(a["nombre"]), a["categoria"]))

    def agregar_adjuntos(self):
        rutas = filedialog.askopenfilenames(
            title="Elegir CV o archivos (puedes elegir varios)", parent=self,
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
                                   + "\n".join(rechazados), parent=self)

    def _adjunto_elegido(self):
        seleccion = self._arbol_adj.selection()
        return int(seleccion[0]) if seleccion else None

    def ver_adjunto(self):
        i = self._adjunto_elegido()
        if i is None:
            messagebox.showinfo("Archivos", "Selecciona un archivo de la lista.", parent=self)
            return
        a = self.adjuntos[i]
        modulos.abrir_ruta(a["origen"] or bd.ruta_archivo(a["archivo"]))

    def quitar_adjunto(self):
        i = self._adjunto_elegido()
        if i is None:
            messagebox.showinfo("Archivos", "Selecciona el archivo que quieres quitar.",
                                parent=self)
            return
        self.adjuntos.pop(i)
        self._pintar_adjuntos()

    def _guardar_adjuntos(self, id_registro):
        actuales = {a["id"] for a in self.adjuntos if a["id"]}
        for previo in bd.adjuntos_de("pruebas", id_registro):
            if previo["id"] not in actuales:
                bd.quitar_adjunto(previo["id"])
        for a in self.adjuntos:
            if a["id"]:
                continue
            archivo = a["archivo"] or bd.copiar_archivo(a["origen"])
            bd.agregar_adjunto("pruebas", id_registro, archivo, a["categoria"])

    def _casilla(self, tarjeta, fila, maximo, espacio):
        var = tk.StringVar()
        var.trace_add("write", lambda *_: self._actualizar())
        orden = len(self.entradas)
        entrada = ttk.Entry(
            tarjeta, textvariable=var, width=5, justify="center", style="Moderno.TEntry",
            validate="key",
            validatecommand=(self.register(self._permitir), "%P", f"{maximo:g}", "%W"))
        entrada.grid(row=fila, column=1, padx=(8, 0), pady=espacio // 2 + 1)
        Etiqueta(tarjeta, f"/ {maximo:g}", tono="sec", fuente=tema.F_NEG).grid(
            row=fila, column=2, sticky="w", padx=(6, 18))
        for tecla in ("<Return>", "<KP_Enter>", "<Down>"):
            entrada.bind(tecla, lambda e, i=orden: self._mover(i + 1) or "break")
        entrada.bind("<Up>", lambda e, i=orden: self._mover(i - 1) or "break")
        entrada.bind("<FocusIn>", lambda e, w=entrada: self._al_enfocar(w))
        self.entradas.append(entrada)
        return var

    def _permitir(self, texto, maximo, ruta):
        if texto == "":
            return True
        if not re.fullmatch(r"\d{1,2}([.,]\d?)?", texto):
            self._error_en_casilla("Escribe solo números, sin letras ni signos.", ruta)
            return False
        if float(texto.replace(",", ".")) > float(maximo):
            self._error_en_casilla(f"La nota máxima de este criterio es {maximo}.", ruta)
            return False
        return True

    def _error_en_casilla(self, mensaje, ruta):
        self.aviso.configure(text=mensaje)
        if self._token_aviso is not None:
            self.after_cancel(self._token_aviso)
        self._token_aviso = self.after(2800, lambda: self.aviso.configure(text=""))
        casilla = self.nametowidget(ruta)
        casilla.configure(style="Error.Moderno.TEntry")
        self.after(450, lambda: self._quitar_error(casilla))

    @staticmethod
    def _quitar_error(casilla):
        try:
            casilla.configure(style="Moderno.TEntry")
        except tk.TclError:
            pass

    def _mover(self, indice):
        if indice < 0:
            return
        if indice >= len(self.entradas):
            self.t_obs.focus_set()
            self._asegurar_visible(self.t_obs)
            return
        self.entradas[indice].focus_set()

    def _al_enfocar(self, casilla):
        casilla.select_range(0, "end")
        self._asegurar_visible(casilla)

    def _asegurar_visible(self, widget):
        self.zona.ver(widget)

    def _leer(self, estricto):
        detalle = ev.vacio()
        for sec, filas, var_g in zip(detalle["secciones"], self.notas, self.globales):
            for c, var in zip(sec["criterios"], filas):
                try:
                    c["calificacion"] = ev.leer_nota(var.get(), c["maximo"])
                except ValueError as e:
                    if estricto:
                        raise ValueError(f"{sec['nombre']} – {c['criterio']}\n{e}") from None
            if var_g is not None:
                try:
                    sec["global"] = ev.leer_nota(var_g.get(), 10)
                except ValueError as e:
                    if estricto:
                        raise ValueError(f"{sec['nombre']} – puntaje global\n{e}") from None
        return detalle

    def _actualizar(self):
        if not getattr(self, "_cableado", False):
            return
        detalle = self._leer(estricto=False)
        for sec, etiqueta in zip(detalle["secciones"], self.etiquetas):
            r = ev.resultado(sec)
            etiqueta.configure(text=f"{r[0]:g}/{r[1]:g}  ·  {r[2] * 100:.0f} %" if r
                               else "Sin calificar")
        total = ev.texto_puntaje(detalle)
        self.total.configure(text=f"Promedio de la prueba: {total}" if total
                             else "Promedio de la prueba: sin calificar")

    def guardar(self):
        candidato = self.v_candidato.get().strip()
        if not candidato:
            messagebox.showwarning("Revisar datos", "Falta completar: Candidato.")
            return False
        texto_eval, texto_hecha = self.v_fecha.get().strip(), self.v_hecha.get().strip()
        fecha, hecha = logica.a_iso(texto_eval), logica.a_iso(texto_hecha)
        if (texto_eval and not fecha) or (texto_hecha and not hecha):
            messagebox.showwarning("Revisar datos", "Fecha no válida. Usa dd/mm/aaaa.")
            return False
        try:
            detalle = self._leer(estricto=True)
        except ValueError as e:
            messagebox.showwarning("Revisar la calificación", str(e))
            return False
        con_notas = ev.promedio(detalle) is not None
        if con_notas and not hecha:
            hecha = date.today().isoformat()
        fecha = fecha or hecha
        if not fecha:
            messagebox.showwarning("Revisar datos", "Falta la fecha de evaluación.")
            return False
        if hecha and hecha > date.today().isoformat():
            messagebox.showwarning("Revisar datos",
                                   "La fecha de la prueba no puede ser futura: es el día que la hizo.")
            return False
        if hecha and not con_notas and not messagebox.askyesno(
                "Sin calificaciones",
                "Indicaste que ya la hizo pero no escribiste calificaciones.\n¿Guardar así?"):
            return False
        if not self.registro and any(
                p["fecha"] == fecha and p["candidato"].strip().lower() == candidato.lower()
                and p.get("tipo_prueba") == "Prueba de habilidades" for p in bd.listar("pruebas")):
            if not messagebox.askyesno(
                    "Prueba repetida",
                    f"{candidato} ya tiene una prueba de habilidades en esa fecha.\n"
                    "¿Guardar otra de todos modos?"):
                return False
        detalle["pendientes"] = self.t_pend.get("1.0", "end").strip()
        datos = {"candidato": candidato, "puesto": self.v_puesto.get().strip() or None,
                 "fecha": fecha, "fecha_prueba": hecha or None,
                 "tipo_prueba": "Prueba de habilidades",
                 "puntaje": ev.texto_puntaje(detalle),
                 "observaciones": self.t_obs.get("1.0", "end").strip() or None,
                 "detalle": ev.a_texto(detalle)}
        id_registro = bd.guardar("pruebas", datos, self.registro["id"] if self.registro else None)
        self._guardar_adjuntos(id_registro)
        if hecha:
            bd.confirmar_asistencia(candidato, False)
        else:
            bd.reagendar_prueba(candidato, fecha)
        self.destroy()
        if self.al_guardar:
            self.al_guardar(id_registro)
        return True
