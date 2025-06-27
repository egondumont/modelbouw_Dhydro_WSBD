# %%
import os
from datetime import datetime
from pathlib import Path

from wbd_tools.logger import get_logger

DATE_TIME_PATTERN = "%Y%m%d"
logger = get_logger()


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


def get_fnames(
    AFWATERINGSEENHEDEN_DIR: Path | None = None,
    MODELLEN_DIR: Path | None = None,
    RUN_DIMR_BAT: Path = Path(
        r"C:\Program Files\Deltares\D-HYDRO Suite 2024.03 1D2D\plugins\DeltaShell.Dimr\kernels\x64\bin\run_dimr.bat"
    ),
    RASTERS_DIR: Path | None = None,
) -> dict[Path]:
    """Get all fnames from"""
    kwargs = locals().copy()

    # init fnames from env
    env = load_env_to_dict()
    fnames = {k.lower(): Path(v) for k, v in env.items()}

    for variable, value in kwargs.items():
        print(variable, value)
        # if not specified we read it from .env
        if value is None:
            if variable.lower() not in fnames.keys():
                raise ValueError(f"{variable.upper()} not specified as input nor in {find_env_file()}")
        else:
            fnames[variable.lower()] = Path(value)

    # afwateringseenheden: all we read
    DATA_DIR = fnames["afwateringseenheden_dir"] / "data"
    fnames["objecten"] = DATA_DIR / "objecten"
    fnames["a_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_A.shp")
    fnames["b_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_B.shp")

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

    # rasters: all we read
    fnames["ahn_dir"] = fnames["rasters_dir"] / "ahn"

    return dict(sorted(fnames.items()))


# %%
def _get_model_dir(model_name: str, create=False) -> Path:
    """Get model directory

    Args:
        model_name (str): model name
        create (bool, optional): if true the dir can be created. If false it should exist. Defaults to False.

    Returns:
        Path: Path to model_dir
    """
    fnames = get_fnames()
    model_dir = fnames["modellen_output"] / model_name
    if not model_dir.exists():
        if create:
            model_dir.mkdir(parents=True)
        else:
            raise FileNotFoundError(f"Sub-folder {model_name} in directory {fnames['modellen_output']} does not exist")

    return model_dir


def _parse_date_dir(date: datetime | str) -> str:
    if isinstance(date, datetime):
        date = date.strftime(DATE_TIME_PATTERN)
    return date


def create_output_dir(model_name: str, date: datetime | str | None = None) -> Path:
    """Create an output dir for today or a specific date

    Args:
        model_name (str): model-name to create a sub-dir for
        date (datetime | str | None, optional): date to create a subdir for. Defaults to None.

    Returns:
        Path: Path of output_dir
    """
    model_dir = _get_model_dir(model_name, create=True)

    if date is None:
        date = datetime.today()

    date = _parse_date_dir(date)
    output_dir = model_dir / date
    output_dir.mkdir(exist_ok=True, parents=True)

    logger.info(f"output_dir: {output_dir}")
    return output_dir


def get_output_dir(model_name: str, date: datetime | str | None = None) -> Path:
    """Get (the latest) output dir.

    Args:
        model_name (str): model-name to create a sub-dir for
        date (datetime | str | None, optional): date to get the output dir for. If not specified the latest is returned Defaults to None.

    Returns:
        Path: Path of output_dir
    """
    model_dir = _get_model_dir(model_name)

    # get folder from date
    if date is not None:
        date = _parse_date_dir(date)
        output_dir = model_dir / date
        if not output_dir.exists():
            raise FileNotFoundError(f"Sub-folder {date} in directory {model_dir} does not exist")

    # return latest folder
    else:
        sub_dirs = []
        for item in model_dir.iterdir():
            if item.is_dir():
                try:
                    # Try to parse the directory name as a date
                    datetime.strptime(item.name, DATE_TIME_PATTERN)
                    sub_dirs.append(item)
                except ValueError:
                    # Skip names that don't match the pattern
                    continue
        if len(sub_dirs) == 0:
            raise FileNotFoundError(
                f"Sub-folder {model_name} does not contain sub-folders with pattern {DATE_TIME_PATTERN}"
            )
        output_dir = sorted(sub_dirs)[-1]

        logger.info(f"output_dir: {output_dir}")

    return output_dir
