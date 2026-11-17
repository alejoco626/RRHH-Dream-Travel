import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

import logica
import tema

ESTADO = {"modo": "claro"}
REGISTRO = []


def paleta():
    return tema.PALETAS[ESTADO["modo"]]


def registrar(widget, aplicar):
    widget._aplicar_tema = aplicar
    REGISTRO.append(widget)
    aplicar(widget, paleta())
    return widget


def recolorear_todo():
    p = paleta()
    vivos = []
    for w in REGISTRO:
        try:
            if w.winfo_exists():
                w._aplicar_tema(w, p)
                vivos.append(w)
        except tk.TclError:
            pass
    REGISTRO[:] = vivos


def podar():
    vivos = []
    for w in REGISTRO:
        try:
            if w.winfo_exists():
                vivos.append(w)
        except tk.TclError:
            pass
    REGISTRO[:] = vivos


def animar(widget, desde, hasta, aplicar, pasos=5, ms=14):
    token = object()
    widget._token_anim = token

    def paso(i):
        if getattr(widget, "_token_anim", None) is not token:
            return
        try:
            aplicar(desde + (hasta - desde) * i / pasos)
            if i < pasos:
                widget.after(ms, paso, i + 1)
        except tk.TclError:
            pass

    paso(1)


class Marco(tk.Frame):
    def __init__(self, master, fondo="tarjeta", borde=False, **kw):
        super().__init__(master, bd=0, highlightthickness=1 if borde else 0, **kw)

        def aplicar(w, p):
            w.configure(bg=p[fondo])
            if borde:
                w.configure(highlightbackground=p["borde"], highlightcolor=p["borde"])

        registrar(self, aplicar)


class Etiqueta(tk.Label):
    def __init__(self, master, texto="", fondo="tarjeta", tono="texto",
                 fuente=tema.F_TEXTO, **kw):
        kw.setdefault("anchor", "w")
        super().__init__(master, text=texto, font=fuente, bd=0, **kw)
        registrar(self, lambda w, p: w.configure(bg=p[fondo], fg=p[tono]))


def Separador(master, fondo="borde"):
    return Marco(master, fondo=fondo, height=1)


class Boton(tk.Canvas):
    def __init__(self, master, texto, comando, tipo="primario", fondo="tarjeta",
                 ancho=None, alto=38, fuente=tema.F_NEG):
        self._fuente = tkfont.Font(font=fuente)
        self.texto, self.comando, self.tipo, self.rol_fondo = texto, comando, tipo, fondo
        self._ancho_pedido = ancho or self._fuente.measure(texto) + 40
        super().__init__(master, width=self._ancho_pedido, height=alto, bd=0,
                         highlightthickness=0, cursor="hand2")
        self._alto = alto
        self._t = 0.0
        self._pulsado = False
        self._activo = True
        self._p = paleta()
        registrar(self, lambda w, p: w._recolorear(p))
        self.bind("<Enter>", lambda e: self._hover(1.0))
        self.bind("<Leave>", self._salir)
        self.bind("<ButtonPress-1>", self._presionar)
        self.bind("<ButtonRelease-1>", self._soltar)
        self._ancho_dibujado = None
        self._redibujo = None
        self.bind("<Configure>", self._al_configurar)

    def _al_configurar(self, e):
        if e.width != self._ancho_dibujado and self._redibujo is None:
            self._redibujo = self.after_idle(self._redibujar)

    def _redibujar(self):
        self._redibujo = None
        try:
            self._ancho_dibujado = self.winfo_width()
            self._dibujar()
        except tk.TclError:
            pass

    def _colores(self, p):
        if self.tipo == "primario":
            return p["primario"], p["primario_hover"], p["primario_texto"], \
                p["primario_texto"], None
        if self.tipo == "peligro":
            return p[self.rol_fondo], p["peligro"], p["peligro"], "#FFFFFF", p["peligro"]
        if self.tipo == "fantasma":
            return p[self.rol_fondo], p["sec_boton"], p["primario"] if \
                ESTADO["modo"] == "claro" else p["texto"], p["texto"], None
        return p["sec_boton"], p["sec_boton_hover"], p["texto"], p["texto"], None

    def _recolorear(self, p):
        self._p = p
        self.configure(bg=p[self.rol_fondo])
        self._dibujar()

    def _hover(self, objetivo):
        if self._activo:
            animar(self, self._t, objetivo, self._poner_t)

    def _poner_t(self, t):
        self._t = t
        self._dibujar()

    def _salir(self, _e):
        self._pulsado = False
        self._hover(0.0)

    def _presionar(self, _e):
        if self._activo:
            self._pulsado = True
            self._dibujar()

    def _soltar(self, e):
        disparar = (self._pulsado and self._activo and 0 <= e.x <= self.winfo_width()
                    and 0 <= e.y <= self._alto)
        self._pulsado = False
        self._dibujar()
        if disparar:
            self.comando()

    def activar(self, activo):
        self._activo = activo
        self.configure(cursor="hand2" if activo else "arrow")
        self._dibujar()

    def _dibujar(self):
        p = self._p
        base, sobre, txt, txt_sobre, borde = self._colores(p)
        ancho = self.winfo_width() if self.winfo_width() > 1 else self._ancho_pedido
        relleno = tema.mezclar(base, sobre, self._t)
        color_texto = tema.mezclar(txt, txt_sobre, self._t)
        if not self._activo:
            relleno, color_texto, borde = p["sec_boton"], p["sec"], None
        elif self._pulsado:
            relleno = tema.mezclar(relleno, "#000000", 0.12)
        self.delete("all")
        r = 9
        x1, y1, x2, y2 = 1, 1, ancho - 1, self._alto - 1
        puntos = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
                  x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        self.create_polygon(puntos, smooth=True, fill=relleno,
                            outline=borde or relleno, width=1)
        self.create_text(ancho / 2, self._alto / 2, text=self.texto, fill=color_texto,
                         font=self._fuente)


class ItemNav(tk.Frame):
    def __init__(self, master, texto, comando):
        super().__init__(master, height=40, bd=0, highlightthickness=0, cursor="hand2")
        self.pack_propagate(False)
        self.comando = comando
        self.activo = False
        self._t = 0.0
        self.indicador = tk.Frame(self, width=4, bd=0, highlightthickness=0)
        self.indicador.pack(side="left", fill="y")
        self.etiqueta = tk.Label(self, text=texto, font=tema.F_TEXTO, anchor="w", padx=16,
                                 bd=0, cursor="hand2")
        self.etiqueta.pack(side="left", fill="both", expand=True)
        self.insignia = tk.Label(self, text="", font=tema.F_PEQ_NEG, bd=0, padx=8, pady=1)
        for w in (self, self.etiqueta, self.insignia):
            w.bind("<Enter>", lambda e: self._hover(1.0))
            w.bind("<Leave>", lambda e: self._hover(0.0))
            w.bind("<Button-1>", lambda e: self.comando())
        registrar(self, lambda w, p: w._pintar(p))

    def _hover(self, objetivo):
        animar(self, self._t, objetivo, self._poner_t, pasos=4)

    def _poner_t(self, t):
        self._t = t
        self._pintar(paleta())

    def poner_activo(self, activo):
        self.activo = activo
        self._pintar(paleta())

    def poner_insignia(self, cantidad):
        if cantidad and cantidad > 0:
            self.insignia.configure(text=str(cantidad))
            self.insignia.pack(side="right", padx=(0, 14))
        else:
            self.insignia.pack_forget()

    def _pintar(self, p):
        fondo = p["lateral_activo"] if self.activo else \
            tema.mezclar(p["lateral"], p["lateral_hover"], self._t)
        self.configure(bg=fondo)
        self.indicador.configure(bg=p["lateral_texto"] if self.activo else fondo)
        self.etiqueta.configure(bg=fondo, fg=p["lateral_texto"] if self.activo or self._t > 0.4
                                else p["lateral_sec"])
        self.insignia.configure(bg=p["acento"], fg="#FFFFFF")


def pintar_lista_combo(combo):
    p = paleta()
    try:
        ventana = combo.tk.eval(f"ttk::combobox::PopdownWindow {combo}")
        combo.tk.call(f"{ventana}.f.l", "configure", "-background", p["campo"],
                      "-foreground", p["texto"], "-selectbackground", p["sel"],
                      "-selectforeground", p["texto"], "-borderwidth", 0,
                      "-highlightthickness", 0)
    except tk.TclError:
        pass


_TECLAS_EDICION = ("BackSpace", "Delete", "Insert")


def autoformato_fecha(entrada):
    def al_soltar(e):
        escribio = bool(e.char) and e.char.isprintable()
        if not (escribio or e.keysym in _TECLAS_EDICION or e.keysym.lower() in ("v", "x")):
            return
        texto = entrada.get()
        if "-" in texto:
            return
        nuevo, posicion = logica.formatear_fecha_escrita(
            texto, entrada.index("insert"), e.char if escribio else "")
        if nuevo != texto:
            entrada.delete(0, "end")
            entrada.insert(0, nuevo)
        entrada.icursor(posicion)

    entrada.bind("<KeyRelease>", al_soltar, add="+")


def _ancestro(widget, clase):
    while widget is not None:
        if isinstance(widget, clase):
            return widget
        widget = getattr(widget, "master", None)
    return None


def pasar_al_siguiente(evento):
    actual = evento.widget
    if not isinstance(actual, (ttk.Entry, ttk.Combobox)) or isinstance(actual, CampoBusqueda):
        return None
    ambito = actual
    while getattr(ambito, "master", None) is not None and not getattr(ambito, "_es_pagina", False):
        ambito = ambito.master
    candidato = actual
    for _ in range(300):
        candidato = candidato.tk_focusNext()
        if candidato is None or candidato == actual:
            break
        if not str(candidato).startswith(str(ambito)):
            continue
        if isinstance(candidato, (ttk.Entry, ttk.Combobox, tk.Text)):
            candidato.focus_set()
            zona = _ancestro(candidato, ZonaDesplazable)
            if zona is not None:
                zona.ver(candidato)
            break
    return "break"


def Combo(master, valores=(), solo_lectura=False, ancho=20):
    combo = ttk.Combobox(master, values=list(valores), width=ancho, style="Moderno.TCombobox",
                         state="readonly" if solo_lectura else "normal")
    combo.configure(postcommand=lambda c=combo: pintar_lista_combo(c))
    return combo


def CajaTexto(master, alto=3):
    caja = tk.Text(master, height=alto, width=10, wrap="word", relief="flat", bd=0,
                   highlightthickness=1, font=tema.F_TEXTO, padx=10, pady=8, undo=True)

    def aplicar(w, p):
        w.configure(bg=p["campo"], fg=p["texto"], insertbackground=p["texto"],
                    highlightbackground=p["campo_borde"], highlightcolor=p["primario"],
                    selectbackground=p["sel"], selectforeground=p["texto"])

    return registrar(caja, aplicar)


class CampoBusqueda(ttk.Entry):
    def __init__(self, master, ayuda, al_cambiar):
        self.var = tk.StringVar()
        super().__init__(master, textvariable=self.var, style="Moderno.TEntry", width=30)
        self.ayuda, self._al_cambiar = ayuda, al_cambiar
        self._mostrando_ayuda = False
        self._silencio = False
        self.bind("<FocusIn>", self._al_entrar)
        self.bind("<FocusOut>", self._al_salir)
        self.var.trace_add("write", self._cambio)
        registrar(self, lambda w, p: w._pintar())
        self._poner_ayuda()

    def texto(self):
        return "" if self._mostrando_ayuda else self.var.get().strip()

    def _pintar(self):
        p = paleta()
        self.configure(foreground=p["sec"] if self._mostrando_ayuda else p["texto"])

    def _poner_ayuda(self):
        self._silencio = True
        self._mostrando_ayuda = True
        self.var.set(self.ayuda)
        self._silencio = False
        self._pintar()

    def _al_entrar(self, _e):
        if self._mostrando_ayuda:
            self._silencio = True
            self._mostrando_ayuda = False
            self.var.set("")
            self._silencio = False
            self._pintar()

    def _al_salir(self, _e):
        if not self.var.get().strip():
            self._poner_ayuda()

    def _cambio(self, *_):
        if not self._silencio:
            self._al_cambiar()


class ZonaDesplazable(tk.Frame):
    def __init__(self, master, fondo="tarjeta", barra=True):
        super().__init__(master, bd=0, highlightthickness=0)
        self.lienzo = tk.Canvas(self, highlightthickness=0, bd=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview,
                                   style="Moderno.Vertical.TScrollbar")
        self.interior = Marco(self.lienzo, fondo=fondo)
        self._ventana = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")
        self.lienzo.configure(yscrollcommand=self.barra.set)
        self.lienzo.pack(side="left", fill="both", expand=True)
        if barra:
            self.barra.pack(side="right", fill="y")
        self._ajuste = None
        self.interior.bind("<Configure>", self._pedir_ajuste)
        self.lienzo.bind("<Configure>", self._pedir_ajuste)
        registrar(self.lienzo, lambda w, p: w.configure(bg=p[fondo]))

    def _pedir_ajuste(self, _e=None):
        if self._ajuste is None:
            self._ajuste = self.after_idle(self._ajustar)

    def _ajustar(self):
        self._ajuste = None
        try:
            self.lienzo.itemconfigure(self._ventana, width=self.lienzo.winfo_width())
            self.lienzo.configure(scrollregion=self.lienzo.bbox("all"))
        except tk.TclError:
            pass

    def desplazar(self, pasos):
        self.lienzo.yview_scroll(pasos, "units")

    def ver(self, widget):
        lienzo, interior = self.lienzo, self.interior
        total = interior.winfo_height()
        if total <= 1:
            return
        arriba = widget.winfo_rooty() - interior.winfo_rooty()
        abajo = arriba + widget.winfo_height()
        visible_ini = lienzo.canvasy(0)
        visible_fin = visible_ini + lienzo.winfo_height()
        if arriba < visible_ini + 30:
            lienzo.yview_moveto(max(0, (arriba - 60) / total))
        elif abajo > visible_fin - 30:
            lienzo.yview_moveto(min(1, (abajo - lienzo.winfo_height() + 60) / total))


def crear_tabla(master, columnas):
    cont = Marco(master, fondo="tarjeta")
    cont.rowconfigure(0, weight=1)
    cont.columnconfigure(0, weight=1)
    arbol = ttk.Treeview(cont, columns=[c[0] for c in columnas], show="headings",
                         selectmode="browse", style="Moderno.Treeview")
    for clave, titulo, ancho in columnas:
        arbol.heading(clave, text=titulo.upper(), anchor="w")
        arbol.column(clave, width=ancho, minwidth=50, anchor="w", stretch=True)
    barra = ttk.Scrollbar(cont, orient="vertical", command=arbol.yview,
                          style="Moderno.Vertical.TScrollbar")
    arbol.configure(yscrollcommand=barra.set)
    arbol.grid(row=0, column=0, sticky="nsew")
    barra.grid(row=0, column=1, sticky="ns")

    def aplicar(w, p):
        w.tag_configure("par", background=p["tarjeta"])
        w.tag_configure("impar", background=p["zebra"])
        w.tag_configure("atrasado", foreground=p["peligro"])

    registrar(arbol, aplicar)
    return cont, arbol


class Toast(tk.Label):
    COLORES = {"ok": "#15803D", "error": "#B42318", "info": "#1766AB"}

    def __init__(self, master):
        super().__init__(master, font=tema.F_TEXTO, fg="#FFFFFF", padx=20, pady=11, bd=0)
        self._espera = None

    def mostrar(self, mensaje, tipo="ok", ms=3200):
        if self._espera is not None:
            self.after_cancel(self._espera)
        self.configure(text=mensaje, bg=self.COLORES.get(tipo, self.COLORES["info"]))
        animar(self, 18, 0, lambda d: self.place(relx=1.0, rely=1.0, x=-28, y=-28 + d,
                                                 anchor="se"), pasos=5, ms=12)
        self.lift()
        self._espera = self.after(ms, self.place_forget)
