# %%

import rasterio
from rasterio.enums import Resampling
from rasterio.fill import fillnodata

from wbd_tools.fnames import get_fnames

cell_size = 2

ahn_dir = get_fnames()["ahn_dir"]
# %%
with rasterio.open(ahn_dir.joinpath("dtm_05m", "dtm_05m.vrt")) as src:
    scale_factor = cell_size / abs(src.res[0])
    new_height = int(src.height / scale_factor)
    new_width = int(src.width / scale_factor)
    resampled_data = src.read(out_shape=(src.count, new_height, new_width), resampling=Resampling.bilinear)
    resampled_transform = src.transform * src.transform.scale((src.width / new_width), (src.height / new_height))

    profile = src.profile.copy()
    profile.update(
        {
            "height": new_height,
            "width": new_width,
            "transform": resampled_transform,
            "driver": "GTiff",
        }
    )
    scales = src.scales

    fillnodata(
        resampled_data,
        mask=resampled_data != profile["nodata"],
        max_search_distance=250,
    )

    with rasterio.open(ahn_dir.joinpath("dtm_2m.tif"), "w+", **profile) as dst:
        dst.write(resampled_data)
        dst.scales = scales
