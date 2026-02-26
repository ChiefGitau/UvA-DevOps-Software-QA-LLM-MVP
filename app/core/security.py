from pathlib import Path
import zipfile, tarfile

def safe_extract_zip(zip_path: Path, dest: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        for m in z.infolist():
            p = (dest / m.filename).resolve()
            if not str(p).startswith(str(dest.resolve())):
                raise ValueError("Unsafe zip: path traversal detected")
        z.extractall(dest)

def safe_extract_tar(tar_path: Path, dest: Path) -> None:
    with tarfile.open(tar_path) as t:
        for m in t.getmembers():
            p = (dest / m.name).resolve()
            if not str(p).startswith(str(dest.resolve())):
                raise ValueError("Unsafe tar: path traversal detected")
        t.extractall(dest)
