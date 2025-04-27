# %%
import shutil
import pandas as pd
import geopandas as gpd
import rioxarray as rxr
from geocube.api.core import make_geocube
from functools import partial
from geocube.rasterize import rasterize_image
from pathlib import Path
from dtm2cat import get_logger, copy_binaries, calculate_subcatchments


logger = get_logger()

# %%
# specificatie bestanden
DTM2CAT_DIR = Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\02.DTM2CAT\dtm2cat")
DATA_DIR = DTM2CAT_DIR / "data"
OUT_DIR = DTM2CAT_DIR / "out"


fnames = dict()
fnames["waterlopen_verwerkt"] = OUT_DIR.joinpath("waterlopen_verwerkt.gpkg")
fnames["ahn_05m"] = DATA_DIR.joinpath(
    r"hoogtekaart", "5m_AHN3_NL", "ahn3_5m_dtm_BD_filled.tif"
)
fnames["b_waterlopen"] = DATA_DIR.joinpath("waterlopen", "Legger_waterlopen_B.shp")
fnames["clusters"] = DATA_DIR.joinpath(
    "clusters", "afwateringsgebieden_25m_15clusters_fixed.shp"
)

fnames["process_dir"] = OUT_DIR.joinpath("clusters")


# %%

# processen clusters
CLUSTERS = [6, 12, 13]
CLUSTERS = None

dfs = dict()
dfs["clusters"] = gpd.read_file(fnames["clusters"]).set_index("CLUSTER_ID", drop=False)
dfs["waterlopen"] = gpd.read_file(
    fnames["waterlopen_verwerkt"],
    layer="waterloopsegmenten",
    fid_as_index=True,
    engine="pyogrio",
)
dfs["waterlopen"].loc[:, "dtm2catId"] = dfs["waterlopen"].index
dfs["waterlopen"].loc[:, "burn_depth"] = 1000

dfs["b_waterlopen"] = gpd.read_file(
    fnames["b_waterlopen"],
    engine="pyogrio",
)
dfs["b_waterlopen"].loc[:, "burn_depth"] = 500

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
    cluster_dir.joinpath("out").mkdir(parents=True)

    # clip hoogteraster met clustergrens
    logger.info(f"aanmaken hoogteraster")
    with rxr.open_rasterio(
        fnames["ahn_05m"], mask_and_scale=True, chunks=True
    ) as ahn_raster_interp:
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
        measurements=["dtm2catId"],
        like=ahn_raster,
        fill=0,
        rasterize_function=partial(rasterize_image, all_touched=False),
    )

    fnames["waterlopen_raster"] = cluster_dir.joinpath(
        "waterlopen_verrasterd_dtm2catID.asc"
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
    fnames["hoogteraster"] = cluster_dir.joinpath("hoogtekaart_interp.asc")
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
    fnames["peilvakken_raster"] = cluster_dir.joinpath("peilvakken.asc")
    peilvak.rio.to_raster(fnames["peilvakken_raster"])

    # schrijven van CSV's voor de interne administratie van DTM2Cat

    logger.info(f"wegschrijven CSVs")
    # verkrijg lijst met ID's van watergangen
    list_ids = waterlopen_clipped_gdf["dtm2catId"].values

    # maak een DataFrame op basis van deze ID's
    df_waterlopen = pd.DataFrame(data=list_ids, columns=[r"id"])
    df_waterlopen["nr"] = list_ids
    df_waterlopen["is"] = 1

    # schrijf ID's weg naar processing map
    df_waterlopen.to_csv(cluster_dir.joinpath("waterloop.csv"), index=False)

    # gebruik voor nu een enkel peilvak voor het gehele cluster (id=1)
    list_ids_peilvakken = [1]

    # maak een DataFrame op basis van dit ID
    df_peilvakken = pd.DataFrame(data=list_ids_peilvakken, columns=[r"id"])

    # voeg kolom 'nr' toe
    df_peilvakken["nr"] = list_ids_peilvakken

    # schrijf peilvakken ID's weg naar processing directory
    df_peilvakken.to_csv(cluster_dir.joinpath("peilvakken.csv"), index=False)

    logger.info(f"wegschrijven binaries")
    copy_binaries(path=cluster_dir)

    # bereken
    logger.info(f"bereken afwateringseenheden")
    fnames["afwateringseenheden"] = cluster_dir.joinpath("afwateringseenheden.gpkg")
    calculate_subcatchments(
        elevation_raster=fnames["hoogteraster"],
        water_segments_raster=fnames["waterlopen_raster"],
        areas_raster=fnames["peilvakken_raster"],
        subatchments_gpkg=fnames["afwateringseenheden"],
        max_fill_depth=250,
        crs=28992,
        report_maps=False,
    )

logger.info("samenvoegen afwateringseenheden")
gdf = pd.concat(
    [
        gpd.read_file(i)
        for i in fnames["process_dir"].glob("*/afwateringseenheden.gpkg")
    ],
    ignore_index=True,
)

gdf.to_file(fnames["waterlopen_verwerkt"].with_name("afwateringseenheden.gpkg"))
