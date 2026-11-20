"""Servidor de desarrollo: sirve web/ y expone la API por HTTP (solo para probar la interfaz
en un navegador normal; la aplicación real usa pywebview)."""
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import api

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
puente = api.Api()
if os.environ.get("RRHH_ALERTA"):
    puente.alerta_base = {"error": "database disk image is malformed", "hay_copias": True}
puente._dialogos = lambda tipo, **kw: os.environ.get("RRHH_DIALOGO") or None


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def do_POST(self):
        nombre = self.path.rsplit("/", 1)[-1]
        largo = int(self.headers.get("Content-Length") or 0)
        args = json.loads(self.rfile.read(largo) or b"[]")
        if nombre.startswith("_") or not hasattr(puente, nombre):
            self.send_error(404)
            return
        cuerpo = json.dumps(getattr(puente, nombre)(*args), ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    import base_datos as bd
    bd.crear_tablas()
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ThreadingHTTPServer(("127.0.0.1", puerto), Manejador).serve_forever()
