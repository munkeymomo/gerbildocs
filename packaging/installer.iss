; Inno Setup script for GerbilDocs.
; Per-user install: no administrator rights needed.
; Build the bundle first:  python packaging/build.py

#define AppName    "GerbilDocs"
; The version comes from pyproject.toml via packaging/build.py (/DAppVersion=…);
; this default is only for running ISCC by hand.
#ifndef AppVersion
  #define AppVersion "1.4.1"
#endif
#define AppPublisher "Mark Isaacs"
#define AppExe     "GerbilDocs.exe"

[Setup]
SetupIconFile=app.ico
AppId={{7B3F1C42-2E2A-4E31-9A6D-0C1A2F5D8E11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
; OutputDir is overridden by build.py with /O; this is the by-hand default.
OutputDir=..\dist\installer
UninstallDisplayIcon={app}\{#AppExe}
VersionInfoVersion={#AppVersion}
OutputBaseFilename=GerbilDocs-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open {#AppName}"; Flags: nowait postinstall skipifsilent
