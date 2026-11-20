import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import base_datos as bd
import respaldos
import tema
from componentes import Boton, Etiqueta, Marco, ZonaDesplazable, crear_tabla
from modulos import Pagina, abrir_ruta


def _tamano(n):
    for unidad in ("B", "KB", "MB", "GB"):
        if n < 1024 or unidad == "GB":
            return f"{n:.0f} {unidad}" if unidad == "B" else f"{n:.1f} {unidad}"
        n /= 1024


class PaginaRespaldos(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Respaldos",
                         "Verifica la base de datos y guarda copias de todos tus datos")
        Boton(self.zona_acciones, "Crear respaldo ahora", self.crear, tipo="primario",
              fondo="app").pack(side="left")
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(1, weight=1)

        estado = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        estado.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        estado.columnconfigure(0, weight=1)
        Marco(estado, fondo="primario", height=3).grid(row=0, column=0, sticky="ew")
        self.titulo_estado = Etiqueta(estado, "", fuente=tema.F_SUB)
        self.titulo_estado.grid(row=1, column=0, sticky="w", padx=18, pady=(12, 2))
        self.detalle = Etiqueta(estado, "", tono="sec", wraplength=900, justify="left")
        self.detalle.grid(row=2, column=0, sticky="w", padx=18)
        self.ubicacion = Etiqueta(estado, "", tono="sec", wraplength=900, justify="left")
        self.ubicacion.grid(row=3, column=0, sticky="w", padx=18, pady=(4, 0))
        botones = Marco(estado, fondo="tarjeta")
        botones.grid(row=4, column=0, sticky="w", padx=18, pady=(10, 16))
        for texto, f, tipo in (
                ("Verificar base de datos", self.verificar, "secundario"),
                ("Copia en otra carpeta…", self.elegir_externa, "secundario"),
                ("Abrir carpeta de respaldos", lambda: abrir_ruta(self._carpeta()), "secundario"),
                ("Exportar todo a Excel", self.exportar, "secundario")):
            Boton(botones, texto, f, tipo=tipo, alto=32, fuente=tema.F_PEQ_NEG).pack(
                side="left", padx=(0, 6))

        lista = Marco(self.cuerpo, fondo="tarjeta", borde=True)
        lista.grid(row=1, column=0, sticky="nsew")
        lista.rowconfigure(1, weight=1)
        lista.columnconfigure(0, weight=1)
        Etiqueta(lista, "Copias guardadas (se hace una automática al abrir y al cerrar)",
                 fuente=tema.F_SUB).grid(row=0, column=0, sticky="w", padx=18, pady=(12, 6))
        cont, self.arbol = crear_tabla(lista, [("fecha", "Fecha", 160), ("tipo", "Tipo", 140),
                                               ("tamano", "Tamaño", 100),
                                               ("nombre", "Archivo", 380)])
        cont.grid(row=1, column=0, sticky="nsew", padx=18)
        pie = Marco(lista, fondo="tarjeta")
        pie.grid(row=2, column=0, sticky="w", padx=18, pady=12)
        for texto, f, tipo in (("Restaurar la seleccionada", self.restaurar, "peligro"),
                               ("Restaurar desde archivo…", self.restaurar_archivo, "secundario"),
                               ("Guardar una copia como…", self.guardar_como, "secundario")):
            Boton(pie, texto, f, tipo=tipo, alto=32, fuente=tema.F_PEQ_NEG).pack(
                side="left", padx=(0, 6))
        self.filas = {}

    def _carpeta(self):
        os.makedirs(respaldos.carpeta_respaldos(), exist_ok=True)
        return respaldos.carpeta_respaldos()

    def refrescar(self):
        e = respaldos.verificar()
        if e["ok"]:
            self.titulo_estado.configure(text="Base de datos en buen estado")
            registros = sum(v for k, v in e["tablas"].items() if k != "adjuntos")
            self.detalle.configure(
                text=f"{registros} registros, {e['adjuntos']} archivos adjuntos "
                     f"({_tamano(e['tamano'] + e['tamano_adjuntos'])} en total). "
                     "Revisión de integridad y de enlaces: correcta.")
        else:
            self.titulo_estado.configure(text="Se detectaron problemas en la base de datos")
            self.detalle.configure(text=e["error"][:400] + "  Restaura una copia de la lista.")
        externa = bd.leer_config(respaldos.CLAVE_EXTERNA, "")
        self.ubicacion.configure(
            text=f"Datos: {bd.CARPETA_DATOS}\nCopia en otra carpeta: "
                 f"{externa or 'no configurada (recomendado: OneDrive, USB o disco de red)'}")
        self.filas = {}
        self.arbol.delete(*self.arbol.get_children())
        for i, r in enumerate(respaldos.listar_respaldos()):
            self.filas[str(i)] = r
            self.arbol.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                              values=(f"{r['fecha']:%d/%m/%Y %H:%M}", r["tipo"],
                                      _tamano(r["tamano"]), r["nombre"]))

    def verificar(self):
        self.refrescar()
        e = respaldos.verificar()
        if e["ok"]:
            self.app.avisar_cambio("Base de datos verificada: sin errores.")
        else:
            messagebox.showwarning("Verificación", e["error"][:600])

    def crear(self):
        try:
            info = respaldos.crear_respaldo(
                os.path.join(self._carpeta(), respaldos.nombre_nuevo(respaldos.PREFIJO_MANUAL)))
        except Exception as ex:
            messagebox.showerror("Respaldo", f"No se pudo crear el respaldo:\n{ex}")
            return
        externo = respaldos.copiar_externo(info["ruta"])
        self.refrescar()
        extra = " y en la otra carpeta" if externo else (
            " (falló la copia en la otra carpeta)" if externo is False else "")
        self.app.avisar_cambio(f"Respaldo creado{extra}.", "ok" if info["ok"] else "error")

    def elegir_externa(self):
        actual = bd.leer_config(respaldos.CLAVE_EXTERNA, "") or None
        carpeta = filedialog.askdirectory(title="Carpeta para copiar cada respaldo",
                                          initialdir=actual, parent=self)
        if carpeta:
            bd.guardar_config(respaldos.CLAVE_EXTERNA, carpeta)
            self.refrescar()
            self.app.avisar_cambio("Cada respaldo también se copiará a esa carpeta.")
        elif actual and messagebox.askyesno("Copia externa", "¿Dejar de copiar a otra carpeta?"):
            bd.guardar_config(respaldos.CLAVE_EXTERNA, "")
            self.refrescar()

    def exportar(self):
        ruta = filedialog.asksaveasfilename(
            parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile=f"RRHH_todos_los_datos_{datetime.now():%Y-%m-%d}.xlsx")
        if ruta:
            try:
                respaldos.exportar_todo_xlsx(ruta)
            except Exception as ex:
                messagebox.showerror("Exportar", str(ex))
                return
            self.app.avisar_cambio("Datos exportados a Excel.")

    def guardar_como(self):
        seleccion = self.arbol.selection()
        if not seleccion:
            messagebox.showinfo("Respaldos", "Selecciona una copia de la lista.")
            return
        r = self.filas[seleccion[0]]
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".zip",
                                            initialfile=r["nombre"],
                                            filetypes=[("Respaldo", "*.zip")])
        if ruta:
            import shutil
            shutil.copy2(r["ruta"], ruta)
            self.app.avisar_cambio("Copia guardada.")

    def restaurar(self):
        seleccion = self.arbol.selection()
        if not seleccion:
            messagebox.showinfo("Respaldos", "Selecciona una copia de la lista.")
            return
        self._restaurar(self.filas[seleccion[0]]["ruta"])

    def restaurar_archivo(self):
        ruta = filedialog.askopenfilename(parent=self, filetypes=[("Respaldo", "*.zip")])
        if ruta:
            self._restaurar(ruta)

    def _restaurar(self, ruta):
        if not messagebox.askyesno(
                "Restaurar respaldo",
                "Se reemplazarán TODOS los datos actuales (registros y archivos adjuntos) por los "
                "del respaldo.\nAntes se guarda una copia de seguridad de lo actual.\n\n"
                "La aplicación se cerrará para cargar los datos. ¿Continuar?"):
            return
        try:
            m = respaldos.restaurar(ruta)
        except Exception as ex:
            messagebox.showerror("Restaurar", str(ex))
            return
        messagebox.showinfo("Restaurar", f"Respaldo del {m.get('creado', '')[:10]} restaurado.\n"
                            "Vuelve a abrir la aplicación.")
        self.app.destroy()
