; Inno Setup Script for 会帮手 (MeetTimer)
; 基于原有版本更新

[Setup]
AppId={{MEET-TIMER-20260616}}
AppName=会帮手
AppVersion=1.22
AppVerName=会帮手 (MeetTimer) v1.22
AppPublisher=GAC数字化部综合管控
DefaultDirName={localappdata}\MeetTimer
DefaultGroupName=会帮手
AllowNoIcons=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
OutputDir=output
OutputBaseFilename=MeetTimer_Setup_v1.22
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ShowLanguageDialog=no
DisableDirPage=no
DisableProgramGroupPage=no
DisableWelcomePage=no
DisableReadyPage=no
UninstallDisplayIcon={app}\MeetTimer.exe
UninstallDisplayName=会帮手 (MeetTimer)

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Files]
Source: "dist\MeetTimer\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{group}\会帮手"; Filename: "{app}\MeetTimer.exe"; WorkingDir: "{app}"
Name: "{group}\卸载 会帮手"; Filename: "{uninstallexe}"
Name: "{commondesktop}\会帮手"; Filename: "{app}\MeetTimer.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Run]
Filename: "{app}\MeetTimer.exe"; Description: "启动 会帮手"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\Sound"
Type: filesandordirs; Name: "{app}\resources"
Type: filesandordirs; Name: "{app}\_internal"