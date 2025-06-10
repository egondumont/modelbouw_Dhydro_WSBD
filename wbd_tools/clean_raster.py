# %%
"""Voor het schonen van rasters t.b.v. DHyDAMO"""

from pathlib import Path

import numpy as np
import rasterio


def opschonen_raster(
    raster_file,
    raster_out_file: Path | None = None,
    min_val: float | int | None = None,
    max_val: float | int | None = None,
):
    # read data of raster_file
    with rasterio.open(raster_file) as src:
        data = src.read(1)
        profile = src.profile
        scales = src.scales

    # convert to signed dtype if unsigned
    if np.issubdtype(data.dtype, np.unsignedinteger):
        bits = data.dtype.itemsize * 8
        dtype = np.dtype(f"int{bits}")
        data = data.astype(dtype)
        profile["dtype"] = dtype

    # set nodata to -999
    nodata = profile["nodata"]
    if nodata is not None:
        if nodata != -999:
            data = np.where(data == nodata, -999, data)
    profile["nodata"] = -999

    # set dtype to float if scales
    if scales[0] != 0:
        data = np.where(data != -999, data.astype(float) * scales, -999)
        profile["dtype"] = data.dtype

    # clip data to min_value and max_value
    if min_val is not None:
        data = np.where(data < min_val, profile["nodata"], data)

    if max_val is not None:
        data = np.where(data > max_val, profile["nodata"], data)

    if raster_out_file is None:
        raster_out_file = raster_file

    with rasterio.open(raster_out_file, "w+", **profile) as dst:
        dst.write(data, 1)
