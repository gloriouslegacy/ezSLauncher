; ezSLauncher Inno Setup Script
; Creates Windows installer with setup wizard

#define MyAppName "ezSLauncher"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ez"
#define MyAppURL "https://github.com/gloriouslegacy/ezSLauncher"
#define MyAppExeName "ezSLauncher.exe"

[Setup]
; App information
AppId={{E7A5C4B2-8D9F-4E3A-9B2C-1F6D8A4E5B3C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output
OutputDir=installer_output
OutputBaseFilename=ezSLauncher_Setup_{#MyAppVersion}

; Compression
Compression=lzma2
SolidCompression=yes

; Windows version requirement
MinVersion=10.0.19041

; Privileges
PrivilegesRequired=lowest
UsePreviousPrivileges=no

; UI settings
UsePreviousAppDir=no
DisableDirPage=yes
WizardStyle=modern
SetupIconFile=icon\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; License (if exists)
;LicenseFile=LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "dist\ezSLauncher\ezSLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

; Language file
Source: "dist\ezSLauncher\lang_ko.ini"; DestDir: "{app}"; Flags: ignoreversion

; Icon folder
Source: "dist\ezSLauncher\icon\*"; DestDir: "{app}\icon"; Flags: ignoreversion recursesubdirs createallsubdirs

; Internal dependencies
Source: "dist\ezSLauncher\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation (if exists)
Source: "README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion isreadme; Check: FileExists('README.md')
Source: "LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion; Check: FileExists('LICENSE')

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to run after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up config files on uninstall
Type: files; Name: "{app}\app_config.json"
Type: dirifempty; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks can be added here
  end;
end;
