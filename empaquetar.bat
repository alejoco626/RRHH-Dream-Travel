@echo off
REM Crea RRHH.exe (necesita:  pip install pyinstaller)
pyinstaller --noconfirm --onefile --windowed --name RRHH --icon "plantillas\icono.ico" ^
  --add-data "plantillas;plantillas" rrhh.py
echo.
echo Listo: dist\RRHH.exe  (la carpeta "datos" se crea junto al .exe al abrirlo)
pause
