# %%
"""Voor het schonen van rasters t.b.v. DHyDAMO"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


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


# %%
def generate_constant_time_rasters(
    raster_template_file: Path,
    dst_folder: Path,
    raster_prefix: str,
    start_time: datetime,
    end_time: datetime,
    delta_time: timedelta,
    constant_value: float,
    cell_size: int | None = None,
):
    dst_folder = Path(dst_folder)

    # make dst_folder
    if dst_folder.exists():
        shutil.rmtree(dst_folder)
    dst_folder.mkdir(parents=True, exist_ok=True)

    # Open the source raster
    with rasterio.open(raster_template_file) as src:
        bounds = src.bounds
        crs = src.crs

    # Define the new resolution
    if cell_size is None:
        cell_size = abs(src.res[0])

    # Calculate the number of rows and columns
    width = int((bounds.right - bounds.left) / cell_size)
    height = int((bounds.top - bounds.bottom) / cell_size)

    # Define transform (origin at top-left)
    transform = from_origin(bounds.left, bounds.top, cell_size, cell_size)

    # Create an array filled with zeros (or any data you want)
    data = np.zeros((height, width), dtype=np.float32) * constant_value

    timesteps = int((end_time - start_time) / delta_time + 0.5)
    for time_step in range(timesteps):
        time_stamp = start_time + delta_time * time_step

        raster_out_file = dst_folder / f"{raster_prefix}_{time_stamp.strftime('%Y%m%d%H%M')}.tif"
        # Write the new raster
        with rasterio.open(
            raster_out_file,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="float32",
            crs=crs,
            transform=transform,
        ) as dst:
            dst.write(data, 1)
