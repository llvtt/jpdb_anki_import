#!/usr/bin/env python

import os
import shutil
import subprocess
import sys
import zipfile

addon_name = "jpdb_anki_import.ankiaddon"
source_dir = "jpdb_anki_import"
addon_path = os.path.abspath(addon_name)

vendor_dir = os.path.sep.join([source_dir, "vendor"])
if not os.path.exists(vendor_dir):
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-U",
            "-r",
            "requirements.txt",
            "-t",
            vendor_dir,
        ]
    )

# Create a zip file containing all the .py files in the source directory
shutil.rmtree(addon_path, ignore_errors=True)
with zipfile.ZipFile(addon_name, "w") as addon_zip:
    addon_zip.write("manifest.json")

    os.chdir(source_dir)

    for root, dirs, files in os.walk("."):
        root_dirs = os.path.normpath(root).split(os.path.sep)
        # Skip tests
        if "tests" in root_dirs:
            continue

        for file in files:
            # Skip compiled files
            if not file.endswith(".pyc"):
                file_path = os.path.join(root, file)
                addon_zip.write(file_path)

print(f"Add-on built successfully at {addon_path}")
