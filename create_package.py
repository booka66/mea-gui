import subprocess
import sys


def main():
    pyinstaller_command = """ pyinstaller --noconfirm --onefile --windowed main.py --icon=icon.ico --add-data "SzDetectCat.m:." --add-data "save_channel_to_mat.m:." --add-data "getChs.m:." --add-data "get_cat_envelop.m:." --additional-hooks-dir "hooks" --add-data "*.m:."
        """
    if sys.platform == "darwin":
        pyinstaller_command = "sudo " + pyinstaller_command

        package_commands = [
            "rm -rf package_root/Applications/MEA\ GUI.app",
            "cp -R dist/main.app package_root/Applications/MEA\ GUI.app ",
            "cp fonts/HackNerdFontMono-Regular.ttf package_root/Library/Fonts ",
            "pkgbuild --root package_root --identifier com.booka66.meagui MEA_GUI_MacOS.pkg",
        ]
    else:
        package_commands = [
            r'"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Q MEA_GUI_Installer.iss'
        ]

    pyinstaller_process = subprocess.Popen(pyinstaller_command, shell=True)
    pyinstaller_process.wait()

    for command in package_commands:
        package_process = subprocess.Popen(command, shell=True)
        package_process.wait()

    print("Package created successfully! 🎉🎉🎉")


if __name__ == "__main__":
    main()
