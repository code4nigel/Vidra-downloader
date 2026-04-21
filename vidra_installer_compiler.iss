[Setup]
AppName=Vidra Downloader Pro
AppVersion=2.0
DefaultDirName={autopf}\Vidra Downloader
DefaultGroupName=Vidra Downloader
OutputDir=release
OutputBaseFilename=Vidra_Installer
Compression=lzma2/ultra
SolidCompression=yes
DisableProgramGroupPage=yes

[Files]
Source: "dist\Vidra_Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Vidra Downloader"; Filename: "{app}\Vidra_Downloader.exe"
Name: "{commondesktop}\Vidra Downloader"; Filename: "{app}\Vidra_Downloader.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
