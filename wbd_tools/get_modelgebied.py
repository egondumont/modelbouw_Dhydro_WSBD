from wbd_tools.case_conversions import sentence_to_snake_case
import geopandas as gpd
import os
from shapely.geometry import Polygon, MultiPolygon


def get_modelgebied(modelgebied_gpkg: os.PathLike, modelnaam:str) -> MultiPolygon | Polygon:
    gdf = gpd.read_file(modelgebied_gpkg, layer="modelgebieden")
    mask = gdf.naam.apply(sentence_to_snake_case) == modelnaam
    if not mask.any():
        raise ValueError(f"{modelnaam} not a name in layer 'modelgebieden' in file {modelgebied_gpkg}")

    return gdf[mask].union_all()