#define NombreApp "RRHH Dream & Travel"
#ifndef VersionApp
  #define VersionApp "1.0.0"
#endif

[Setup]
AppId={{B7D0B2E4-5C1A-4D8F-9A52-3E6C0F7A1D21}
AppName={#NombreApp}
AppVersion={#VersionApp}
AppPublisher=Dream & Travel
DefaultDirName={localappdata}\Programs\RRHH Dream & Travel
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=salida
OutputBaseFilename=RRHH-Instalador
SetupIconFile=plantillas\icono.ico
UninstallDisplayIcon={app}\RRHH.exe
UninstallDisplayName={#NombreApp}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\RRHH.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#NombreApp}"; Filename: "{app}\RRHH.exe"; AppUserModelID: "DreamTravel.RRHH"
Name: "{autodesktop}\{#NombreApp}"; Filename: "{app}\RRHH.exe"; AppUserModelID: "DreamTravel.RRHH"; Tasks: escritorio

[Run]
; Instalación normal: ofrece abrir la app.
Filename: "{app}\RRHH.exe"; Description: "Abrir {#NombreApp} ahora"; Flags: nowait postinstall skipifsilent
; Actualización automática (silenciosa): reabre la app y le avisa para que muestre las novedades.
Filename: "{app}\RRHH.exe"; Parameters: "--actualizado"; Flags: nowait skipifnotsilent

[Code]
function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  { El programa reabierto no debe heredar la carpeta temporal del anterior (error "Failed to load Python DLL"). }
  SetEnvironmentVariable('PYINSTALLER_RESET_ENVIRONMENT', '1');
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
begin
  { Si la app sigue abierta, se cierra para poder reemplazar RRHH.exe (si no está abierta, no pasa nada). }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM RRHH.exe', '', SW_HIDE, ewWaitUntilTerminated, Codigo);
  Sleep(800);
  Result := '';
end;
