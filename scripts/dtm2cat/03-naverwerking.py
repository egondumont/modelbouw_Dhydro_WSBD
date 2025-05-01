# %%
from dtm2cat import get_logger
from pathlib import Path
import pandas as pd
import geopandas as gpd
from dtm2cat.lines import snap_point_to_line

DTM2CAT_DIR = Path(r"d:\projecten\D2508.WBD_modelinstrumentarium\02.DTM2CAT\dtm2cat")
DATA_DIR = DTM2CAT_DIR / "data"
OUT_DIR = DTM2CAT_DIR / "out"

logger = get_logger()

# %% filenames
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
fnames["waterlopen_verwerkt"] = OUT_DIR.joinpath("waterlopen_verwerkt.gpkg")
fnames["afwateringseenheden"] = OUT_DIR.joinpath("afwateringseenheden.gpkg")


# %% samenvoegen afwateringseenheden
dfs = dict()
logger.info("samenvoegen afwateringseenheden")

# samenvoegen in 1 gdf
dfs["afwateringseenheden"] = pd.concat(
    [
        gpd.read_file(i)
        for i in fnames["process_dir"].glob("*/afwateringseenheden.gpkg")
    ],
    ignore_index=True,
)
dfs["afwateringseenheden"].value = dfs["afwateringseenheden"].value.astype(int)

dfs["afwateringseenheden"] = dfs["afwateringseenheden"][
    dfs["afwateringseenheden"]["value"] != 0
]

# dissolven polygonen met gelijke waarde
dfs["afwateringseenheden"] = dfs["afwateringseenheden"].dissolve("value")
dfs["afwateringseenheden"].sort_values("value", inplace=True)

# %% Uniforme codering

logger.info("codering waterlopen en afwateringseenheden")
dfs["waterlopen"] = gpd.read_file(
    fnames["waterlopen_verwerkt"],
    layer="waterloopsegmenten",
    fid_as_index=True,
    engine="pyogrio",
)

# filter waterlopen on waterlopen not in afwateringseenheden
dfs["waterlopen"] = dfs["waterlopen"][
    dfs["waterlopen"].index.isin(dfs["afwateringseenheden"].index)
]

# object-code met een integer postfix om het uniek te maken
dfs["waterlopen"]["code"] = (
    dfs["waterlopen"].groupby("Code_objec").cumcount() + 1
).astype(str)
dfs["waterlopen"]["code"] = (
    dfs["waterlopen"]["Code_objec"] + "_" + dfs["waterlopen"]["code"]
)

dfs["afwateringseenheden"].loc[dfs["waterlopen"]["code"].index.to_numpy(), "code"] = (
    dfs["waterlopen"]["code"]
)

# %%
# Bepaling laterale knopen
logger.info("bepaling laterale knopen")

# centroide van de afwateringseenheden
dfs["lateralen"] = dfs["afwateringseenheden"].copy()
dfs["lateralen"]["geometry"] = dfs["lateralen"].centroid

# snappen centroide naar juiste waterloopsegment
dfs["waterlopen"].set_index("code", inplace=True)

dfs["lateralen"]["geometry"] = dfs["lateralen"].apply(
    (
        lambda row: snap_point_to_line(
            point=row.geometry,
            line=dfs["waterlopen"].at[row.code, "geometry"],
            tolerance=None,
        )
    ),
    axis=1,
)

# %%
logger.info("wegschrijven resultaat")

for layer in ["waterlopen", "lateralen", "afwateringseenheden"]:
    df = dfs[layer].reset_index()
    df[["code", "geometry"]].to_file(fnames["afwateringseenheden"], layer=layer)
