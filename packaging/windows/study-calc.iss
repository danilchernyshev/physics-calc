; Inno Setup script for study-calc — builds a per-user Windows installer (#63, epic #60).
;
; It bundles the PyInstaller one-folder output (packaging/study-calc.spec, #62) and
; silently provisions the Microsoft Edge WebView2 runtime (PyWebView's Windows
; backend) when it is absent. Compile from the project root, injecting the
; single-sourced version:
;
;     iscc /DMyAppVersion=0.7.0 packaging\windows\study-calc.iss
;
; -> Output\study-calc-<version>-windows-setup.exe
;
; packaging/windows/build_installer.ps1 wires the whole flow (freeze -> smoke ->
; fetch bootstrapper -> compile).

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppName "Study Calculator"
#define MyAppExeName "study-calc.exe"
#define MyAppPublisher "Mark Chernyshev, Danil Chernyshev"
#define MyAppURL "https://github.com/danilchernyshev/study-calc"

[Setup]
AppId={{2F9B7C14-5E3A-4D8B-9A21-7C6E0F4B8A52}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Per-user install: no administrator rights required.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\study-calc
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=study-calc-{#MyAppVersion}-windows-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
; The frozen app is 64-bit only.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; study-calc.ico is generated from study_calc/web/frontend/icon.png by
; build_installer.ps1 (Inno Setup needs a real multi-resolution .ico here).
SetupIconFile=study-calc.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; The entire PyInstaller one-folder bundle (study-calc.exe + _internal\...).
Source: "..\..\dist\study-calc\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The WebView2 Evergreen Bootstrapper (~2 MB), fetched by build_installer.ps1.
; Lives in {tmp} only during setup and runs when WebView2 is missing.
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Provision WebView2 silently, only when it is not already present. The bundled
; app is --noconsole, so launching it opens no terminal window.
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; \
  StatusMsg: "Installing the Microsoft Edge WebView2 runtime…"; \
  Check: WebView2Missing; Flags: waituntilterminated
; Offer to launch the app at the end of setup.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; \
  Flags: nowait postinstall skipifsilent

[Code]
{ The WebView2 Evergreen Runtime registers a client under the EdgeUpdate keys,
  both machine-wide (HKLM, incl. the WOW6432Node view on 64-bit) and per-user
  (HKCU). If none carry a non-empty "pv" (product version), the runtime is
  absent and the bootstrapper must run. }
const
  WV2_CLIENT = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Present: Boolean;
var
  Pv: string;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WV2_CLIENT, 'pv', Pv) and (Pv <> '') and (Pv <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WV2_CLIENT, 'pv', Pv) and (Pv <> '') and (Pv <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WV2_CLIENT, 'pv', Pv) and (Pv <> '') and (Pv <> '0.0.0.0'));
end;

function WebView2Missing: Boolean;
begin
  Result := not WebView2Present;
end;
