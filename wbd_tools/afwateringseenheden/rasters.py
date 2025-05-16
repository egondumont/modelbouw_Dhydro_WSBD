from rasterio.io import DatasetReader
from pyproj.crs.crs import CRS
import geopandas as gpd
from rasterio.features import shapes
from numpy import ndarray
from rasterio import Affine


def vectorize_data(
    data: ndarray,
    nodata: int | float,
    transform: Affine,
    crs: CRS | int | None = None,
    column_name: str = "value",
) -> gpd.GeoDataFrame:
    """Vectorize a numpy ndarray into a GeoDataFrame

    Args:
        data (ndarray): data
        nodata (int | float): nodata-value used as mask
        crs (CRS | int | None, optional): pyproj crs. Defaults to None.
        transform (Affine): Affine transformation
        column_name (str, optional): Column name in resulting GeoDataFrame. Defaults to "value".
        band (int, optional): Band to read. Defaults to 1.

    Returns:
        gpd.GeoDataFrame: raster polygons
    """
    # mask for ignoring data
    mask = data != nodata

    # rasterize
    features = [
        {"properties": {column_name: v}, "geometry": s}
        for s, v in shapes(data, mask=mask, transform=transform)
    ]

    # Convert to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(features)

    if crs is not None:
        gdf.set_crs(crs=crs, inplace=True)

    return gdf


def vectorize_raster(
    raster: DatasetReader,
    crs: CRS | int | None = None,
    column_name: str = "value",
    band: int = 1,
) -> gpd.GeoDataFrame:
    """Vectorize a rasterio dataset into a GeoPandas GeoDataFrame

    Args:
        raster (DatasetReader): open rasterio DatasetReader
        crs (CRS | int | None, optional): pyproj crs, if None, read from raster. Defaults to None.
        column_name (str, optional): Column name in resulting GeoDataFrame. Defaults to "value".
        band (int, optional): Band to read. Defaults to 1.

    Returns:
        gpd.GeoDataFrame: raster polygons
    """
    # read data
    data = raster.read(band)
    nodata = raster.nodata
    # Set CRS from raster
    if crs is None:
        crs = raster.crs

    return vectorize_data(
        data=data,
        nodata=nodata,
        transform=raster.transform,
        crs=crs,
        column_name=column_name,
    )
