import os
import sys
import threading
from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk

import agenda
import base_datos as bd
import configuracion
import componentes as ui
import dialogo_evaluacion
import actualizador
import documentos
import modulos
import pagina_configuracion
import pagina_ranking
import pagina_respaldos
import respaldos
import tema
import version
from componentes import Etiqueta, ItemNav, Marco, Toast


class Aplicacion(tk.Tk):
    def __init__(self):
        super().__init__()
        self._revisar_base()
        bd.crear_tablas()
        configuracion.cargar()
        try:
            respaldos.respaldo_automatico()
        except Exception as e:
            self.after(1500, lambda: messagebox.showwarning("Respaldo automático", str(e)))
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
        if actualizador.puede_actualizarse():
            self.after(2500, lambda: self._buscar_actualizacion(False))

    def _poner_icono(self):
        carpeta = documentos._carpeta_plantillas()
        try:
            self._iconos = [tk.PhotoImage(file=os.path.join(carpeta, n))
                            for n in ("icono_app.png", "icono_32.png", "icono_16.png")
                            if os.path.exists(os.path.join(carpeta, n))]
            self.iconphoto(True, *self._iconos)
        except Exception as e:
            self._anotar_icono(e)
        if sys.platform == "win32":
            self.after(60, self._icono_windows)

    def _icono_windows(self):
        try:
            import ctypes
            u = ctypes.windll.user32
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DreamTravel.RRHH")
            ruta = os.path.join(documentos._carpeta_plantillas(), "icono.ico")
            ventana = u.GetParent(self.winfo_id()) or self.winfo_id()
            for grande, medida in ((0, 49), (1, 11)):
                tam = u.GetSystemMetrics(medida)
                gestor = u.LoadImageW(None, ruta, 1, tam, tam, 0x10)
                if gestor:
                    u.SendMessageW(ventana, 0x80, grande, gestor)
        except Exception as e:
            self._anotar_icono(e)

    def _anotar_icono(self, error):
        try:
            os.makedirs(bd.CARPETA_DATOS, exist_ok=True)
            with open(os.path.join(bd.CARPETA_DATOS, "icono.log"), "a", encoding="utf-8") as f:
                f.write(f"{error!r}\n")
        except OSError:
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
                          ("vacaciones", "Vacaciones"), ("memos", "Memorándums"),
                          ("ausencias", "Ausencias"))),
            ("Documentos", (("documentos", "Vista previa"),
                            ("pendientes", "Pendientes de completar"))),
            ("Sistema", (("respaldos", "Respaldos"), ("configuracion", "Configuración"))),
        )
        pie = Marco(lateral, fondo="lateral")
        pie.pack(side="bottom", fill="x", pady=(0, 14))
        self.item_actualizar = ItemNav(pie, f"Buscar actualizaciones  ·  v{version.VERSION}",
                                       lambda: self._buscar_actualizacion(True))
        self.item_actualizar.pack(fill="x")
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
            ("ausencias", modulos.ModuloCrud(
                self.contenido, self, "ausencias", "Ausencias",
                "Faltas, permisos e incapacidades de los empleados, desde que se reportan hasta su cierre",
                acciones=[("Siguiente etapa", modulos.accion_avanzar_ausencia)])),
            ("respaldos", pagina_respaldos.PaginaRespaldos(self.contenido, self)),
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

    def _buscar_actualizacion(self, manual):
        if getattr(self, "_buscando", False):
            return
        self._buscando = True
        resultado = {}

        def trabajo():
            try:
                resultado["datos"] = actualizador.buscar_nueva()
            except Exception as e:
                resultado["error"] = e
            resultado["listo"] = True

        def revisar():
            if not resultado.get("listo"):
                self.after(250, revisar)
                return
            self._buscando = False
            if "error" in resultado:
                if manual:
                    self.toast.mostrar("No se pudo comprobar: revisa tu conexión a internet", "error")
            elif resultado["datos"]:
                self._ofrecer_actualizacion(resultado["datos"])
            elif manual:
                self.toast.mostrar(f"Ya tienes la última versión (v{version.VERSION})", "ok")

        if manual:
            self.toast.mostrar("Buscando actualizaciones…", "ok")
        threading.Thread(target=trabajo, daemon=True).start()
        self.after(250, revisar)

    def _ofrecer_actualizacion(self, datos):
        notas = datos["notas"][:600]
        texto = (f"Hay una versión nueva: {datos['version']} (tienes v{version.VERSION}).\n\n"
                 + (notas + "\n\n" if notas else "") + "¿Actualizar ahora? La app se reiniciará.")
        if not actualizador.puede_actualizarse():
            messagebox.showinfo("Actualización disponible",
                                f"Hay una versión nueva ({datos['version']}). La actualización "
                                "automática solo funciona con RRHH.exe.", parent=self)
            return
        if not messagebox.askyesno("Actualización disponible", texto, parent=self):
            return
        pagina_docs = self.paginas.get("documentos")
        if pagina_docs is not None and not pagina_docs.confirmar_salida():
            return
        estado = {}

        def trabajo():
            try:
                actualizador.instalar_y_reiniciar(
                    datos, lambda f: estado.__setitem__("fraccion", f))
                estado["ok"] = True
            except Exception as e:
                estado["error"] = e
            estado["listo"] = True

        def revisar():
            if not estado.get("listo"):
                f = estado.get("fraccion")
                if f is not None:
                    self.toast.mostrar(f"Descargando actualización… {int(f * 100)}%", "ok", 900)
                self.after(400, revisar)
                return
            if estado.get("ok"):
                self.destroy()
            else:
                self.toast.mostrar("No se pudo actualizar; se mantiene esta versión", "error")
                messagebox.showerror("Actualización", f"No se pudo actualizar:\n{estado['error']}",
                                     parent=self)

        self.toast.mostrar("Descargando actualización…", "ok", 1500)
        threading.Thread(target=trabajo, daemon=True).start()
        self.after(400, revisar)

    def _cerrar(self):
        documentos_pagina = self.paginas.get("documentos")
        if documentos_pagina is not None and not documentos_pagina.confirmar_salida():
            return
        try:
            respaldos.respaldo_automatico(horas=2)
        except Exception:
            pass
        self.destroy()

    def _revisar_base(self):
        if not os.path.exists(bd.RUTA_DB):
            return
        estado = respaldos.verificar_archivo(bd.RUTA_DB)
        if estado["ok"]:
            return
        copias = [r for r in respaldos.listar_respaldos() if r["tipo"] != "Antes de restaurar"]
        detalle = estado["error"][:300]
        if copias and messagebox.askyesno(
                "Base de datos dañada",
                f"Se detectó un problema en la base de datos:\n{detalle}\n\n"
                f"¿Restaurar el respaldo más reciente ({copias[0]['fecha']:%d/%m/%Y %H:%M})?\n"
                "La base actual se conserva como copia de seguridad."):
            try:
                respaldos.restaurar(copias[0]["ruta"])
                return
            except Exception as e:
                messagebox.showerror("Restaurar", str(e))
        else:
            messagebox.showwarning("Base de datos", "Se abrirá la base tal como está. "
                                   "Entra a Respaldos para restaurar una copia.")


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
