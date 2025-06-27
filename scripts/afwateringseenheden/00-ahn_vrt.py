# %%
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from osgeo import gdal
from rasterio.enums import Resampling
from rasterio.io import MemoryFile
from shapely.geometry import Polygon

# %%%
ROOT_URL = "https://service.pdok.nl/rws/ahn/atom/downloads"


def get_tiles_gdf(poly_mask: Polygon | None = None, ahn_type: str = "dtm_05m"):
    # get url
    response = requests.get(f"{ROOT_URL}/{ahn_type}/kaartbladindex.json")
    response.raise_for_status()

    # convert to gdf
    gdf = gpd.GeoDataFrame.from_features(response.json(), crs=28992)

    # clip gdf
    if poly_mask is not None:
        gdf = gdf[gdf.intersects(poly_mask)]

    return gdf


def create_vrt_file(download_dir: Path):
    # List of your GeoTIFF files
    download_dir = Path(download_dir)
    tif_files = [i.absolute().resolve().as_posix() for i in download_dir.glob("*.tif")]

    # Output VRT filename
    vrt_filename = download_dir / f"{download_dir.name}.vrt"

    # Build VRT
    vrt_options = gdal.BuildVRTOptions(
        resolution="average",
        separate=False,
        addAlpha=False,
        bandList=[1],
    )

    ds = gdal.BuildVRT(destName=vrt_filename.as_posix(), srcDSOrSrcDSTab=tif_files, options=vrt_options)
    ds.FlushCache()


def get_ahn_rasters(
    download_dir: Path,
    poly_mask: Polygon | None = None,
    ahn_type: str = "dtm_05m",
    missings_only: bool = True,
    create_vrt: bool = True,
    save_tiles_index: bool = False,
):
    # get AHN tiles as gdf
    tiles_gdf = get_tiles_gdf(poly_mask, ahn_type=ahn_type)

    # make download dir
    download_dir = Path(download_dir)
    download_dir = download_dir / ahn_type
    download_dir.mkdir(exist_ok=True, parents=True)

    # save index tiles
    if save_tiles_index:
        tiles_gdf.to_file(download_dir / f"{ahn_type}.gpkg")

    # iteratively download AHN-tiles
    for row in tiles_gdf.itertuples():
        file_path = download_dir / f"{row.kaartbladNr}.tif"

        if missings_only and (not file_path.exists()):
            print(f"downloading {row.kaartbladNr}")

            # get file
            try:
                response = requests.get(row.url)
                response.raise_for_status()
            except:
                continue

            # read tif in memory
            with MemoryFile(response.content) as memfile:
                with memfile.open() as src:
                    # Read the data
                    data = src.read(1)  # Read first band; use read() for all bands

                    # make it integer

                    data = np.where(data != src.nodata, (data * 100), -32768).astype(np.int16)

                    # update profile
                    profile = src.profile.copy()
                    profile.update(
                        dtype=np.int16,
                        compress="deflate",
                        predictor=2,
                        tiled=True,
                        driver="GTiff",
                        nodata=-32768,
                    )

                    # write it to disc

                    with rasterio.open(file_path, "w", **profile) as dst:
                        cell_size = abs(dst.res[0])
                        dst.scales = (0.01,)
                        dst.write(data, 1)
                        factors = [int(size / cell_size) for size in [5, 25] if size > cell_size]
                        dst.build_overviews(factors, Resampling.average)
                        dst.update_tags(ns="rio_overview", resampling="average")
    if create_vrt:
        create_vrt_file(download_dir)
