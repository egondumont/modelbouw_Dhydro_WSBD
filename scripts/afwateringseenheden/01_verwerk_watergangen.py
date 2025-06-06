# %%
import geopandas as gpd
from wbd_tools.afwateringseenheden.objects import read_objects, remove_duplicated_objects
from wbd_tools.afwateringseenheden.lines import (
    split_lines_to_points,
    get_line_connections,
    connecting_secondary_lines,
)
from wbd_tools.afwateringseenheden import get_logger, get_fnames


logger = get_logger()

# %%
# specificatie bestanden
fnames = get_fnames()


# %%
# Init dfs en lees mask
dfs = dict()

# onderstaande operaties worden geclipt op mask als je poly_mask en bbox berekent
# dfs["mask"] = gpd.read_file(fnames["mask"])

# poly_mask = dfs["mask"].at[0, "geometry"]
# bbox = poly_mask.bounds
poly_mask = None
bbox = None

# %%
# inlezen objecten
logger.info("verwerken objecten")

# inlezen shapes uit objecten-dir
dfs["objecten"] = read_objects(
    path=fnames["objecten"],
    poly_mask=poly_mask,
    suffix=".shp",
    keep_columns=["Code_objec"],
)

# verwijderen van gedupliceerde objecten (gelijke coordinaten)
dfs["objecten"] = remove_duplicated_objects(
    objects_gdf=dfs["objecten"],
    drop_object_types=["Legger_duiker", "Legger_syfon", "Legger_stuw"],
)

# %%
# opknippen A-waterlopen
logger.info("opknippen a-waterlopen")
TOLERANCE = 5  # tolerantie waarbinnen objecten naar een waterloop worden gesnapt
MAX_LENGTH = 500  # maximale lengte van een waterloopsegment

# inlezen van de waterlopen en multi-linestrings exploden
dfs["a_waterlopen"] = gpd.read_file(
    fnames["a_waterlopen"], engine="pyogrio", bbox=bbox
)[["Code_objec", "geometry"]]

if poly_mask is not None:
    dfs["a_waterlopen"] = dfs["a_waterlopen"].clip(poly_mask).explode(ignore_index=True)
else:
    dfs["a_waterlopen"] = dfs["a_waterlopen"].explode(ignore_index=True)

# opknippen van waterlopen bij objecten en in segmenten
dfs["waterloopsegmenten"] = split_lines_to_points(
    lines_gdf=dfs["a_waterlopen"],
    points_gdf=dfs["objecten"],
    tolerance=TOLERANCE,
    max_length=MAX_LENGTH,
)

# %%
# bepalen connectiepunten

logger.info("bepalen connectiepunten")

dfs["connecties"] = get_line_connections(
    lines_gdf=dfs["waterloopsegmenten"], points_gdf=dfs["objecten"], tolerance=5
)

# bepalen verbonden b_waterlopen
logger.info("vinden verbonden b-waterlopen")

dfs["b_waterlopen"] = gpd.read_file(
    fnames["b_waterlopen"], engine="pyogrio", bbox=bbox
)[["Code_objec", "geometry"]]


dfs["b_waterlopen"] = connecting_secondary_lines(
    lines_gdf=dfs["a_waterlopen"], secondary_lines_gdf=dfs["b_waterlopen"], tolerance=1
)


# %%
# Resultaten wegschrijven als lagen in GeoPackage
logger.info("wegschrijven resultaten")
WRITE_LAYERS = ["objecten", "waterloopsegmenten", "connecties", "b_waterlopen"]

for layer in WRITE_LAYERS:
    if layer in dfs.keys():
        dfs[layer].to_file(fnames["waterlopen_verwerkt"], layer=layer, index=True)
