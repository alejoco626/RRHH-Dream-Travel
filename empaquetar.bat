@echo off
REM Crea RRHH.exe (necesita:  pip install pyinstaller)
pyinstaller --noconfirm --onefile --windowed --name RRHH --icon "plantillas\icono.ico" ^
  --add-data "plantillas;plantillas" rrhh.py
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" instalador.iss
echo.
echo Listo: dist\RRHH.exe  y, si tienes Inno Setup, salida\RRHH-Instalador.exe  (la carpeta "datos" se crea junto al .exe al abrirlo)
pause
