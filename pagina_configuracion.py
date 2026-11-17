import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import base_datos as bd
import configuracion
import evaluacion
import logica
import ranking
import tema
from componentes import (Boton, CajaTexto, Etiqueta, Marco, ZonaDesplazable, crear_tabla,
                         podar, registrar)
from modulos import Pagina


def _preguntar(ventana, titulo, texto, inicial=""):
    valor = simpledialog.askstring(titulo, texto, initialvalue=inicial, parent=ventana)
    valor = (valor or "").strip()
    return valor or None


class Tarjeta(Marco):
    def __init__(self, master, pagina, titulo, ayuda):
        super().__init__(master, fondo="tarjeta", borde=True)
        self.pagina = pagina
        self.columnconfigure(0, weight=1)
        Marco(self, fondo="primario", height=3).grid(row=0, column=0, sticky="ew")
        Etiqueta(self, titulo, fuente=tema.F_SUB).grid(row=1, column=0, sticky="w",
                                                        padx=18, pady=(12, 2))
        Etiqueta(self, ayuda, tono="sec", wraplength=430, justify="left").grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 8))
        self.cuerpo = Marco(self, fondo="tarjeta")
        self.cuerpo.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.cuerpo.columnconfigure(0, weight=1)

    def botones(self, fila, *definiciones):
        marco = Marco(self.cuerpo, fondo="tarjeta")
        marco.grid(row=fila, column=0, sticky="w", pady=(10, 0))
        for texto, funcion, tipo in definiciones:
            Boton(marco, texto, funcion, tipo=tipo, alto=32, fuente=tema.F_PEQ_NEG).pack(
                side="left", padx=(0, 6))

    def tabla(self, columnas, alto=6):
        cont, arbol = crear_tabla(self.cuerpo, columnas)
        arbol.configure(height=alto)
        cont.grid(row=0, column=0, sticky="ew")
        return arbol

    def elegida(self, arbol):
        seleccion = arbol.selection()
        if not seleccion:
            messagebox.showinfo("Configuración", "Selecciona un elemento de la lista.")
            return None
        return int(seleccion[0])

    def llenar(self, arbol, filas):
        arbol.delete(*arbol.get_children())
        for i, valores in enumerate(filas):
            arbol.insert("", "end", iid=str(i), tags=("par" if i % 2 == 0 else "impar",),
                         values=valores)


class EditorLista(Tarjeta):
    def __init__(self, master, pagina, titulo, ayuda, lista, renombrar=None):
        super().__init__(master, pagina, titulo, ayuda)
        self.lista, self._renombrar = lista, renombrar
        self.arbol = self.tabla([("valor", titulo, 380)])
        self.botones(1, ("Agregar", self.agregar, "primario"),
                     ("Renombrar", self.renombrar, "secundario"),
                     ("Quitar", self.quitar, "peligro"),
                     ("▲", lambda: self.mover(-1), "fantasma"),
                     ("▼", lambda: self.mover(1), "fantasma"))
        self.pintar()

    def pintar(self):
        self.llenar(self.arbol, [(v,) for v in self.lista])

    def _guardar(self, seleccionar=None):
        self.pintar()
        if seleccionar is not None and seleccionar < len(self.lista):
            self.arbol.selection_set(str(seleccionar))
        self.pagina.guardado()

    def _valido(self, nombre, original=""):
        if any(v.lower() == nombre.lower() and v != original for v in self.lista):
            messagebox.showwarning("Configuración", "Ese valor ya existe.")
            return False
        return True

    def agregar(self):
        nombre = _preguntar(self, "Agregar", "Nuevo valor:")
        if nombre and self._valido(nombre):
            self.lista.append(nombre)
            self._guardar(len(self.lista) - 1)

    def renombrar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        viejo = self.lista[i]
        nombre = _preguntar(self, "Renombrar", "Nuevo nombre:", viejo)
        if nombre and nombre != viejo and self._valido(nombre, viejo):
            self.lista[i] = nombre
            if self._renombrar:
                self._renombrar(viejo, nombre)
            self._guardar(i)

    def quitar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        if len(self.lista) == 1:
            messagebox.showinfo("Configuración", "Debe quedar al menos un valor.")
            return
        if messagebox.askyesno("Quitar", f"¿Quitar «{self.lista[i]}» de la lista?\n"
                               "Los registros que ya lo usan conservan su valor."):
            self.lista.pop(i)
            self._guardar()

    def mover(self, delta):
        i = self.elegida(self.arbol)
        if i is None or not 0 <= i + delta < len(self.lista):
            return
        self.lista[i], self.lista[i + delta] = self.lista[i + delta], self.lista[i]
        self._guardar(i + delta)


class EditorGrupos(Tarjeta):
    def __init__(self, master, pagina):
        super().__init__(master, pagina, "Grupos de autorización de vacaciones",
                         "Cada grupo tiene las personas que pueden autorizar. Sepáralas con coma.")
        self.arbol = self.tabla([("grupo", "Grupo", 190), ("autorizan", "Autorizan", 200)])
        self.botones(1, ("Agregar", self.agregar, "primario"),
                     ("Editar", self.editar, "secundario"),
                     ("Quitar", self.quitar, "peligro"))
        self.pintar()

    def pintar(self):
        self.llenar(self.arbol, [(g, ", ".join(a)) for g, a in
                                 logica.GRUPOS_AUTORIZACION.items()])

    def _pedir(self, grupo="", autorizan=""):
        nombre = _preguntar(self, "Grupo", "Nombre del grupo:", grupo)
        if not nombre:
            return None
        texto = simpledialog.askstring("Grupo", "Quién autoriza (separa con coma):",
                                       initialvalue=autorizan, parent=self)
        if texto is None:
            return None
        return nombre, [p.strip() for p in texto.split(",") if p.strip()]

    def _nombres(self):
        return list(logica.GRUPOS_AUTORIZACION)

    def agregar(self):
        r = self._pedir()
        if not r:
            return
        if r[0] in logica.GRUPOS_AUTORIZACION:
            messagebox.showwarning("Configuración", "Ese grupo ya existe.")
            return
        logica.GRUPOS_AUTORIZACION[r[0]] = r[1]
        self.pagina.guardado()
        self.pintar()

    def editar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        viejo = self._nombres()[i]
        r = self._pedir(viejo, ", ".join(logica.GRUPOS_AUTORIZACION[viejo]))
        if not r:
            return
        if r[0] != viejo and r[0] in logica.GRUPOS_AUTORIZACION:
            messagebox.showwarning("Configuración", "Ese grupo ya existe.")
            return
        nuevo = {}
        for g, a in logica.GRUPOS_AUTORIZACION.items():
            nuevo[r[0] if g == viejo else g] = r[1] if g == viejo else a
        logica.GRUPOS_AUTORIZACION.clear()
        logica.GRUPOS_AUTORIZACION.update(nuevo)
        if r[0] != viejo:
            bd.renombrar_valor("empleados", "grupo", viejo, r[0])
        self.pagina.guardado()
        self.pintar()

    def quitar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        grupo = self._nombres()[i]
        if len(logica.GRUPOS_AUTORIZACION) == 1:
            messagebox.showinfo("Configuración", "Debe quedar al menos un grupo.")
            return
        if messagebox.askyesno("Quitar", f"¿Quitar el grupo «{grupo}»?\n"
                               "Los empleados que lo tenían conservan su valor."):
            del logica.GRUPOS_AUTORIZACION[grupo]
            self.pagina.guardado()
            self.pintar()


class EditorDatos(Tarjeta):
    def __init__(self, master, pagina):
        super().__init__(master, pagina, "Documentos y avisos",
                         "Datos que aparecen en el encabezado de los documentos y en el Resumen.")
        import documentos
        self.documentos = documentos
        self.vars = {
            "empresa": tk.StringVar(value=documentos.EMPRESA),
            "area": tk.StringVar(value=documentos.AREA),
            "ciudad": tk.StringVar(value=documentos.CIUDAD),
            "dias_cumpleanos": tk.StringVar(value=str(configuracion.PARAMETROS["dias_cumpleanos"])),
            "escala": tk.StringVar(value=evaluacion.ESCALA)}
        for fila, (clave, texto) in enumerate((
                ("empresa", "Nombre de la empresa (encabezado)"),
                ("area", "Área o departamento (encabezado)"),
                ("ciudad", "Ciudad que aparece en la fecha de los documentos"),
                ("dias_cumpleanos", "Avisar cumpleaños con cuántos días de anticipación"),
                ("escala", "Escala de calificación de la ficha (texto de ayuda)"))):
            Etiqueta(self.cuerpo, texto, tono="sec", fuente=tema.F_PEQ).grid(
                row=fila * 2, column=0, sticky="w", pady=(8, 2))
            ttk.Entry(self.cuerpo, textvariable=self.vars[clave], style="Moderno.TEntry").grid(
                row=fila * 2 + 1, column=0, sticky="ew")
        self.botones(10, ("Guardar cambios", self.guardar, "primario"))

    def pintar(self):
        self.vars["empresa"].set(self.documentos.EMPRESA)
        self.vars["area"].set(self.documentos.AREA)
        self.vars["ciudad"].set(self.documentos.CIUDAD)
        self.vars["dias_cumpleanos"].set(str(configuracion.PARAMETROS["dias_cumpleanos"]))
        self.vars["escala"].set(evaluacion.ESCALA)

    def guardar(self):
        try:
            dias = int(self.vars["dias_cumpleanos"].get().strip())
            if not 1 <= dias <= 365:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Configuración", "Los días de aviso deben ser un número entre 1 y 365.")
            return
        textos = {k: self.vars[k].get().strip() for k in ("empresa", "area", "ciudad", "escala")}
        if not all(textos.values()):
            messagebox.showwarning("Configuración", "Completa la empresa, el área, la ciudad y la escala.")
            return
        self.documentos.EMPRESA, self.documentos.AREA = textos["empresa"], textos["area"]
        self.documentos.CIUDAD = textos["ciudad"]
        evaluacion.ESCALA = textos["escala"]
        configuracion.PARAMETROS["dias_cumpleanos"] = dias
        self.pagina.guardado()


class EditorFicha(Tarjeta):
    def __init__(self, master, pagina):
        super().__init__(master, pagina, "Criterios de la ficha de evaluación",
                         "Secciones y criterios de la prueba de habilidades. Los cambios aplican "
                         "a las fichas nuevas o que abras; las notas ya guardadas de criterios "
                         "con el mismo nombre se conservan.")
        self.arbol = self.tabla([("seccion", "Sección", 260), ("criterios", "Criterios", 70),
                                 ("maximo", "Puntos", 70)], alto=7)
        self.botones(1, ("Agregar sección", self.agregar, "primario"),
                     ("Editar", self.editar, "secundario"),
                     ("Quitar", self.quitar, "peligro"),
                     ("▲", lambda: self.mover(-1), "fantasma"),
                     ("▼", lambda: self.mover(1), "fantasma"))
        self.pintar()

    def pintar(self):
        self.llenar(self.arbol, [
            (s["nombre"], len(s["criterios"]), f"{sum(m for _, m in s['criterios']):g}")
            for s in evaluacion.SECCIONES])

    def _guardar(self, seleccionar=None):
        self.pintar()
        if seleccionar is not None:
            self.arbol.selection_set(str(seleccionar))
        self.pagina.guardado()

    def agregar(self):
        d = DialogoSeccion(self, None)
        self.wait_window(d)
        if d.resultado:
            evaluacion.SECCIONES.append(d.resultado)
            self._guardar(len(evaluacion.SECCIONES) - 1)

    def editar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        d = DialogoSeccion(self, evaluacion.SECCIONES[i])
        self.wait_window(d)
        if d.resultado:
            evaluacion.SECCIONES[i] = d.resultado
            self._guardar(i)

    def quitar(self):
        i = self.elegida(self.arbol)
        if i is None:
            return
        if len(evaluacion.SECCIONES) == 1:
            messagebox.showinfo("Configuración", "Debe quedar al menos una sección.")
            return
        if messagebox.askyesno("Quitar", f"¿Quitar «{evaluacion.SECCIONES[i]['nombre']}»?\n"
                               "Las fichas ya guardadas no se borran, pero esa sección dejará "
                               "de mostrarse en ellas."):
            evaluacion.SECCIONES.pop(i)
            self._guardar()

    def mover(self, delta):
        i = self.elegida(self.arbol)
        if i is None or not 0 <= i + delta < len(evaluacion.SECCIONES):
            return
        s = evaluacion.SECCIONES
        s[i], s[i + delta] = s[i + delta], s[i]
        self._guardar(i + delta)


class DialogoSeccion(tk.Toplevel):
    def __init__(self, padre, seccion):
        super().__init__(padre)
        self.resultado = None
        self.title("Sección de la ficha")
        self.transient(padre.winfo_toplevel())
        registrar(self, lambda w, p: w.configure(bg=p["fondo"]))
        self.geometry("640x560")
        raiz = Marco(self, fondo="app")
        raiz.pack(fill="both", expand=True, padx=22, pady=18)
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(5, weight=1)
        self.v_nombre = tk.StringVar(value=seccion["nombre"] if seccion else "")
        self.v_global = tk.StringVar(value=(seccion["global"] or "") if seccion else "")
        Etiqueta(raiz, "Nombre de la sección", fondo="app", tono="sec", fuente=tema.F_PEQ).grid(
            row=0, column=0, sticky="w")
        ttk.Entry(raiz, textvariable=self.v_nombre, style="Moderno.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(2, 10))
        Etiqueta(raiz, "Texto del puntaje global (opcional, sobre 10)", fondo="app", tono="sec",
                 fuente=tema.F_PEQ).grid(row=2, column=0, sticky="w")
        ttk.Entry(raiz, textvariable=self.v_global, style="Moderno.TEntry").grid(
            row=3, column=0, sticky="ew", pady=(2, 10))
        Etiqueta(raiz, "Criterios: uno por línea, con su máximo así:  Criterio | 5",
                 fondo="app", tono="sec", fuente=tema.F_PEQ).grid(row=4, column=0, sticky="w")
        self.texto = CajaTexto(raiz, alto=12)
        self.texto.grid(row=5, column=0, sticky="nsew", pady=(2, 10))
        if seccion:
            self.texto.insert("1.0", "\n".join(f"{c} | {m:g}" for c, m in seccion["criterios"]))
        botones = Marco(raiz, fondo="app")
        botones.grid(row=6, column=0, sticky="e")
        Boton(botones, "Cancelar", self.destroy, tipo="secundario", fondo="app").pack(
            side="left", padx=(0, 8))
        Boton(botones, "Guardar", self.guardar, fondo="app").pack(side="left")
        self.bind("<Escape>", lambda e: self.destroy())
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass

    def guardar(self):
        nombre = self.v_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Sección", "Escribe el nombre de la sección.", parent=self)
            return
        try:
            criterios = configuracion.leer_criterios(self.texto.get("1.0", "end"))
        except ValueError as e:
            messagebox.showwarning("Sección", str(e), parent=self)
            return
        self.resultado = {"nombre": nombre, "global": self.v_global.get().strip() or None,
                          "criterios": criterios}
        self.destroy()


class PaginaConfiguracion(Pagina):
    def __init__(self, master, app):
        super().__init__(master, app, "Configuración",
                         "Listas, datos de documentos y criterios que puedes editar sin tocar el código")
        Boton(self.zona_acciones, "Restablecer valores originales", self.restablecer,
              tipo="peligro", fondo="app").pack(side="left")
        self.cuerpo.columnconfigure(0, weight=1)
        self.cuerpo.rowconfigure(0, weight=1)
        zona = ZonaDesplazable(self.cuerpo, fondo="app")
        zona.grid(row=0, column=0, sticky="nsew")
        rejilla = zona.interior
        rejilla.columnconfigure((0, 1), weight=1, uniform="cfg")
        self.editores = [
            EditorLista(rejilla, self, "Plazas", "Plazas a las que aplican los candidatos; "
                        "se usan en el Embudo, la ficha, las entrevistas y el Ranking.",
                        ranking.PLAZAS, ranking_renombrar),
            EditorLista(rejilla, self, "Departamentos", "Departamentos de los empleados.",
                        configuracion.DEPARTAMENTOS,
                        lambda v, n: bd.renombrar_valor("empleados", "departamento", v, n)),
            EditorGrupos(rejilla, self),
            EditorLista(rejilla, self, "Temas de memorándum", "Políticas que firman los empleados.",
                        configuracion.TEMAS_MEMO,
                        lambda v, n: bd.renombrar_valor("memos", "tema", v, n)),
            EditorLista(rejilla, self, "Tipos de archivo", "Clasificación de los archivos que se "
                        "suben a candidatos (CV, Excel…).", bd.CATEGORIAS_ADJUNTO,
                        lambda v, n: bd.renombrar_valor("adjuntos", "categoria", v, n)),
            EditorDatos(rejilla, self),
            EditorFicha(rejilla, self)]
        for i, tarjeta in enumerate(self.editores):
            ancho = i == len(self.editores) - 1
            tarjeta.grid(row=i // 2, column=0, columnspan=2 if ancho and i % 2 == 0 else 1,
                         sticky="nsew", padx=(0, 8) if i % 2 == 0 else (8, 0), pady=(0, 14))
            if i % 2 == 1:
                tarjeta.grid_configure(column=1)
        self.editores[-1].grid_configure(column=0, columnspan=2, padx=0)

    def guardado(self):
        configuracion.guardar()
        self.app.recargar_listas()
        self.app.avisar_cambio("Configuración guardada.")

    def restablecer(self):
        if not messagebox.askyesno(
                "Restablecer", "¿Volver a los valores originales de todas las listas y datos?\n"
                "Los registros ya guardados no se modifican."):
            return
        configuracion.restablecer()
        for editor in self.editores:
            if hasattr(editor, "pintar"):
                editor.pintar()
        self.app.recargar_listas()
        self.app.avisar_cambio("Valores originales restablecidos.")

    def refrescar(self):
        for editor in self.editores:
            if hasattr(editor, "pintar"):
                editor.pintar()
        podar()


def ranking_renombrar(viejo, nuevo):
    bd.renombrar_plaza(viejo, nuevo)
