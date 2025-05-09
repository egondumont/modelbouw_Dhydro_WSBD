# %%
import shutil
import pandas as pd
import geopandas as gpd
import rioxarray as rxr
from geocube.api.core import make_geocube
from functools import partial
from geocube.rasterize import rasterize_image
from pathlib import Path
from afwateringseenheden import (
    get_logger,
    calculate_subcatchments,
    get_fnames,
)


logger = get_logger()

# %%
# globals

AHN_FILE = "dtm_2m_filled.tif"
MAX_FILL_DEPTH = 5000
CLUSTERS: list[int] = []

# %%

# processen clusters
# geef hier specifieke clusters op als je niet het hele waterschap wilt draaien
fnames = get_fnames()

# add ahn from fnames
fnames["ahn_dir"]
fnames["ahn"] = next((fnames["ahn_dir"].glob(f"**/{AHN_FILE}")), None)
if not fnames["ahn"]:
    raise FileNotFoundError(
        f"{AHN_FILE} not found in any (sub directory of) {fnames['ahn']}"
    )

dfs = dict()
dfs["clusters"] = gpd.read_file(fnames["clusters"]).set_index("CLUSTER_ID", drop=False)
dfs["waterlopen"] = gpd.read_file(
    fnames["waterlopen_verwerkt"],
    layer="waterloopsegmenten",
    fid_as_index=True,
    engine="pyogrio",
)
dfs["waterlopen"].loc[:, "GridId"] = dfs["waterlopen"].index
dfs["waterlopen"].loc[:, "burn_depth"] = MAX_FILL_DEPTH * 4

dfs["b_waterlopen"] = gpd.read_file(
    fnames["waterlopen_verwerkt"],
    layer="b_waterlopen",
    engine="pyogrio",
)
dfs["b_waterlopen"].loc[:, "burn_depth"] = MAX_FILL_DEPTH * 2

clusters = dfs["clusters"].index
# limiteren clusters tot CLUSTERS
if CLUSTERS:
    clusters = [i for i in clusters if i in CLUSTERS]


for cluster in clusters:
    logger.info(f"starten met cluster {cluster}")

    # select_clusters
    cluster_select_df = dfs["clusters"].loc[[cluster]]

    # aanmaken directory
    cluster_dir = fnames["process_dir"].joinpath(f"{cluster}")
    if cluster_dir.exists():
        shutil.rmtree(cluster_dir)

    # clip hoogteraster met clustergrens
    logger.info(f"aanmaken hoogteraster")
    with rxr.open_rasterio(
        fnames["ahn"], mask_and_scale=True, chunks=True
    ) as ahn_raster_interp:
        ahn_raster_interp = ahn_raster_interp.rio.write_crs("EPSG:28992", inplace=True)
        ahn_clipped = ahn_raster_interp.rio.clip(
            cluster_select_df.geometry,
            cluster_select_df.crs,
            all_touched=True,
            drop=True,
            invert=False,
        )

        # reken hoogtedata om naar integers
        ahn_raster = ahn_clipped * 100
        ahn_raster = ahn_raster.astype(int)

    # clip waterlopen op basis van clustergrens
    logger.info(f"aanmaken waterlopen-raster")
    waterlopen_clipped_gdf = gpd.clip(
        dfs["waterlopen"], dfs["clusters"].at[cluster, "geometry"]
    )

    # creëer mask om ID van waterlopen in template raster te branden (verrasteren van waterlopen)
    waterlopen = make_geocube(
        waterlopen_clipped_gdf,
        measurements=["GridId"],
        like=ahn_raster,
        fill=0,
        rasterize_function=partial(rasterize_image, all_touched=False),
    )

    fnames["waterlopen_raster"] = cluster_dir.joinpath(
        "waterlopen_verrasterd_GridId.tif"
    )
    waterlopen.rio.to_raster(fnames["waterlopen_raster"])

    # branden van a-waterlopen in hoogtekaart
    burn_layer = make_geocube(
        waterlopen_clipped_gdf,
        measurements=["burn_depth"],
        like=ahn_raster,
        fill=0,
        rasterize_function=partial(rasterize_image, all_touched=False),
    )

    ahn_raster = ahn_raster - burn_layer["burn_depth"].astype(int)

    # branden van b-waterlopen in hoogtekaart
    b_waterlopen_clipped_gdf = gpd.clip(
        dfs["b_waterlopen"], dfs["clusters"].at[cluster, "geometry"]
    )

    burn_layer = make_geocube(
        b_waterlopen_clipped_gdf,
        measurements=["burn_depth"],
        like=ahn_raster,
        fill=0,
        rasterize_function=partial(rasterize_image, all_touched=False),
    )

    ahn_raster = ahn_raster - burn_layer["burn_depth"].astype(int)
    ahn_raster_nan = ahn_raster.where(ahn_raster != -2147483648.0)
    ahn_raster_nan.rio.write_nodata(-9999, encoded=True, inplace=True)
    fnames["hoogteraster"] = cluster_dir.joinpath("hoogtekaart_interp.tif")
    ahn_raster_nan.rio.to_raster(fnames["hoogteraster"])

    # maak raster met peilvakken met waarde CLUSTER_ID en schrijf weg zodat clustergrenzen worden gebruikt als peilgebiedsgrens
    logger.info(f"aanmaken peilvak-raster")
    peilvak = make_geocube(
        cluster_select_df,
        measurements=["CLUSTER_ID"],
        like=ahn_raster_nan,
        fill=-9999.0,
        rasterize_function=partial(rasterize_image, all_touched=False),
    )

    # gebruik de code van het cluster (CLUSTER_ID) om juiste mask te selecteren
    peilvak = peilvak.where(peilvak != cluster, 1)

    # schrijf peilvakken mask weg naar raster (.asc)
    fnames["peilvakken_raster"] = cluster_dir.joinpath("peilvakken.tif")
    peilvak.rio.to_raster(fnames["peilvakken_raster"])

    # bereken
    logger.info(f"bereken afwateringseenheden")
    fnames["afwateringseenheden"] = cluster_dir.joinpath("afwateringseenheden.gpkg")
    calculate_subcatchments(
        elevation_raster=fnames["hoogteraster"],
        water_segments_raster=fnames["waterlopen_raster"],
        areas_raster=fnames["peilvakken_raster"],
        subatchments_gpkg=fnames["afwateringseenheden"],
        max_fill_depth=MAX_FILL_DEPTH,
        crs=28992,
        report_maps=False,
    )
