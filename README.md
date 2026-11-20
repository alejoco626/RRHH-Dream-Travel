# RRHH – Dream & Travel

Aplicación de escritorio para Windows (Python + pywebview + SQLite) del departamento de Recursos Humanos: embudo de confirmados, pruebas, entrevistas, ranking por plaza, personal, vacaciones y documentos.

## Descargar y ejecutar

1. Entra a **Releases** y descarga **`RRHH-Instalador.exe`**.
2. Ábrelo y sigue el asistente (no pide permisos de administrador). Crea el acceso directo en el escritorio y en el menú Inicio.
3. Tus datos (base de datos y documentos) se guardan en `%LOCALAPPDATA%\RRHH Dream & Travel\datos` y no se borran al actualizar ni al desinstalar.
4. La app se actualiza sola cuando hay una versión nueva.

`RRHH.exe` (portable, sin instalar) también está en Releases; guarda sus datos junto al `.exe` si ya hay una carpeta `datos` allí.

Si Windows muestra "SmartScreen", pulsa *Más información → Ejecutar de todos modos*.

## Interfaz

La interfaz es web (HTML, CSS y JavaScript sin dependencias externas, en la carpeta `web/`) dentro de una ventana **pywebview** (usa Microsoft Edge WebView2, ya incluido en Windows 10/11). Tiene gráficas SVG animadas, modo claro/oscuro y atajo Ctrl+S para guardar. La lógica y la base de datos siguen en Python; `api.py` es el puente entre ambas.

Para probar la interfaz en un navegador normal: `python servidor_dev.py` y abre http://127.0.0.1:8765.

## Respaldos

Menú **Respaldos**: verificación de integridad al abrir, copias automáticas (ZIP con base y adjuntos, últimas 15), respaldo manual, restauración segura, copia a otra carpeta y exportación a Excel.

## Ejecutar desde el código

```
pip install -r requisitos.txt
python rrhh.py
```

## Publicar una nueva versión

```
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions construye `RRHH.exe` y lo publica en Releases.

Más detalles de uso en `LEEME.txt`.
