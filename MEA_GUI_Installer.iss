#define MyAppName "MEA GUI"
#define MyAppVersion "1.0"
#define MyAppPublisher "Booka66"
#define MyAppExeName "MEA GUI.exe"
#define MyAppIconName "icon.ico"

[Setup]
AppId={{COM.BOOKA66.MEAGUI}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=MEA_GUI_Windows
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile={#MyAppIconName}
; Add these lines for self-deletion
DeleteAfterInstall=yes
SetupMutex={{35E1B185-47A5-4B93-9F53-C88CF75A8F0F}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "D:\Users\booka66\mea-gui\dist\main\main.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion
Source: "D:\Users\booka66\mea-gui\dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "main.exe"
Source: "D:\Users\booka66\mea-gui\fonts\HackNerdFontMono-Regular.ttf"; DestDir: "{fonts}"; FontInstall: "Hack Nerd Font Mono"; Flags: ignoreversion uninsneveruninstall
Source: "{#MyAppIconName}"; DestDir: "{app}"; Flags: ignoreversion
; Add this line for self-deletion
Source: "{srcexe}"; DestDir: "{app}"; Flags: external deleteafterinstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppIconName}"; Tasks: desktopicon

[Code]
// Add this function for self-deletion
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    Exec(ExpandConstant('{cmd}'), '/C ping 127.0.0.1 -n 2 -w 1000 > nul & Del "' + ExpandConstant('{srcexe}') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
