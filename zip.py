import zipfile
import os

def zip_files(zip_filename):
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk('.'):
            for file in files:
                if file != zip_filename and file != 'zip.py':
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), '.'))

def ensure_zip_extension(filename):
    if not filename.endswith('.zip'):
        filename += '.zip'
    return filename

if __name__ == "__main__":
    zip_name = input("Введіть назву zip-файлу: ")
    zip_name = ensure_zip_extension(zip_name)
    zip_files(zip_name)

