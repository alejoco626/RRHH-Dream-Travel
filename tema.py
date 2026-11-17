import sys

AZUL = "#003D6B"
CORINTO = "#960018"

if sys.platform.startswith("win"):
    FAMILIA, SEMINEGRITA = "Segoe UI", "Segoe UI Semibold"
elif sys.platform == "darwin":
    FAMILIA, SEMINEGRITA = "Helvetica Neue", "Helvetica Neue"
else:
    FAMILIA, SEMINEGRITA = "DejaVu Sans", "DejaVu Sans"
F_TEXTO = (FAMILIA, 10)
F_PEQ = (FAMILIA, 9)
F_PEQ_NEG = (FAMILIA, 9, "bold")
F_NEG = (FAMILIA, 10, "bold")
F_SUB = (FAMILIA, 12, "bold")
F_TITULO = (FAMILIA, 22, "bold")
F_KPI = (FAMILIA, 30, "bold")
F_MARCA = (FAMILIA, 12, "bold")
F_GRUPO = (SEMINEGRITA, 11, "bold") if SEMINEGRITA == FAMILIA else (SEMINEGRITA, 11)

PALETAS = {
    "claro": dict(
        fondo="#F3F5F9", tarjeta="#FFFFFF", borde="#E2E8F0", texto="#0F172A", sec="#64748B",
        primario=AZUL, primario_hover="#0B5A93", primario_texto="#FFFFFF", acento=CORINTO,
        campo="#FFFFFF", campo_borde="#CBD5E1", sel="#E3EEF8", zebra="#F8FAFC",
        sec_boton="#EEF2F7", sec_boton_hover="#E1E8F0", peligro="#B42318",
        lateral=AZUL, lateral_hover="#0B5188", lateral_activo="#0F5C9C",
        lateral_texto="#FFFFFF", lateral_sec="#B7CBDD"),
    "noche": dict(
        fondo="#07090C", tarjeta="#11161D", borde="#212A36", texto="#E8EDF3", sec="#8A97A8",
        primario="#1766AB", primario_hover="#2379C2", primario_texto="#FFFFFF", acento="#D12A44",
        campo="#0C1117", campo_borde="#2B3644", sel="#14304A", zebra="#0E131A",
        sec_boton="#1B2430", sec_boton_hover="#243040", peligro="#F0616D",
        lateral="#00294A", lateral_hover="#0A3A63", lateral_activo="#0F4A7C",
        lateral_texto="#FFFFFF", lateral_sec="#9FB7CC"),
}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mezclar(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def _mapa_fijo(estilo, opcion):
    return [e for e in estilo.map("Treeview", query_opt=opcion)
            if e[:2] != ("!disabled", "!selected")]


def aplicar_estilos(e, p):
    e.theme_use("clam")
    e.configure(".", background=p["tarjeta"], foreground=p["texto"], font=F_TEXTO,
                bordercolor=p["borde"], lightcolor=p["borde"], darkcolor=p["borde"],
                troughcolor=p["fondo"], focuscolor=p["tarjeta"])
    foco = [("focus", p["primario"])]

    e.configure("Moderno.TEntry", fieldbackground=p["campo"], foreground=p["texto"],
                bordercolor=p["campo_borde"], lightcolor=p["campo_borde"],
                darkcolor=p["campo_borde"], insertcolor=p["texto"], padding=(10, 8))
    e.map("Moderno.TEntry", bordercolor=foco, lightcolor=foco, darkcolor=foco,
          fieldbackground=[("readonly", p["fondo"])], foreground=[("readonly", p["texto"])])

    rojo = [("focus", p["peligro"])]
    e.configure("Error.Moderno.TEntry", fieldbackground=mezclar(p["campo"], p["peligro"], 0.14),
                bordercolor=p["peligro"], lightcolor=p["peligro"], darkcolor=p["peligro"])
    e.map("Error.Moderno.TEntry", bordercolor=rojo, lightcolor=rojo, darkcolor=rojo)

    e.configure("Moderno.TCombobox", fieldbackground=p["campo"], background=p["campo"],
                foreground=p["texto"], arrowcolor=p["sec"], bordercolor=p["campo_borde"],
                lightcolor=p["campo_borde"], darkcolor=p["campo_borde"], padding=(10, 8),
                arrowsize=16, insertcolor=p["texto"])
    e.map("Moderno.TCombobox", bordercolor=foco, lightcolor=foco, darkcolor=foco,
          fieldbackground=[("readonly", p["campo"])], foreground=[("readonly", p["texto"])],
          selectbackground=[("readonly", p["campo"])],
          selectforeground=[("readonly", p["texto"])],
          background=[("active", p["fondo"]), ("readonly", p["campo"])])

    e.map("Treeview", foreground=_mapa_fijo(e, "foreground"),
          background=_mapa_fijo(e, "background"))
    e.configure("Moderno.Treeview", background=p["tarjeta"], fieldbackground=p["tarjeta"],
                foreground=p["texto"], rowheight=38, borderwidth=0, relief="flat",
                font=F_TEXTO)
    e.map("Moderno.Treeview", background=[("selected", p["sel"])],
          foreground=[("selected", p["texto"])])
    e.configure("Moderno.Treeview.Heading", background=p["fondo"], foreground=p["sec"],
                relief="flat", borderwidth=0, padding=(12, 10), font=F_PEQ_NEG)
    e.map("Moderno.Treeview.Heading", background=[("active", p["fondo"])])
    try:
        e.layout("Moderno.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    except Exception:
        pass

    try:
        e.layout("Moderno.Vertical.TScrollbar", [
            ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
                ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        e.configure("Moderno.Vertical.TScrollbar", background=p["campo_borde"],
                    troughcolor=p["tarjeta"], bordercolor=p["tarjeta"],
                    lightcolor=p["campo_borde"], darkcolor=p["campo_borde"],
                    gripcount=0, width=9)
        e.map("Moderno.Vertical.TScrollbar",
              background=[("active", p["sec"]), ("pressed", p["sec"])])
    except Exception:
        pass


for _p in PALETAS.values():
    _p.setdefault("app", _p["fondo"])
