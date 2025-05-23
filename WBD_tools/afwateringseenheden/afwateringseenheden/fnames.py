# %%
import os
from pathlib import Path


def find_env_file():
    """Find env file in current directory or any of its parents"""
    cwd = Path(os.getcwd())
    env_file = next(
        (
            i.joinpath(".env")
            for i in [cwd] + list(cwd.parents)
            if i.joinpath(".env").exists()
        ),
        None,
    )
    if env_file is None:
        raise ValueError(
            f"Couldn't find .env in current directory nor it's parents: {cwd}"
        )
    return env_file


def load_env_to_dict(env_file: Path | None = None):
    """read env_file to dict"""

    # get env-file
    if env_file is None:
        env_file = find_env_file()

    # populate dict
    env_dict = {}
    with open(env_file) as f:
        for idx, line in enumerate(f):
            try:
                stripped_line = line.strip()
                if not stripped_line or stripped_line.startswith("#"):
                    continue
                if "=" in stripped_line:
                    key, value = stripped_line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    env_dict[key] = value
            except Exception:
                raise ValueError(f"Line {idx + 1} is not valid : {line}")
    return env_dict


def get_fnames(AFWATERINGSEENHEDEN_DIR: Path | None = None):
    """Get fnames relative to AFWATERINGSEENHEDEN_DIR"""

    # specify AFWATERINGSEENHEDEN_DIR
    if AFWATERINGSEENHEDEN_DIR is None:
        env = load_env_to_dict()
        if "AFWATERINGSEENHEDEN_DIR" not in env.keys():
            raise ValueError(
                f"AFWATERINGSEENHEDEN_DIR not specified in {find_env_file()}"
            )

        AFWATERINGSEENHEDEN_DIR = Path(env["AFWATERINGSEENHEDEN_DIR"])

    # populate fnames
    fnames = dict()

    # all we read
    DATA_DIR = AFWATERINGSEENHEDEN_DIR / "data"
    fnames["objecten"] = DATA_DIR / "objecten"
    fnames["a_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_A.shp")
    fnames["b_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_B.shp")

    fnames["ahn_dir"] = DATA_DIR.joinpath("hoogtekaart")
    fnames["clusters"] = DATA_DIR.joinpath(
        "clusters", "afwateringsgebieden_25m_15clusters_fixed.shp"
    )

    # all we write
    OUT_DIR = AFWATERINGSEENHEDEN_DIR / "out"
    fnames["waterlopen_verwerkt"] = OUT_DIR.joinpath("waterlopen_verwerkt.gpkg")
    fnames["afwateringseenheden"] = OUT_DIR.joinpath("afwateringseenheden.gpkg")
    fnames["process_dir"] = OUT_DIR.joinpath("clusters")

    return fnames
