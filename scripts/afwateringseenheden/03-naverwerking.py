# %%
from wbd_tools.afwateringseenheden import get_logger, get_fnames
import pandas as pd
import geopandas as gpd
from wbd_tools.afwateringseenheden.lines import snap_point_to_line

logger = get_logger()

# %% filenames
fnames = get_fnames()

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
