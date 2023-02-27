import os
import zipfile

addon_name = "jpdb_anki_import.ankiaddon"
source_dir = "jpdb_anki_import"

# Create a zip file containing all the .py files in the source directory
with zipfile.ZipFile(addon_name, "w") as addon_zip:
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                addon_zip.write(file_path, arcname)

print(f"Addon built successfully")
