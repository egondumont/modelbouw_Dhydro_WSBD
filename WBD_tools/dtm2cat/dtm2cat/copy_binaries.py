import shutil
from pathlib import Path


def copy_binaries(path):
    path = Path(path)
    path.mkdir(exist_ok=True, parents=True)

    bin_dir = Path(__file__).parent / "bin"
    for file_name in bin_dir.glob("*.*"):
        shutil.copy(file_name, path)
