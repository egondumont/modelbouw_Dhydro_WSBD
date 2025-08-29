from pathlib import Path

from hydrolib.core.dflowfm.mdu.models import FMModel


def get_his_file(mdu_file: Path) -> Path:
    mdu_file = Path(mdu_file)
    fm = FMModel(mdu_file)
    his_file = fm.output.hisfile.filepath
    if his_file is None:
        his_file = mdu_file.parent.joinpath(f"DFM_OUTPUT_{mdu_file.stem}", f"{mdu_file.stem}_his.nc")
    return his_file
