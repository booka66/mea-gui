import subprocess
import sys
import re
import aiohttp
import asyncio
import os

# GitHub API configuration
GITHUB_API_URL = "https://api.github.com"
REPO_OWNER = "booka66"
REPO_NAME = "mea-gui"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


def create_tag(tag):
    # Create and push a new tag
    subprocess.run(["git", "tag", tag])
    subprocess.run(["git", "push", "origin", tag])


def update_constants_file(tag):
    constants_file = "../Constants.py"
    with open(constants_file, "r") as f:
        content = f.read()
    updated_content = re.sub(
        r'VERSION = "v\d+\.\d+\.\d+"', f'VERSION = "{tag}"', content
    )
    with open(constants_file, "w") as f:
        f.write(updated_content)


async def get_or_create_release(session, tag):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    releases_url = (
        f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/releases/tags/{tag}"
    )
    async with session.get(releases_url, headers=headers) as response:
        if response.status == 200:
            print(f"Release for {tag} already exists. Updating it.")
            return await response.json()

    create_url = f"{GITHUB_API_URL}/repos/{REPO_OWNER}/{REPO_NAME}/releases"
    data = {
        "tag_name": tag,
        "name": f"Release {tag}",
        "body": f"Release notes for {tag}",
        "draft": False,
        "prerelease": False,
    }
    async with session.post(create_url, headers=headers, json=data) as response:
        if response.status == 201:
            print(f"Successfully created release for {tag}")
            return await response.json()
        else:
            print(f"Failed to create release. Status code: {response.status}")
            print(await response.text())
            return None


async def upload_or_update_asset(session, release_data, file_path):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    file_name = os.path.basename(file_path)
    assets = release_data.get("assets", [])
    existing_asset = next(
        (asset for asset in assets if asset["name"] == file_name), None
    )

    if existing_asset:
        delete_url = existing_asset["url"]
        async with session.delete(delete_url, headers=headers) as response:
            if response.status == 204:
                print(f"Deleted existing asset: {file_name}")
            else:
                print(f"Failed to delete existing asset: {file_name}")
                return

    upload_url = release_data["upload_url"].split("{")[0]
    headers["Content-Type"] = "application/octet-stream"
    params = {"name": file_name}

    file_size = os.path.getsize(file_path)

    print(f"Uploading {file_name} to the release...")

    async with aiohttp.ClientSession() as upload_session:
        with open(file_path, "rb") as file:
            headers["Content-Length"] = str(file_size)
            async with upload_session.post(
                upload_url, headers=headers, params=params, data=file
            ) as response:
                if response.status == 201:
                    print(f"Successfully uploaded {file_name} to the release.")
                else:
                    print(
                        f"Failed to upload {file_name}. Status code: {response.status}"
                    )
                    print(await response.text())


def increment_tag():
    # Increment the last digit of the tag
    with open("../Constants.py", "r") as f:
        content = f.read()
    match = re.search(r'VERSION = "v(\d+\.\d+\.)(\d+)"', content)
    if match:
        major_minor = match.group(1)
        last_digit = int(match.group(2))
        new_tag = f"v{major_minor}{last_digit + 1}"
        return new_tag
    return "Wah wah wahhhhh"


async def main(tag=None, no_package=False):
    # Try to compile the c++ extensions
    # try:
    #     setup_file = (
    #         "../extensions/setup.py"
    #         if sys.platform == "darwin"
    #         else "../extensions/win_setup.py"
    #     )
    #     subprocess.run(["python", setup_file, "build_ext", "--inplace"])
    # except Exception as e:
    #     print(f"Failed to compile c++ extensions: {e}")
    #     return
    if tag:
        # Validate tag format (e.g., v1.0.0)
        if tag == "next":
            tag = increment_tag()
        if not re.match(r"^v\d+\.\d+\.\d+$", tag):
            print("Invalid tag format. Please use vX.Y.Z (e.g., v1.0.0)")
            return
        create_tag(tag)
        update_constants_file(tag)

    print(f"Creating {'package' if not no_package else 'application'}...")

    if sys.platform == "darwin":
        pyinstaller_command = """sudo pyinstaller --noconfirm --onedir --argv-emulation --windowed ../../main.py --icon=../../../resources/icon.ico --add-data "../../helpers/mat/SzDetectCat.m:." --add-data "../../helpers/mat/save_channel_to_mat.m:." --add-data "../../helpers/mat/getChs.m:." --add-data "../../helpers/mat/get_cat_envelop.m:." --additional-hooks-dir "../../../hooks/" --add-data "../../helpers/mat/*.m:."
        """
        package_commands = [
            "rm -rf package_root/Applications/MEA\\ GUI.app",
            "cp -R dist/main.app package_root/Applications/MEA\\ GUI.app ",
            "cp ../../../resources/fonts/HackNerdFontMono-Regular.ttf package_root/Library/Fonts ",
            "pkgbuild --root package_root --identifier com.booka66.meagui --install-location / --overwrite-files MEA_GUI_MacOS.pkg",
        ]
        package_file = "MEA_GUI_MacOS.pkg"
    else:
        pyinstaller_command = """pyinstaller --collect-submodules=sz_se_detect --noconfirm  --onedir --windowed ../../main.py --icon=../../../resources/icon.ico --add-data "../../helpers/mat/SzDetectCat.m:." --add-data "../../helpers/mat/save_channel_to_mat.m:." --add-data "../../helpers/mat/getChs.m:." --add-data "../../helpers/mat/get_cat_envelop.m:." --additional-hooks-dir "../../../hooks/" --add-data "../../helpers/mat/*.m:."
            """
        package_commands = [
            r'"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Q MEA_GUI_Installer.iss'
        ]
        package_file = "Output\\MEA_GUI_Windows.exe"

    pyinstaller_process = subprocess.Popen(pyinstaller_command, shell=True)
    pyinstaller_process.wait()

    if no_package:
        print("Application created successfully! 🎉🎉🎉")
        return

    for command in package_commands:
        package_process = subprocess.Popen(command, shell=True)
        package_process.wait()

    print("Package created successfully! 🎉🎉🎉")

    if tag:
        async with aiohttp.ClientSession() as session:
            release_data = await get_or_create_release(session, tag)
            if release_data:
                await upload_or_update_asset(session, release_data, package_file)


if __name__ == "__main__":
    args = sys.argv[1:]
    tag = None
    no_package = False
    for arg in args:
        if arg.startswith("--tag="):
            tag = arg.split("=")[1]
        elif arg == "--no-package":
            no_package = True
    asyncio.run(main(tag, no_package))
