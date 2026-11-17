import os
import tkinter as tk

import logica
import tema
from componentes import Boton, Etiqueta, Marco, crear_tabla, registrar


class DialogoImportacion(tk.Toplevel):
    def __init__(self, app, ruta, nuevas, repetidas, errores, al_confirmar):
        super().__init__(app)
        self.title("Importar pruebas")
        self.transient(app)
        self.al_confirmar = al_confirmar
        registrar(self, lambda w, p: w.configure(bg=p["fondo"]))

        ancho, alto = 820, 700 if errores else 620
        x = app.winfo_rootx() + max(0, (app.winfo_width() - ancho) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - alto) // 3)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.minsize(700, 520)

        raiz = Marco(self, fondo="app")
        raiz.pack(fill="both", expand=True, padx=26, pady=22)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(3, weight=1)

        Etiqueta(raiz, "Importar pruebas", fondo="app",
                 fuente=(tema.FAMILIA, 18, "bold")).grid(row=0, column=0, sticky="w")
        Etiqueta(raiz, os.path.basename(ruta), fondo="app", tono="sec").grid(
            row=1, column=0, sticky="w", pady=(2, 14))

        fichas = Marco(raiz, fondo="app")
        fichas.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        for i in range(3):
            fichas.columnconfigure(i, weight=1, uniform="ficha")
        datos = ((len(nuevas), "se importarán", "primario"),
                 (len(repetidas), "ya existían (se omiten)", "sec"),
                 (len(errores), "con problemas (se omiten)", "peligro"))
        for i, (numero, texto, color) in enumerate(datos):
            ficha = Marco(fichas, fondo="tarjeta", borde=True)
            ficha.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
            Marco(ficha, fondo=color, height=3).pack(fill="x")
            Etiqueta(ficha, str(numero), fuente=tema.F_KPI).pack(anchor="w", padx=16, pady=(8, 0))
            Etiqueta(ficha, texto, tono="sec").pack(anchor="w", padx=16, pady=(0, 12))

        vista = Marco(raiz, fondo="tarjeta", borde=True)
        vista.grid(row=3, column=0, sticky="nsew")
        vista.rowconfigure(1, weight=1)
        vista.columnconfigure(0, weight=1)
        Etiqueta(vista, "Vista previa", fuente=tema.F_SUB).grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 6))
        cont, arbol = crear_tabla(vista, [("candidato", "Candidato", 220),
                                          ("puesto", "Puesto", 150), ("fecha", "Fecha", 90),
                                          ("tipo", "Tipo de prueba", 160),
                                          ("puntaje", "Puntaje", 80)])
        cont.grid(row=1, column=0, sticky="nsew", padx=(12, 4), pady=(0, 10))
        for i, d in enumerate(nuevas[:300]):
            arbol.insert("", "end", values=(d["candidato"], d.get("puesto") or "",
                                            logica.formatear(d["fecha"]),
                                            d.get("tipo_prueba") or "", d.get("puntaje") or ""),
                         tags=("par" if i % 2 == 0 else "impar",))

        fila = 4
        if errores:
            raiz.rowconfigure(fila, weight=0)
            problemas = Marco(raiz, fondo="tarjeta", borde=True)
            problemas.grid(row=fila, column=0, sticky="ew", pady=(12, 0))
            problemas.columnconfigure(0, weight=1)
            Etiqueta(problemas, "Filas con problemas", fuente=tema.F_SUB).grid(
                row=0, column=0, sticky="w", padx=16, pady=(12, 4))
            cont_e, arbol_e = crear_tabla(problemas, [("fila", "Fila", 60),
                                                      ("problema", "Problema", 640)])
            arbol_e.configure(height=4)
            cont_e.grid(row=1, column=0, sticky="ew", padx=(12, 4), pady=(0, 10))
            for i, (numero, texto) in enumerate(errores[:100]):
                arbol_e.insert("", "end", values=(numero, texto),
                               tags=("par" if i % 2 == 0 else "impar",))
            fila += 1

        Etiqueta(raiz, "Las pruebas importadas quedan en «Pendientes de completar» hasta "
                       "que les adjuntes su archivo.", fondo="app", tono="sec").grid(
            row=fila, column=0, sticky="w", pady=(12, 0))
        botones = Marco(raiz, fondo="app")
        botones.grid(row=fila + 1, column=0, sticky="e", pady=(14, 0))
        Boton(botones, "Cancelar", self.destroy, tipo="secundario", fondo="app").pack(
            side="left", padx=(0, 10))
        self.boton_ok = Boton(botones, f"Importar {len(nuevas)} pruebas", self._confirmar,
                              fondo="app")
        self.boton_ok.pack(side="left")
        self.boton_ok.activar(len(nuevas) > 0)

        self.bind("<Escape>", lambda e: self.destroy())
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.focus_set()

    def _confirmar(self):
        self.destroy()
        self.al_confirmar()
