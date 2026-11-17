import os
import re
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import base_datos as bd
import informes
import logica
import tema
from componentes import (Boton, Combo, Etiqueta, Marco, autoformato_fecha, crear_tabla,
                         registrar)


def _nombre_archivo(texto):
    return re.sub(r"[^\w\-]+", "_", texto.strip().lower()).strip("_") or "informe"


class DialogoInforme(tk.Toplevel):
    def __init__(self, app, tabla, persona_id=None):
        super().__init__(app)
        self.app, self.tabla = app, tabla
        self.title("Ver informes")
        self.transient(app)
        registrar(self, lambda w, p: w.configure(bg=p["fondo"]))
        ancho = min(1020, app.winfo_screenwidth() - 60)
        alto = min(680, app.winfo_screenheight() - 100)
        x = app.winfo_rootx() + max(0, (app.winfo_width() - ancho) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - alto) // 3)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(min(820, ancho), min(500, alto))
        self.personas = bd.empleados_basico()
        self.resultado = ("", [], [])

        raiz = Marco(self, fondo="app")
        raiz.pack(fill="both", expand=True, padx=26, pady=20)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(2, weight=1)
        self.titulo = Etiqueta(raiz, informes.ESPECIFICACIONES[tabla]["titulo"], fondo="app",
                               fuente=(tema.FAMILIA, 18, "bold"))
        self.titulo.grid(row=0, column=0, sticky="w")

        filtros = Marco(raiz, fondo="tarjeta", borde=True)
        filtros.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        interior = Marco(filtros, fondo="tarjeta")
        interior.pack(fill="x", padx=16, pady=12)
        Etiqueta(interior, "Persona", tono="sec", fuente=tema.F_PEQ).grid(row=0, column=0, sticky="w")
        Etiqueta(interior, "Desde (dd/mm/aaaa)", tono="sec", fuente=tema.F_PEQ).grid(
            row=0, column=1, sticky="w", padx=(14, 0))
        Etiqueta(interior, "Hasta (dd/mm/aaaa)", tono="sec", fuente=tema.F_PEQ).grid(
            row=0, column=2, sticky="w", padx=(14, 0))
        self.v_persona = tk.StringVar(value=informes.TODAS)
        self.combo = Combo(interior, [informes.TODAS] + [n for _, n in self.personas],
                           solo_lectura=True, ancho=32)
        self.combo.configure(textvariable=self.v_persona)
        self.combo.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.actualizar())
        self.v_desde, self.v_hasta = tk.StringVar(), tk.StringVar()
        for col, var in ((1, self.v_desde), (2, self.v_hasta)):
            entrada = ttk.Entry(interior, textvariable=var, width=14, style="Moderno.TEntry")
            entrada.grid(row=1, column=col, sticky="w", padx=(14, 0), pady=(4, 0))
            autoformato_fecha(entrada)
            entrada.bind("<KeyRelease>", lambda e: self.after_idle(self.actualizar), add="+")
        Boton(interior, "Quitar filtros", self.limpiar, tipo="secundario", alto=32,
              fuente=tema.F_PEQ_NEG).grid(row=1, column=3, padx=(14, 0), pady=(4, 0))
        self.aviso = Etiqueta(interior, "", tono="sec", fuente=tema.F_PEQ)
        self.aviso.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

        vista = Marco(raiz, fondo="tarjeta", borde=True)
        vista.grid(row=2, column=0, sticky="nsew")
        vista.rowconfigure(0, weight=1)
        vista.columnconfigure(0, weight=1)
        columnas = [(f"c{i}", c[0], 120) for i, c in
                    enumerate(informes.ESPECIFICACIONES[tabla]["columnas"])]
        cont, self.arbol = crear_tabla(vista, columnas)
        cont.grid(row=0, column=0, sticky="nsew", padx=(12, 4), pady=12)

        pie = Marco(raiz, fondo="app")
        pie.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        Boton(pie, "Exportar a Excel", self.exportar, fondo="app").pack(side="left")
        Boton(pie, "Copiar imagen", self.copiar, tipo="secundario", fondo="app").pack(
            side="left", padx=8)
        Boton(pie, "Guardar imagen", self.guardar_imagen, tipo="secundario", fondo="app").pack(
            side="left")
        Boton(pie, "Cerrar", self.destroy, tipo="fantasma", fondo="app").pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())

        if persona_id is not None:
            for i, n in self.personas:
                if i == persona_id:
                    self.v_persona.set(n)
        self.actualizar()
        try:
            self.wait_visibility()
            self.focus_set()
        except tk.TclError:
            pass

    def _id_persona(self):
        nombre = self.v_persona.get()
        return next((i for i, n in self.personas if n == nombre), None)

    def _fechas(self):
        valores = []
        for var in (self.v_desde, self.v_hasta):
            texto = var.get().strip()
            if not texto:
                valores.append(None)
                continue
            iso = logica.a_iso(texto)
            if not iso:
                return None
            valores.append(iso)
        return valores

    def limpiar(self):
        self.v_persona.set(informes.TODAS)
        self.v_desde.set("")
        self.v_hasta.set("")
        self.actualizar()

    def actualizar(self):
        fechas = self._fechas()
        if fechas is None:
            self.aviso.configure(text="Escribe las fechas completas, por ejemplo 16/11/2026.")
            return
        desde, hasta = fechas
        if desde and hasta and hasta < desde:
            self.aviso.configure(text="La fecha «Hasta» es anterior a «Desde».")
            return
        titulo, columnas, filas = informes.construir(self.tabla, self._id_persona(), desde, hasta)
        sub = informes.subtitulo(None if self._id_persona() is None else self.v_persona.get(),
                                 desde, hasta, len(filas))
        self.resultado = (titulo, columnas, filas, sub)
        self.aviso.configure(text=sub)
        self.arbol.delete(*self.arbol.get_children())
        for n, fila in enumerate(filas):
            self.arbol.insert("", "end", values=fila, tags=("par" if n % 2 == 0 else "impar",))

    def _datos(self):
        if len(self.resultado) < 4:
            return None
        return self.resultado

    def _nombre(self, extension):
        titulo = self.resultado[0]
        persona = "" if self._id_persona() is None else "_" + _nombre_archivo(self.v_persona.get())
        return f"{_nombre_archivo(titulo)}{persona}{extension}"

    def exportar(self):
        datos = self._datos()
        if not datos:
            return
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar informe", defaultextension=".xlsx",
            initialfile=self._nombre(".xlsx"), filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        try:
            informes.exportar_xlsx(ruta, datos[0], datos[1], datos[2])
        except (OSError, ImportError) as e:
            messagebox.showerror("No se pudo exportar", str(e), parent=self)
            return
        self.app.avisar_cambio("Informe exportado.")
        from modulos import abrir_ruta
        abrir_ruta(ruta)

    def _imagen(self):
        datos = self._datos()
        if not datos:
            return None
        titulo, columnas, filas, sub = datos
        return informes.imagen_tabla(titulo, sub, columnas, filas)

    def copiar(self):
        try:
            img = self._imagen()
        except ImportError as e:
            messagebox.showerror("Copiar imagen", f"Falta un componente: {e}", parent=self)
            return
        if img is None:
            return
        try:
            informes.copiar_imagen(img)
        except OSError as e:
            ruta = os.path.join(tempfile.gettempdir(), self._nombre(".png"))
            img.save(ruta)
            messagebox.showinfo("Copiar imagen", f"{e}\n\nSe guardó la imagen en:\n{ruta}",
                                parent=self)
            return
        self.app.avisar_cambio(f"Imagen copiada ({len(self.resultado[2])} registros). "
                               "Pégala con Ctrl+V.")

    def guardar_imagen(self):
        try:
            img = self._imagen()
        except ImportError as e:
            messagebox.showerror("Guardar imagen", f"Falta un componente: {e}", parent=self)
            return
        if img is None:
            return
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar imagen", defaultextension=".png",
            initialfile=self._nombre(".png"), filetypes=[("Imagen PNG", "*.png")])
        if not ruta:
            return
        try:
            img.save(ruta)
        except OSError as e:
            messagebox.showerror("No se pudo guardar", str(e), parent=self)
            return
        self.app.avisar_cambio("Imagen guardada.")
