# %%
import shutil
from functools import partial

import geopandas as gpd
import rioxarray as rxr
from geocube.api.core import make_geocube
from geocube.rasterize import rasterize_image

from wbd_tools.afwateringseenheden import (
    calculate_subcatchments,
    get_fnames,
    get_logger,
)

logger = get_logger()
fnames = get_fnames()
# %%
# globals

AHN_FILE = "dtm_2m.tif"
MAX_FILL_DEPTH = 5000
# CLUSTERS: list[int] = []

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# add ahn from fnames
# fnames["rasters_dir"]
logger.info("Bestanden ophalen")

fnames["ahn"] = next((fnames["rasters_dir"].glob(f"**/{AHN_FILE}")), None)
if not fnames["ahn"]:
    raise FileNotFoundError(f"{AHN_FILE} not found in any (sub directory of) {fnames['ahn']}")

dfs = dict()
# dfs["clusters"] = gpd.read_file(fnames["clusters"]).set_index("CLUSTER_ID", drop=False)
dfs["waterlopen"] = gpd.read_file(
    fnames["waterlopen_verwerkt"],
    layer="waterloopsegmenten",
    fid_as_index=True,
    engine="pyogrio",
)
dfs["waterlopen"].loc[:, "GridId"] = dfs["waterlopen"].index
dfs["waterlopen"].loc[:, "burn_depth"] = MAX_FILL_DEPTH * 4

dfs["b_waterlopen"] = gpd.read_file(
    "G:/WS_KenA/TG_hydrologie/wbd_tools/afwateringseenheden/data/waterlopen/Legger_waterlopen_B.shp"
)
dfs["b_waterlopen"].loc[:, "burn_depth"] = MAX_FILL_DEPTH * 2

# aanmaken directory
process_dir = fnames["process_dir"]
if process_dir.exists():
    shutil.rmtree(process_dir)
process_dir.mkdir(parents=True)

# ahn openen en omzetten naar int
logger.info("AHN inladen")
with rxr.open_rasterio(fnames["ahn"], mask_and_scale=True, chunks={"x": 2500, "y": 3250}) as ahn_raster_interp:
    ahn_raster_interp = ahn_raster_interp.rio.write_crs("EPSG:28992", inplace=True)
    ahn_raster = (ahn_raster_interp.chunk({"x": 2500, "y": 3250}) * 100).fillna(-9999).astype("int32")
    ahn_raster.rio.to_raster("temp_int32.tif")
    ahn_raster = rxr.open_rasterio("temp_int32.tif", chunks={"x": 2500, "y": 3250})

ahn_raster.close()
# Verrasteren van waterlopen als int32
logger.info("Verrasteren waterlopen")

# Belangrijk: je geeft rasterize_image mee met de juiste dtype
waterlopen = make_geocube(
    vector_data=dfs["waterlopen"],
    measurements=["GridId"],
    like=ahn_raster,
    fill=0,
    rasterize_function=partial(rasterize_image, all_touched=False, dtype="int32"),
)

# Zorg dat de waarden ook echt int32 zijn in de Dataset
for var in waterlopen.data_vars:
    waterlopen[var] = waterlopen[var].astype("int32")

# Opslaan met compressie en windowed schrijven (geheugenefficiënt)
fnames["waterlopen_raster"] = process_dir.joinpath("waterlopen_verrasterd_GridId.tif")
waterlopen.rio.to_raster(fnames["waterlopen_raster"], dtype="int32", windowed=True, compress="deflate")


# %% problemen met int 64
# Verraster waterlopen
logger.info("Verrasteren waterlopen")
waterlopen = make_geocube(
    dfs["waterlopen"],
    measurements=["GridId"],
    like=ahn_raster,
    fill=0,
    rasterize_function=partial(rasterize_image, all_touched=False, dtype="int32"),
)
fnames["waterlopen_raster"] = process_dir.joinpath("waterlopen_verrasterd_GridId.tif")
waterlopen.rio.to_raster(fnames["waterlopen_raster"], windowed=True)

logger.info("Waterlopen in ahn branden")
# Brand a-waterlopen in raster
burn_layer = make_geocube(
    dfs["waterlopen"],
    measurements=["burn_depth"],
    like=ahn_raster,
    fill=0,
    rasterize_function=partial(rasterize_image, all_touched=False),
)
ahn_raster = ahn_raster - burn_layer["burn_depth"].astype("int32")

# Brand b-waterlopen in raster
burn_layer = make_geocube(
    dfs["b_waterlopen"],
    measurements=["burn_depth"],
    like=ahn_raster,
    fill=0,
    rasterize_function=partial(rasterize_image, all_touched=False),
)
ahn_raster = ahn_raster - burn_layer["burn_depth"].astype("int32")

logger.info("AHN opschonen en opslaan")
ahn_raster_nan = ahn_raster.where(ahn_raster != -2147483648.0)
ahn_raster_nan.rio.write_nodata(-9999, encoded=True, inplace=True)
fnames["hoogteraster"] = process_dir.joinpath("hoogtekaart_interp.tif")
ahn_raster_nan.rio.to_raster(fnames["hoogteraster"])

# %%
# Maak raster met 1 waarde voor hele gebied (bijv 1)

peilvak = xr.full_like(ahn_raster_nan, 1, dtype=int)
fnames["peilvakken_raster"] = process_dir.joinpath("peilvakken.tif")
peilvak.rio.to_raster(fnames["peilvakken_raster"])

# Bereken afwateringseenheden over het hele gebied
fnames["afwateringseenheden"] = process_dir.joinpath("afwateringseenheden.gpkg")
logger.info("Bereken afwateringseenheden voor het hele gebied")
calculate_subcatchments(
    elevation_raster=fnames["hoogteraster"],
    water_segments_raster=fnames["waterlopen_raster"],
    areas_raster=fnames["peilvakken_raster"],
    subatchments_gpkg=fnames["afwateringseenheden"],
    max_fill_depth=MAX_FILL_DEPTH,
    crs=28992,
    report_maps=False,
)
