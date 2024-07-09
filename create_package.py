import subprocess
import sys


def main():
    if sys.platform == "darwin":
        command = """
            sudo pyinstaller --noconfirm --onefile --windowed main.py --icon=icon.icns --add-data "SzDetectCat.m:." --add-data "save_channel_to_mat.m:." --add-data "getChs.m:." --add-data "get_cat_envelop.m:." --additional-hooks-dir "hooks" --add-data "*.m:."
        """
    else:
        command = """
            pyinstaller --noconfirm --onefile --windowed main.py --icon=icon.ico --add-data "SzDetectCat.m:." --add-data "save_channel_to_mat.m:." --add-data "getChs.m:." --add-data "get_cat_envelop.m:." --additional-hooks-dir "hooks" --add-data "*.m:."
        """

    process = subprocess.Popen(command, shell=True)
    process.wait()

    print("Package created successfully! 🎉🎉🎉")


if __name__ == "__main__":
    main()
