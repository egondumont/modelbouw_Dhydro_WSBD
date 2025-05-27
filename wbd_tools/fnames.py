# %%
import os
from pathlib import Path


def find_env_file():
    """Find env file in current directory or any of its parents"""
    cwd = Path(os.getcwd())
    env_file = next(
        (i.joinpath(".env") for i in [cwd] + list(cwd.parents) if i.joinpath(".env").exists()),
        None,
    )
    if env_file is None:
        raise ValueError(f"Couldn't find .env in current directory nor it's parents: {cwd}")
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


# %%
def get_fnames(AFWATERINGSEENHEDEN_DIR: Path | None = None, MODELLEN_DIR: Path | None = None) -> dict[Path]:
    """Get all fnames from"""
    fnames = {k.lower(): v for k, v in locals().items()}

    env = None
    for variable, value in fnames.items():
        # if not specified we read it from .env
        if value is None:
            # load env
            if env is None:
                env = load_env_to_dict()
            # raise ValueError if local is not in env
            if variable.upper() not in env.keys():
                raise ValueError(f"{variable.upper()} not specified as input nor in {find_env_file()}")
            fnames[variable] = Path(env[variable.upper()])
        else:
            fnames[variable] = Path(value)

    # afwateringseenheden: all we read
    DATA_DIR = fnames["afwateringseenheden_dir"] / "data"
    fnames["objecten"] = DATA_DIR / "objecten"
    fnames["a_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_A.shp")
    fnames["b_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_B.shp")

    fnames["ahn_dir"] = DATA_DIR.joinpath("hoogtekaart")
    fnames["clusters"] = DATA_DIR.joinpath("clusters", "afwateringsgebieden_25m_15clusters_fixed.shp")

    # afwateringseenheden: all we write
    OUT_DIR = fnames["afwateringseenheden_dir"] / "out"
    fnames["waterlopen_verwerkt"] = OUT_DIR.joinpath("waterlopen_verwerkt.gpkg")
    fnames["afwateringseenheden"] = OUT_DIR.joinpath("afwateringseenheden.gpkg")
    fnames["process_dir"] = OUT_DIR.joinpath("clusters")

    # modellen: all we read
    DATA_DIR = fnames["modellen_dir"] / "data"
    fnames["damo_gdb"] = DATA_DIR.joinpath("acceptatiedatabase.gdb")
    fnames["modelgebieden_gpkg"] = DATA_DIR.joinpath("modelgebieden.gpkg")

    # modellen: all we write
    fnames["modellen_output"] = fnames["modellen_dir"] / "output"

    return fnames


# %%
