# RRHH – Dream & Travel

Aplicación de escritorio para Windows (Python + Tkinter + SQLite) del departamento de Recursos Humanos: embudo de confirmados, pruebas, entrevistas, ranking por plaza, personal, vacaciones y documentos.

## Descargar y ejecutar

1. Entra a **Releases** y descarga `RRHH.exe`.
2. Ábrelo con doble clic. No necesita instalar Python.
3. La carpeta `datos` (base de datos y documentos) se crea junto al `.exe`.

Si Windows muestra "SmartScreen", pulsa *Más información → Ejecutar de todos modos*.

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
