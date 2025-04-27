# %%
import pyflwdir
from pathlib import Path
import rasterio
import numpy as np
import time
import geopandas as gpd

DTM2CAT_DIR = Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\02.DTM2CAT\dtm2cat")
DATA_DIR = DTM2CAT_DIR / "data"
OUT_DIR = DTM2CAT_DIR / "out"


fnames = dict()
fnames["waterlopen_verwerkt"] = OUT_DIR.joinpath("waterlopen_verwerkt.gpkg")
fnames["ahn_05m"] = DATA_DIR.joinpath(
    r"hoogtekaart", "5m_AHN3_NL", "AHN_25m_BD_filled.tif"
)
fnames["b_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_B.shp")
fnames["clusters"] = DATA_DIR.joinpath(
    "clusters", "afwateringsgebieden_25m_15clusters_fixed.shp"
)

fnames["process_dir"] = OUT_DIR.joinpath("clusters")

elevation_asc = fnames["process_dir"].joinpath("13", "hoogtekaart_interp.asc")
with rasterio.open(elevation_asc, "r") as src:
    elevtn = src.read(1)
    nodata = src.nodata
    transform = src.transform
    crs = src.crs
    extent = np.array(src.bounds)[[0, 2, 1, 3]]
    latlon = src.crs.is_geographic
    prof = src.profile

t0 = time.time()
flw = pyflwdir.from_dem(
    data=elevtn,
    nodata=src.nodata,
    transform=transform,
    latlon=latlon,
    outlets="min",
)

d8_data = flw.to_array(ftype="d8")
prof.update(dtype=d8_data.dtype, nodata=247, driver="GTiff")
with rasterio.open(
    fnames["process_dir"].joinpath("13", "flwdir.tif"), "w", **prof
) as src:
    src.write(d8_data, 1)

feats = flw.streams(min_sto=4)
gdf = gpd.GeoDataFrame.from_features(feats, crs=crs)
gdf.to_file(fnames["process_dir"].joinpath("13", "streams.gpkg"))

print(f"flwdir in {time.time() - t0}")
