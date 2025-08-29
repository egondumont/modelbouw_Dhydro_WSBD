from datetime import datetime, timedelta
from pathlib import Path

import cftime
import numpy as np
import pandas as pd
from hydrolib.core.dflowfm.mdu.models import FMModel

CALENDAR = "gregorian"


def parse_cf_time(cf_time: str) -> tuple[str, datetime]:
    """Parse CF time to delta-unit and datetime

    Args:
        cf_time (str): datetime string, e.g. "minutes since 2016-06-01 00:00:00"

    Returns:
        (str, datetime): unit (e.g. minutes, seconds), ref_datetime
    """
    _cf_time = cftime.num2date(0, units=cf_time, calendar=CALENDAR)

    ref_datetime = datetime(
        _cf_time.year,
        _cf_time.month,
        _cf_time.day,
        _cf_time.hour,
        _cf_time.minute,
        _cf_time.second,
        _cf_time.microsecond,
    )
    time_unit = cf_time.split()[0]
    return time_unit, ref_datetime


def read_flow_boundaries(mdu_file: Path) -> pd.DataFrame:
    """Read all flow-boundaries from an existing FM-model

    Args:
        mdu_file (Path): Path to FM mdu-file

    Raises:
        ValueError: no flow_boundaries
        ValueError: flow boundaries with unequal lengths

    Returns:
        pd.DataFrame: dataframe with time (index) versus flow boundary timeseries per node_id (columns)
    """

    fm = FMModel(filepath=mdu_file)

    # get Q-boundaries
    bnds = [i for i in fm.external_forcing.extforcefilenew.boundary if i.quantity == "dischargebnd"]

    # check if boundary timeseries exists and are equal in length
    lengths = set([len(i.forcing.datablock) for i in bnds if i.forcing.function == "timeseries"])
    if len(lengths) == 0:
        raise ValueError("No timeseries exist")
    if len(lengths) != 1:
        raise ValueError(f"Only timeseries with equal lengths are supported. Now you have lengths {list(lengths)}")

    # parse time-index from first timeseries
    cf_time = next((i.unit for i in bnds[0].forcing.quantityunitpair if i.quantity == "time"))
    time_unit, ref_datetime = parse_cf_time(cf_time)

    index = pd.Index(
        [ref_datetime + timedelta(**{time_unit: i[0]}) for i in bnds[0].forcing.datablock], name="datetime"
    )

    # node-ids as columns
    columns = [i.nodeid for i in bnds]

    # parse all data
    data = np.array([np.array(i.forcing.datablock)[:, 1] for i in bnds]).transpose()

    return pd.DataFrame(data, index=index, columns=columns)
