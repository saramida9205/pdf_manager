[Setup]
AppName=PDF Manager
AppVersion=2.0
DefaultDirName={autopf}\PDF Manager
DefaultGroupName=PDF Manager
OutputDir=dist
OutputBaseFilename=PDF_Manager_Setup_v2.0
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PDF_Manager_Fast.exe

[Files]
Source: "dist\PDF_Manager_Fast\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PDF Manager"; Filename: "{app}\PDF_Manager_Fast.exe"
Name: "{autodesktop}\PDF Manager"; Filename: "{app}\PDF_Manager_Fast.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
