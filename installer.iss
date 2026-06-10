; Inno Setup script для Jarvis
; Сборка: build_installer.bat (или ISCC.exe installer.iss)
; Перед сборкой соберите exe: build_gui.bat (нужна папка dist\Jarvis)

#define AppName "Jarvis"
#define AppVersion "0.2.0"
#define AppPublisher "lastlofty"
#define AppExe "Jarvis.exe"

[Setup]
AppId={{8F2A6C31-9B4E-4D2A-9C7E-1A2B3C4D5E6F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Ставим в пользовательскую папку — агент пишет data/.env рядом с собой,
; поэтому не нужны права администратора и Program Files (только чтение).
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\Jarvis
DefaultGroupName=Jarvis
DisableProgramGroupPage=yes
OutputDir=installer_out
OutputBaseFilename=Jarvis-Setup-{#AppVersion}
SetupIconFile=jarvis.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Запускать Jarvis при входе в Windows"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
; Вся папка onedir-сборки PyInstaller
Source: "dist\Jarvis\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Jarvis"; Filename: "{app}\{#AppExe}"
Name: "{group}\Удалить Jarvis"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Jarvis"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Автозапуск (опционально)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "Jarvis"; ValueData: """{app}\{#AppExe}"""; \
  Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Запустить Jarvis сейчас"; \
  Flags: nowait postinstall skipifsilent
