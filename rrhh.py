"""RRHH – Dream & Travel. Interfaz web (HTML/CSS/JS) dentro de una ventana pywebview."""
import os
import sys

import api
import base_datos as bd
import configuracion
import respaldos
import version


def carpeta_web():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "web")


def carpeta_plantillas():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "plantillas")


def _nitidez_en_windows():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DreamTravel.RRHH")
        except Exception:
            pass


def _anotar(error):
    try:
        os.makedirs(bd.CARPETA_DATOS, exist_ok=True)
        with open(os.path.join(bd.CARPETA_DATOS, "arranque.log"), "a", encoding="utf-8") as f:
            f.write(f"{error!r}\n")
    except OSError:
        pass


def _icono_windows(ventana):
    """Pone el icono de la empresa en la ventana y en la barra de tareas."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u = ctypes.windll.user32
        ruta = os.path.join(carpeta_plantillas(), "icono.ico")
        hwnd = int(ventana.native.Handle.ToInt64())
        for grande, medida in ((0, 49), (1, 11)):
            tam = u.GetSystemMetrics(medida)
            gestor = u.LoadImageW(None, ruta, 1, tam, tam, 0x10)
            if gestor:
                u.SendMessageW(hwnd, 0x80, grande, gestor)
    except Exception as e:
        _anotar(e)


def preparar():
    """Verifica la base antes de abrir; devuelve la alerta (o None) para la pantalla."""
    if os.path.exists(bd.RUTA_DB):
        estado = respaldos.verificar_archivo(bd.RUTA_DB)
        if not estado["ok"]:
            return {"error": estado["error"][:400],
                    "hay_copias": any(r["tipo"] != "Antes de restaurar"
                                      for r in respaldos.listar_respaldos())}
    bd.crear_tablas()
    configuracion.cargar()
    try:
        respaldos.respaldo_automatico()
    except Exception as e:
        _anotar(e)
    return None


def main():
    import webview
    _nitidez_en_windows()
    puente = api.Api()
    puente.alerta_base = preparar()
    ventana = webview.create_window(
        "RRHH – Dream & Travel", url=os.path.join(carpeta_web(), "index.html"), js_api=puente,
        width=1380, height=820, min_size=(1100, 640), background_color="#f3f6fa",
        text_select=True)
    puente._ventana = ventana
    ventana.events.shown += lambda: _icono_windows(ventana)

    def al_cerrar():
        if puente.alerta_base is None:
            try:
                respaldos.respaldo_automatico(horas=2)
            except Exception:
                pass
        return True
    ventana.events.closing += al_cerrar
    webview.start(debug=bool(os.environ.get("RRHH_DEBUG")))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        _anotar(e)
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, f"No se pudo abrir la aplicación:\n\n{e}\n\n"
                                                 "Si falta WebView2, instálalo desde "
                                                 "microsoft.com/edge/webview2.", "RRHH", 0x10)
            except Exception:
                pass
        raise
