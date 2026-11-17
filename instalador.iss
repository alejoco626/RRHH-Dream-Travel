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
Name: "{autoprograms}\{#NombreApp}"; Filename: "{app}\RRHH.exe"
Name: "{autodesktop}\{#NombreApp}"; Filename: "{app}\RRHH.exe"; Tasks: escritorio

[Run]
Filename: "{app}\RRHH.exe"; Description: "Abrir {#NombreApp} ahora"; Flags: nowait postinstall skipifsilent
