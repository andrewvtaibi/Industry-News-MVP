; industry_news.iss
; Inno Setup 6 script for Industry News — Company Reports and Information Engine
;
; Prerequisites:
;   1. Install Inno Setup 6 from https://jrsoftware.org/isinfo.php
;   2. Build the PyInstaller bundle first:
;        pip install pyinstaller
;        pyinstaller industry_news.spec
;      This produces:  dist\IndustryNews\
;   3. (Optional) Place a 256x256 icon at installer\icon.ico
;   4. Open this file in the Inno Setup IDE and click Build,
;      or run from the command line:
;        iscc installer\industry_news.iss
;      To pass a version number from CI:
;        iscc /DAppVersion=1.0.1 installer\industry_news.iss
;
; Output:
;   installer\Output\IndustryNews-Setup.exe
;   (Upload this single file to your GitHub Release)

; AppVersion can be overridden from the command line with /DAppVersion=x.x.x
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

#define AppName      "Industry News"
#define AppPublisher "Your Name or Organization"
#define AppURL       "https://github.com/andrewvtaibi/Industry-News-MVP"
#define AppExeName   "IndustryNews.exe"
#define SourceDir    "..\dist\IndustryNews"

[Setup]
; Keep this AppId constant across versions so upgrades work correctly.
; Do not change it once published.
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=Output
OutputBaseFilename=IndustryNews-Setup
; Uncomment once you have an icon:
; SetupIconFile=icon.ico
WizardStyle=modern
; lowest = installs to user's AppData without requiring admin rights,
; but prompts the user if they want system-wide install instead.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Desktop shortcut — checked ON by default so non-technical users
; get an icon without having to find it themselves.
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy everything PyInstaller built into the install directory.
Source: "{#SourceDir}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu entry
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Comment: "Launch Industry News"

; Desktop shortcut (created if the user left the checkbox ticked)
Name: "{autodesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  Comment: "Launch Industry News"; \
  Tasks: desktopicon

; Start Menu uninstall link
Name: "{group}\Uninstall {#AppName}"; \
  Filename: "{uninstallexe}"

[Run]
; Offer to open the app right after install finishes
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent
