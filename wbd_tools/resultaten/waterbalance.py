from pathlib import Path

import pandas as pd
import xarray as xr

from wbd_tools.resultaten.common import get_his_file


def water_balance(mdu_file: Path, remove_no_flow: bool = False) -> pd.DataFrame:
    """Get the water-balance of a FM model

    Args:
        mdu_file (Path): mdu_file of fm-model
        remove_no_flow (bool, optional): remove all series with only 0-values. Defaults to False.

    Returns:
        pd.DataFrame: DataFrame with time (index) versus station-ids (columns)
    """
    his_file = get_his_file(mdu_file)
    with xr.open_dataset(his_file) as ds:
        variables = [v for v in ds.data_vars if v.startswith("water_balance_")]

    df = ds[variables].to_dataframe()

    if remove_no_flow:
        df = df.loc[:, (df != 0).any(axis=0)]

    return df
