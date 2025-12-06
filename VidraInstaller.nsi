!define APP_NAME "Vidra Downloader"
!define APP_EXE "Vidra_downloader.exe"
!define UNINSTALLER_NAME "Uninstall.exe"

OutFile "Vidra_Installer.exe"
InstallDir "$PROGRAMFILES\\${APP_NAME}"
RequestExecutionLevel admin

!define SHORTCUT_DESKTOP "$DESKTOP\\${APP_NAME}.lnk"
!define SHORTCUT_STARTMENU "$SMPROGRAMS\\${APP_NAME}"

# UI pages
Page components       ; ✅ Shows optional shortcut checkboxes
Page directory
Page instfiles
UninstPage uninstConfirm
UninstPage instfiles

# --- Always-installed hidden main files ---
Section "" SEC_MAIN
    SectionIn RO      ; Hidden, required
    SetOutPath "$INSTDIR"
    File /r "dist\\Vidra_downloader\\*.*"

    WriteUninstaller "$INSTDIR\\${UNINSTALLER_NAME}"

    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$INSTDIR\\${UNINSTALLER_NAME}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "InstallLocation" "$INSTDIR"
SectionEnd

# --- Optional desktop shortcut ---
Section /o "Create Desktop Shortcut" SEC_DESKTOP
    CreateShortcut "${SHORTCUT_DESKTOP}" "$INSTDIR\\${APP_EXE}"
SectionEnd

# --- Optional start menu shortcut ---
Section /o "Create Start Menu Shortcut" SEC_STARTMENU
    CreateDirectory "${SHORTCUT_STARTMENU}"
    CreateShortcut "${SHORTCUT_STARTMENU}\\${APP_NAME}.lnk" "$INSTDIR\\${APP_EXE}"
    CreateShortcut "${SHORTCUT_STARTMENU}\\Uninstall.lnk" "$INSTDIR\\${UNINSTALLER_NAME}"
SectionEnd

# --- Uninstaller cleanup ---
Section "Uninstall"
    Delete "${SHORTCUT_DESKTOP}"
    Delete "${SHORTCUT_STARTMENU}\\${APP_NAME}.lnk"
    Delete "${SHORTCUT_STARTMENU}\\Uninstall.lnk"
    RMDir "${SHORTCUT_STARTMENU}"

    RMDir /r "$INSTDIR"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"
SectionEnd
