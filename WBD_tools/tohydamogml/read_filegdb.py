"""
Read esri filegdb and keep original objectid
"""

import fiona
import geopandas as gpd
from tohydamogml.config import COLNAME_OID


def read_filegdb(filegdb, layer):
    """Read filegdb with fiona to get original objectid. Return geopandas dataframe or pandas dataframe"""
    if layer in fiona.listlayers(filegdb):
        gdf = gpd.read_file(filegdb, layer=layer, fid_as_index=True, engine="pyogrio")
        gdf.loc[:, COLNAME_OID] = gdf.index.astype(int)
    else:
        raise ValueError(
            f"layer '{layer}' not in layer list: {fiona.listlayers(filegdb)}"
        )
