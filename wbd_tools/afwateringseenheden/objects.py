# %%
import os
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Polygon
import logging
import pandas as pd
import fiona

logger = logging.Logger(__file__)

SUPPORTED_SUFFICES = [".shp", ".gpkg", ".gdb"]
SUPPORTED_GEOMETRIES = ["Point", "LineString"]


def read_objects(
    path: os.PathLike,
    poly_mask: Polygon | None = None,
    suffix: str = ".shp",
    keep_columns: list[str] = ["Code_objec"],
) -> gpd.GeoDataFrame:
    # make path absolute
    path = Path(path).absolute().resolve()

    # list files as we sometimes have ESRI shapefiles
    if path.is_dir():
        file_paths = [
            i for i in path.glob(f"*{suffix}") if i.suffix in SUPPORTED_SUFFICES
        ]
    elif path.is_file() and (path.suffix in SUPPORTED_SUFFICES):
        file_paths = [path]

    # raise for unsupported file
    if not file_paths:
        raise ValueError(
            f"path {path.as_posix()} does not yield valid file(s) with suffix {suffix} and supported suffices {SUPPORTED_SUFFICES}"
        )

    # read with bounds if poly_mask is supplied
    if poly_mask is None:
        bbox = None
    else:
        bbox = poly_mask.bounds

    # prepare keep columns
    keep_columns = list(set(keep_columns + ["object_type", "geometry"]))

    # read all layers as dfs
    dfs = []
    for file_path in file_paths:
        # read every layer in the file
        for layer in fiona.listlayers(file_path):
            # read the file
            df = gpd.read_file(file_path, layer=layer, bbox=bbox, engine="pyogrio")
            if not df.empty:
                # check if layer has only one geometry type
                geom_types = list(df.geometry.geom_type.unique())

                # try to explode MultiGeometries
                if any((i.startswith("Multi") for i in geom_types)):
                    logger.warning(
                        f"layer {layer} in {file_path} contains Multi-type geometries: {geom_types}. Trying to resolve this by explode"
                    )
                    df = df.explode(ignore_index=True)
                    geom_types = list(df.geometry.geom_type.unique())
                if len(geom_types) > 1:
                    raise ValueError(
                        f"layer {layer} in {file_path} has multiple geometry types {geom_types}. Provide only one of {SUPPORTED_GEOMETRIES}"
                    )
                else:
                    geometry_type = geom_types[0]

                # If LineString we convert to point by taking line start
                if geometry_type == "LineString":
                    df.loc[:, "geometry"] = df.boundary.explode(index_parts=True).xs(
                        0, level=1
                    )
                elif geometry_type not in SUPPORTED_GEOMETRIES:
                    raise ValueError(
                        f"layer {layer} in {file_path} has geometry type {geometry_type}. Provide one of {SUPPORTED_GEOMETRIES}"
                    )

                # we use layer.name as object_type, so we can filter later
                df["object_type"] = layer

                # add to concat-list
                dfs += [df[["Code_objec", "object_type", "geometry"]]]

    # concatenate result
    df = pd.concat(dfs, ignore_index=True)

    # filter result by poly_mask
    if poly_mask is not None:
        df = df[df.within(poly_mask)].reset_index()

    return df

    # waar duikers bij stuwen liggen, gooien we de duikers weg


def remove_duplicated_objects(
    objects_gdf: gpd.GeoDataFrame,
    drop_object_types: list[str] = ["Legger_duiker", "Legger_syfon", "Legger_stuw"],
) -> gpd.GeoDataFrame:
    duplicates = objects_gdf[objects_gdf["geometry"].duplicated(keep=False)]
    duplicated_idx = duplicates.index.to_numpy()

    # drop duplicated within 1 layer
    duplicates = pd.concat(
        [
            df.drop_duplicates(subset="geometry")
            for _, df in duplicates.groupby("object_type")
        ]
    )
    drop_idx = [i for i in duplicated_idx if i not in duplicates.index]

    # drop duplicated in order of object_types
    for object_type in drop_object_types:
        drop_idx += duplicates[duplicates["object_type"] == object_type].index.to_list()
        duplicates = duplicates[~duplicates.index.isin(drop_idx)]

    return objects_gdf[~objects_gdf.index.isin(drop_idx)]
