; Inno Setup Script for 会帮手
; Generated for Trae AI

[Setup]
AppId={{HUI-BANG-SHOU-20260615}
AppName=会帮手
AppVersion=1.0.0
AppPublisher=GAC-JD
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/
DefaultDirName={pf}\会帮手
DefaultGroupName=会帮手
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=output
OutputBaseFilename=HuiBangShou_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ShowLanguageDialog=no
DisableDirPage=no
DisableProgramGroupPage=no
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "dist\会帮手\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\会帮手"; Filename: "{app}\会帮手.exe"; WorkingDir: "{app}"
Name: "{group}\卸载 会帮手"; Filename: "{uninstallexe}"
Name: "{commondesktop}\会帮手"; Filename: "{app}\会帮手.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Run]
Filename: "{app}\会帮手.exe"; Description: "启动 会帮手"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"