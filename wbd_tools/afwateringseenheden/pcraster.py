# %%
from pathlib import Path

import numpy as np
import pcraster as pcr
import rasterio

from wbd_tools.afwateringseenheden.rasters import vectorize_data


def raster_to_pcr(raster_file, dtype: np.dtype | None = None):
    """Read non-PCRaster into PCRaster object"""
    if raster_file.suffix == ".map":
        return pcr.readmap(raster_file.as_posix())
    else:
        with rasterio.open(raster_file) as src:
            # set dtype
            if dtype is None:
                dtype = src.profile["dtype"]
            if np.issubdtype(np.dtype(dtype), np.integer):
                pcr_valuescale = pcr.Nominal
            elif np.issubdtype(np.dtype(dtype), np.floating):
                pcr_valuescale = pcr.Scalar

            data = src.read(1).astype(dtype)
            nodata = src.nodata
            return pcr.numpy2pcr(pcr_valuescale, data, nodata)


def set_clone_from_raster(raster_file):
    """Set PCRaster clone from non PCRaster"""
    if raster_file.suffix == ".map":
        pcr.setclone(raster_file.as_posix())
    with rasterio.open(raster_file) as src:
        nrRows = src.height
        nrCols = src.width
        cellSize = abs(src.res[0])
        west = src.bounds.left
        north = src.bounds.top
        pcr.setclone(nrRows, nrCols, cellSize, west, north)


def set_global_options(global_raster):
    """Set global options for PCRaster processing"""
    # set PCRaster environment
    set_clone_from_raster(global_raster)
    pcr.setglobaloption("unittrue")
    pcr.setglobaloption("lddin")


def calculate_subcatchments(
    elevation_raster: Path,
    water_segments_raster: Path,
    areas_raster: Path,
    subatchments_gpkg: Path,
    max_fill_depth: float = 1e31,
    crs: int = 28992,
    report_maps: bool = False,
):
    """Calculate subcatchments to water_segments from elevation_raster.

    Note (!) area_raster will be used later to iterate process. Not yet implemented

    Args:
        elevation_raster (Path): Any rasterio-compatible elevation raster
        water_segments_raster (Path): Any rasterio-compatible water segments raster like (!) elevation_rater
        areas_raster (Path): Any raterio-compatible areas_raster like (!) elevation raster
        subatchments_gpkg (Path): Subcatchments-file to be written
        max_fill_depth (float, optional): Max fill-depth. Defaults to 1e31.
        crs (int, optional): Raster projection, if not supplied it should be readable from elevation-raster. Defaults to 28992.
        report_maps (bool, optional): Verbose option to report PCRaster maps. Defaults to False.
    """
    # set globals from elevation_raster
    set_global_options(elevation_raster)

    # read rasters
    elevation = raster_to_pcr(elevation_raster)
    water_segments = raster_to_pcr(water_segments_raster, dtype="int32")
    areas = raster_to_pcr(areas_raster, dtype=np.dtype("int32"))

    # Local Drainage Direction map from LDD
    ldd = pcr.lddcreate(elevation, max_fill_depth, 1e31, 1e31, 1e31)

    # subcatchments from outlets
    catchments = pcr.subcatchment(ldd, water_segments)

    # vectorize sub-catchments
    with rasterio.open(elevation_raster, "r") as src:
        transform = src.transform
    nodata = -999
    if elevation_raster.suffix == ".map":
        catchments_map = elevation_raster.with_name("catchments.map")
        pcr.report(catchments, catchments_map.as_posix())
        with rasterio.open(catchments_map) as src:
            data = src.read(1).astype("int32")
    else:
        data = pcr.pcr2numpy(catchments, nodata).astype("int32")
    gdf = vectorize_data(data=data, nodata=nodata, transform=transform, crs=crs)
    gdf.to_file(subatchments_gpkg)

    # report PCRaster objects as maps
    if report_maps:
        directory = Path(elevation_raster).parent
        for pcr_map in ["elevation", "water_segments", "ldd", "catchments"]:
            pcr.report(locals()[pcr_map], (directory / f"{pcr_map}.map").as_posix())
