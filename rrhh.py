import os
import sys
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

import agenda
import base_datos as bd
import configuracion
import componentes as ui
import dialogo_evaluacion
import documentos
import modulos
import pagina_configuracion
import pagina_ranking
import tema
from componentes import Etiqueta, ItemNav, Marco, Toast


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        bd.crear_tablas()
        configuracion.cargar()
        self.title("RRHH – Dream & Travel")
        self._poner_icono()
        ancho = min(1380, self.winfo_screenwidth() - 40)
        alto = min(820, self.winfo_screenheight() - 90)
        self.geometry(f"{ancho}x{alto}+20+10")
        self.minsize(min(1100, ancho), min(620, alto))
        ui.ESTADO["modo"] = bd.leer_config("modo", "claro")
        self.estilo = ttk.Style(self)
        tema.aplicar_estilos(self.estilo, ui.paleta())
        ui.registrar(self, lambda w, p: w.configure(bg=p["fondo"]))
        self.option_add("*TCombobox*Listbox.font", tema.F_TEXTO)

        self.report_callback_exception = self._error_en_pantalla
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.items, self.paginas = {}, {}
        self.actual = None
        self._construir_lateral()

        self.contenido = Marco(self, fondo="app")
        self.contenido.grid(row=0, column=1, sticky="nsew")
        self.contenido.columnconfigure(0, weight=1)
        self.contenido.rowconfigure(0, weight=1)
        self._construir_paginas()

        self.toast = Toast(self)
        self.bind_all("<MouseWheel>", self._rueda)
        self.bind_all("<Button-4>", self._rueda)
        self.bind_all("<Button-5>", self._rueda)
        self.bind("<Return>", ui.pasar_al_siguiente)
        self.bind("<KP_Enter>", ui.pasar_al_siguiente)
        self.bind_all("<Control-s>", lambda e: self._atajo_guardar())
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.mostrar("resumen")

    def _poner_icono(self):
        carpeta = documentos._carpeta_plantillas()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "DreamTravel.RRHH")
            except Exception:
                pass
            try:
                self.iconbitmap(os.path.join(carpeta, "icono.ico"))
                return
            except tk.TclError:
                pass
        try:
            self._icono = tk.PhotoImage(file=os.path.join(carpeta, "icono_app.png"))
            self.iconphoto(True, self._icono)
        except tk.TclError:
            pass

    def _construir_lateral(self):
        lateral = Marco(self, fondo="lateral", width=240)
        lateral.grid(row=0, column=0, sticky="ns")
        lateral.pack_propagate(False)
        cabecera = Marco(lateral, fondo="lateral")
        cabecera.pack(fill="x", padx=22, pady=(26, 20))
        try:
            self._logo = tk.PhotoImage(file=os.path.join(
                documentos._carpeta_plantillas(), "logo_menu.png"))
            logo = tk.Label(cabecera, image=self._logo, bd=0)
            ui.registrar(logo, lambda w, p: w.configure(bg=p["lateral"]))
            logo.pack(side="left")
        except tk.TclError:
            pass
        textos = Marco(cabecera, fondo="lateral")
        textos.pack(side="left", padx=(10, 0))
        Etiqueta(textos, "Dream & Travel", fondo="lateral", tono="lateral_texto",
                 fuente=tema.F_MARCA, anchor="w").pack(fill="x")
        Etiqueta(textos, "RECURSOS HUMANOS", fondo="lateral", tono="lateral_sec",
                 fuente=tema.F_PEQ_NEG, anchor="w").pack(fill="x")

        grupos = (
            ("", (("resumen", "Resumen"),)),
            ("Selección", (("embudo", "Embudo de confirmados"), ("pruebas", "Pruebas"),
                           ("entrevistas", "Entrevistas"),
                           ("ranking", "Ranking de candidatos"),
                           ("no_aprobados", "No aprobados"))),
            ("Personal", (("empleados", "Empleados"), ("amonestaciones", "Amonestaciones"),
                          ("vacaciones", "Vacaciones"), ("memos", "Memorándums"))),
            ("Documentos", (("documentos", "Vista previa"),
                            ("pendientes", "Pendientes de completar"))),
            ("Sistema", (("configuracion", "Configuración"),)),
        )
        pie = Marco(lateral, fondo="lateral")
        pie.pack(side="bottom", fill="x", pady=(0, 14))
        self.item_modo = ItemNav(pie, "", self.alternar_modo)
        self.item_modo.pack(fill="x")
        self._texto_modo()
        menu = ui.ZonaDesplazable(lateral, fondo="lateral", barra=False)
        menu.pack(fill="both", expand=True)
        for titulo, elementos in grupos:
            if titulo:
                self._titulo_grupo(menu.interior, titulo)
            for clave, texto in elementos:
                item = ItemNav(menu.interior, texto, lambda c=clave: self.mostrar(c))
                item.pack(fill="x")
                self.items[clave] = item

    def _titulo_grupo(self, lateral, texto):
        fila = Marco(lateral, fondo="lateral")
        fila.pack(fill="x", padx=(20, 12), pady=(20, 6))
        Marco(fila, fondo="acento", width=4, height=16).pack(side="left", padx=(0, 10))
        Etiqueta(fila, texto, fondo="lateral", tono="lateral_texto",
                 fuente=tema.F_GRUPO).pack(side="left")
        Marco(fila, fondo="lateral_hover", height=1).pack(side="left", fill="x", expand=True,
                                                          padx=(12, 0), pady=(3, 0))

    def _construir_paginas(self):
        definicion = (
            ("resumen", modulos.Resumen(self.contenido, self)),
            ("embudo", modulos.ModuloCrud(
                self.contenido, self, "embudo", "Embudo de confirmados",
                "Personas que confirmaron su asistencia a las pruebas o a la entrevista",
                estado="Activo",
                acciones=[("Mover de etapa", modulos.accion_mover_etapa),
                          ("Registrar resultado", modulos.accion_registrar_resultado),
                          ("Marcar recibido", modulos.accion_marcar_recibido),
                          ("Descartar candidato", modulos.accion_descartar)])),
            ("no_aprobados", modulos.ModuloCrud(
                self.contenido, self, "embudo", "No aprobados",
                "Candidatos que no continúan en el proceso", clave="no_aprobados",
                estado="No aprobado",
                acciones=[("Reactivar en el embudo", modulos.accion_reactivar)])),
            ("pruebas", modulos.ModuloCrud(
                self.contenido, self, "pruebas", "Pruebas",
                "Cada prueba se registra con su ficha de calificaciones; la nota final es el "
                "promedio",
                boton_nuevo=False, formulario=False,
                acciones=[("Abrir / editar", modulos.accion_abrir_prueba, "secundario"),
                          ("Pasar a entrevista", modulos.accion_pasar_a_entrevista,
                           "secundario"),
                          ("Descartar candidato", modulos.accion_descartar_registro,
                           "secundario"),
                          ("Eliminar", modulos.accion_eliminar, "peligro")],
                acciones_cabecera=[("+ Prueba de habilidades",
                                    modulos.accion_nueva_habilidades, "primario"),
                                   ("+ Psicométrica", modulos.accion_nueva_psicometrica,
                                    "secundario"),
                                   ("Plantilla de importación",
                                    modulos.accion_plantilla_importacion, "fantasma"),
                                   ("Importar pruebas", modulos.accion_importar_pruebas,
                                    "secundario")])),
            ("entrevistas", modulos.ModuloCrud(
                self.contenido, self, "entrevistas", "Entrevistas",
                "Entrevistas realizadas a los candidatos",
                acciones=[("Descartar candidato", modulos.accion_descartar_registro)])),
            ("ranking", pagina_ranking.PaginaRanking(self.contenido, self)),
            ("configuracion", pagina_configuracion.PaginaConfiguracion(self.contenido, self)),
            ("empleados", modulos.ModuloCrud(
                self.contenido, self, "empleados", "Empleados",
                "Nombre, puesto y departamento son obligatorios; lo demás puedes ir "
                "completándolo")),
            ("amonestaciones", modulos.ModuloCrud(
                self.contenido, self, "amonestaciones", "Amonestaciones",
                "Cartas de amonestación y su comprobante firmado",
                acciones=[("Crear carta (Word)",
                           modulos.accion_amonestacion)])),
            ("vacaciones", modulos.ModuloCrud(
                self.contenido, self, "vacaciones", "Vacaciones",
                "Solicitud, constancia de goce y comprobantes escaneados",
                acciones=[("Sugerir periodo", modulos.accion_periodo),
                          ("Crear solicitud", modulos.accion_solicitud),
                          ("Crear constancia", modulos.accion_constancia)])),
            ("memos", modulos.ModuloCrud(
                self.contenido, self, "memos", "Memorándums",
                "Políticas internas firmadas por cada empleado")),
            ("documentos", modulos.PaginaDocumentos(self.contenido, self)),
            ("pendientes", modulos.Pendientes(self.contenido, self)),
        )
        for clave, pagina in definicion:
            pagina.grid(row=0, column=0, sticky="nsew")
            self.paginas[clave] = pagina

    def mostrar(self, clave):
        anterior = self.paginas.get(self.actual)
        if isinstance(anterior, modulos.PaginaDocumentos) and clave != self.actual \
                and not anterior.confirmar_salida():
            return
        self.actual = clave
        pagina = self.paginas[clave]
        pagina.refrescar()
        pagina.tkraise()
        for k, item in self.items.items():
            item.poner_activo(k == clave)
        self._actualizar_insignia()

    def ir_a(self, tabla, id_registro):
        self.mostrar(tabla)
        self.paginas[tabla].seleccionar(id_registro)

    def abrir_ficha(self, registro=None, valores=None, heredar=None):
        def guardada(id_registro):
            self.mostrar("pruebas")
            self.paginas["pruebas"].seleccionar(id_registro)
            self.avisar_cambio("Prueba guardada. Puedes agregar el CV o el Excel abajo.")
        dialogo_evaluacion.DialogoEvaluacion(self, registro, valores, heredar, guardada)

    def recargar_listas(self):
        for clave, pagina in self.paginas.items():
            if clave != "configuracion":
                pagina.refrescar()

    def nuevo_en(self, tabla, valores, heredar=None):
        self.mostrar(tabla)
        self.paginas[tabla].nuevo(valores, heredar)
        self.avisar_cambio("Completa el resultado y guarda.", "info")

    def ver_documento(self, ruta):
        self.mostrar("documentos")
        self.paginas["documentos"].mostrar(ruta)

    def avisar_cambio(self, mensaje="", tipo="ok"):
        if mensaje:
            self.toast.mostrar(mensaje, tipo)
        self._actualizar_insignia()

    def _actualizar_insignia(self):
        self.items["pendientes"].poner_insignia(len(bd.pendientes()))
        hoy = date.today()
        self.items["embudo"].poner_insignia(sum(
            1 for r in agenda.elementos(bd.listar("embudo"), bd.listar("pruebas"))
            if agenda.esta_atrasado(r, hoy)))

    def _texto_modo(self):
        noche = ui.ESTADO["modo"] == "noche"
        self.item_modo.etiqueta.configure(text="Cambiar a modo claro" if noche
                                          else "Cambiar a modo noche")

    def alternar_modo(self):
        ui.ESTADO["modo"] = "noche" if ui.ESTADO["modo"] == "claro" else "claro"
        bd.guardar_config("modo", ui.ESTADO["modo"])
        tema.aplicar_estilos(self.estilo, ui.paleta())
        ui.recolorear_todo()
        self._texto_modo()

    def _error_en_pantalla(self, tipo, valor, rastro):
        import traceback
        texto = "".join(traceback.format_exception(tipo, valor, rastro))
        try:
            with open(os.path.join(bd.CARPETA_DATOS, "errores.txt"), "a", encoding="utf8") as f:
                f.write(texto + "\n")
        except OSError:
            pass
        sys.stderr.write(texto)
        try:
            messagebox.showerror("Algo salió mal",
                                 f"{tipo.__name__}: {valor}\n\nEl detalle quedó en "
                                 f"datos/errores.txt")
        except Exception:
            pass

    def _rueda(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if isinstance(w, ui.ZonaDesplazable):
                subir = e.num == 4 or getattr(e, "delta", 0) > 0
                w.desplazar(-2 if subir else 2)
                return
            w = getattr(w, "master", None)

    def _atajo_guardar(self):
        pagina = self.paginas.get(self.actual)
        if hasattr(pagina, "guardar"):
            pagina.guardar()

    def _cerrar(self):
        documentos_pagina = self.paginas.get("documentos")
        if documentos_pagina is not None and not documentos_pagina.confirmar_salida():
            return
        self.destroy()


def _nitidez_en_windows():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def main():
    _nitidez_en_windows()
    try:
        Aplicacion().mainloop()
    except Exception as e:
        try:
            messagebox.showerror("RRHH", f"Ocurrió un error inesperado:\n\n{e}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
