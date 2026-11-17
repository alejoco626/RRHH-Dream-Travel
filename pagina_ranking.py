import tkinter as tk
from tkinter import filedialog, messagebox

import base_datos as bd
import ranking
import tema
from componentes import Boton, Combo, Etiqueta, Marco, crear_tabla, podar
from modulos import Pagina, abrir_ruta

TODAS = "Todas las plazas"
SOLO_ACTIVOS = "Solo activos"
CON_DESCARTADOS = "Incluir no aprobados"


class PaginaRanking(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Ranking de candidatos",
                         "El mejor candidato de cada plaza, según la nota de la prueba de habilidades")
        self.v_plaza = tk.StringVar(value=TODAS)
        self.v_estado = tk.StringVar(value=SOLO_ACTIVOS)
        self.combo_plaza = Combo(self.zona_acciones, [], solo_lectura=True, ancho=24)
        self.combo_plaza.configure(textvariable=self.v_plaza)
        combo_estado = Combo(self.zona_acciones, [SOLO_ACTIVOS, CON_DESCARTADOS],
                             solo_lectura=True, ancho=20)
        combo_estado.configure(textvariable=self.v_estado)
        for combo in (self.combo_plaza, combo_estado):
            combo.pack(side="left", padx=(10, 0))
            combo.bind("<<ComboboxSelected>>", lambda e: self.refrescar())
        Boton(self.zona_acciones, "Plazas", self.gestionar_plazas, tipo="secundario",
              fondo="app").pack(side="left", padx=(10, 0))
        Boton(self.zona_acciones, "Exportar a Excel", self.exportar, tipo="secundario",
              fondo="app").pack(side="left", padx=(10, 0))
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(1, weight=1)
        self.tarjetas = Marco(self.cuerpo, fondo="app")
        self.tarjetas.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        lista = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        lista.grid(row=1, column=0, sticky="nsew")
        lista.rowconfigure(1, weight=1)
        lista.columnconfigure(0, weight=1)
        self.etiqueta_total = Etiqueta(lista, "", tono="sec")
        self.etiqueta_total.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 8))
        cont, self.arbol = crear_tabla(lista, [("pos", "#", 60), ("candidato", "Candidato", 230),
                                               ("plaza", "Plaza", 190), ("nota", "Nota", 90),
                                               ("etapa", "Etapa", 170),
                                               ("entrevista", "Entrevista", 130)])
        cont.grid(row=1, column=0, sticky="nsew", padx=(12, 4), pady=(0, 12))
        self.filas = []

    def _datos(self):
        plaza = self.v_plaza.get()
        return ranking.clasificar(
            bd.listar("embudo"), bd.listar("pruebas"), bd.listar("entrevistas"),
            None if plaza == TODAS else plaza, self.v_estado.get() == CON_DESCARTADOS)

    def _pintar_tarjetas(self):
        for w in self.tarjetas.winfo_children():
            w.destroy()
        for c in range(12):
            self.tarjetas.columnconfigure(c, weight=1 if c < len(ranking.PLAZAS) else 0,
                                          uniform="plaza" if c < len(ranking.PLAZAS) else "")
        mejores = ranking.mejores_por_plaza(bd.listar("embudo"), bd.listar("pruebas"),
                                            bd.listar("entrevistas"))
        for i, plaza in enumerate(ranking.PLAZAS):
            info = mejores[plaza]
            activa = self.v_plaza.get() == plaza
            tarjeta = Marco(self.tarjetas, fondo="tarjeta", borde=True)
            tarjeta.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            Marco(tarjeta, fondo="acento" if activa else "primario", height=3).pack(fill="x")
            Etiqueta(tarjeta, plaza, fuente=tema.F_NEG, wraplength=170, justify="left").pack(
                anchor="w", padx=14, pady=(10, 2))
            if info["mejor"]:
                Etiqueta(tarjeta, "★ " + info["mejor"]["candidato"], fuente=tema.F_SUB,
                         wraplength=170, justify="left").pack(anchor="w", padx=14)
                Etiqueta(tarjeta, f"{info['mejor']['nota']:g} %", fuente=tema.F_KPI).pack(
                    anchor="w", padx=14)
            else:
                Etiqueta(tarjeta, "Sin candidatos con nota", tono="sec").pack(anchor="w", padx=14)
            n = info["candidatos"]
            Etiqueta(tarjeta, f"{n} candidato{'s' if n != 1 else ''}", tono="sec",
                     fuente=tema.F_PEQ).pack(anchor="w", padx=14, pady=(2, 12))
            for w in [tarjeta] + tarjeta.winfo_children():
                w.configure(cursor="hand2")
                w.bind("<Button-1>", lambda e, p=plaza: self._elegir(p))

    def _elegir(self, plaza):
        self.v_plaza.set(TODAS if self.v_plaza.get() == plaza else plaza)
        self.refrescar()

    def gestionar_plazas(self):
        self.app.mostrar("configuracion")

    def refrescar(self):
        self.combo_plaza.configure(values=[TODAS] + ranking.PLAZAS + [ranking.SIN_PLAZA])
        if self.v_plaza.get() not in [TODAS, ranking.SIN_PLAZA] + ranking.PLAZAS:
            self.v_plaza.set(TODAS)
        self._pintar_tarjetas()
        self.filas = self._datos()
        self.arbol.delete(*self.arbol.get_children())
        for n, f in enumerate(self.filas):
            self.arbol.insert("", "end", iid=str(n), tags=("par" if n % 2 == 0 else "impar",),
                              values=(("★ " if n == 0 and f["nota"] is not None else "")
                                      + str(f["posicion"]), f["candidato"], f["plaza"],
                                      "" if f["nota"] is None else f"{f['nota']:g} %",
                                      f["etapa"], f["entrevista"]))
        total = len(self.filas)
        self.etiqueta_total.configure(
            text=f"{total} candidato{'s' if total != 1 else ''} · ordenados de la mejor a la menor nota")
        podar()

    def exportar(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar ranking", defaultextension=".xlsx", initialfile="ranking_candidatos.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        try:
            from openpyxl import Workbook
            libro = Workbook()
            hoja = libro.active
            hoja.title = "Ranking"
            hoja.append(["#", "Candidato", "Plaza", "Nota (%)", "Etapa", "Entrevista"])
            for f in self.filas:
                hoja.append([f["posicion"], f["candidato"], f["plaza"], f["nota"], f["etapa"],
                             f["entrevista"]])
            for letra, ancho in zip("ABCDEF", (6, 30, 26, 10, 24, 18)):
                hoja.column_dimensions[letra].width = ancho
            libro.save(ruta)
        except (OSError, ImportError) as e:
            messagebox.showerror("No se pudo exportar", str(e))
            return
        self.app.avisar_cambio("Ranking exportado.")
        abrir_ruta(ruta)

