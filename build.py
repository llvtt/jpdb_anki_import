import os
import shutil
import zipfile

addon_name = 'jpdb_anki_import.ankiaddon'
source_dir = 'jpdb_anki_import'

addon_path = os.path.abspath(addon_name);

shutil.rmtree(addon_path, ignore_errors=True)

# Create a zip file containing all the .py files in the source directory
with zipfile.ZipFile(addon_name, 'w') as addon_zip:
    addon_zip.write('manifest.json')
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                # ensure file is added to root of zip file
                arc_file_name = os.path.basename(file_path)
                addon_zip.write(file_path, arc_file_name)

print(f'Add-on built successfully at {addon_path}')
