"""
Read esri filegdb and keep original objectid
"""

# from arcgis.features import FeatureLayerCollection
import fiona
import geopandas as gpd
from tohydamogml.config import COLNAME_OID


def read_filegdb(filegdb, layer):
    """Read filegdb with fiona to get original objectid. Return geopandas dataframe or pandas dataframe"""
    if layer in fiona.listlayers(filegdb):
        gdf = gpd.read_file(filegdb, layer=layer, fid_as_index=True, engine="pyogrio")
        gdf.loc[:, COLNAME_OID] = gdf.index.astype(int)
        gdf.reset_index(inplace=True, drop=True)
    else:
        raise ValueError(
            f"layer '{layer}' not in layer list: {fiona.listlayers(filegdb)}"
        )
    return gdf


if __name__ == "__main__":
    a = read_featureserver(
        "https://maps.brabantsedelta.nl/arcgis/rest/services/Extern/Kunstwerken/FeatureServer",
        "14",
    )
    mask = gpd.read_file(r"c:\local\TKI_WBD\aanvullende_data\Aa_of_Weerijs_v2.shp")
    gdf = a[a.intersects(mask.unary_union)]
    gdf.to_file(
        r"c:\Users\908367\Box\BH8519 WBD DHYDRO\BH8519 WBD DHYDRO WIP\04_GIS\kopie_server\Cat_A_Waterloop_Aa_of_Weerijs.shp"
    )
    gdf.to_file(
        r"c:\Users\908367\Box\BH8519 WBD DHYDRO\BH8519 WBD DHYDRO WIP\04_GIS\kopie_server\Cat_A_Waterloop_Aa_of_Weerijs.gpkg",
        driver="GPKG",
    )
