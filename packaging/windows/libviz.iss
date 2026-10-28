; packaging/windows/libviz.iss — Inno Setup script for the Windows installer.
; Built by packaging\windows\build.ps1 (which passes /DAppVersion from pyproject.toml).
;
; Per-user install into %LOCALAPPDATA%\Programs\LibViz: no admin rights, no UAC prompt.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Never change AppId: Windows uses it to recognise upgrades of the same app.
AppId={{3A365503-499F-4DFD-91FD-9F6151ADA17A}
AppName=LibViz
AppVersion={#AppVersion}
AppPublisher=Matteo Miotto
DefaultDirName={autopf}\LibViz
DefaultGroupName=LibViz
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\..\dist
OutputBaseFilename=LibViz-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\libviz-gui.exe
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\libviz-gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; An upgrade must not leave the previous version's libraries behind.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\LibViz"; Filename: "{app}\libviz-gui.exe"
Name: "{autodesktop}\LibViz"; Filename: "{app}\libviz-gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\libviz-gui.exe"; Description: "{cm:LaunchProgram,LibViz}"; Flags: nowait postinstall skipifsilent
